"""
MIA's directions to this node: the node's own check (DEC-0185; docs/MIA_COMMAND_INTERFACE.md, step 1 of 4).

MIA may adjust targets on this node, never actuate. A direction names one whitelisted parameter on one cell, the new
value, the value MIA believes is current, and who approved it and when. `submit()` checks it here, on the node,
against config/command_limits.yaml (which MIA can't change):

1. the parameter is on the whitelist, the cell exists, someone approved it;
2. the value is a number inside the parameter's hard low/high, and keeps its band (a new minimum stays at least
   `min_band` below the current maximum, and the other way round);
3. the value MIA believed was current is the real current target (else it's refused as stale: something else
   changed it since she looked);
4. no change to that parameter on that cell in the last `min_minutes_between_changes` (staged or applied), so
   nothing can oscillate.

A refusal is recorded with its reason (`mia_commands`) and never retried around. A direction that passes becomes a
`parameter_change_proposals` row, exactly as an experiment's suggested change does; with `approval: node` (the
default, WAITING_ON 0zu) it waits there for his press on this node (ExperimentManager.approve_parameter_change),
with `approval: mia` it's approved at once through that same method, so it lands as a target_overrides row the
control loop reads. Either way the safety MCU's hard limits still apply on top. Nothing here doses, switches a
pump or valve, sends a notification or touches the MCU: those stay with the control loop and the existing approval
queues (CLAUDE.md rules 5 and 6).

Not built yet (steps 2-4): the signed endpoint MIA sends to, the command's state in the exports she reads, and
MIA's side. Until then nothing outside this process can call submit().
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from contracts.capability import Describable

logger = logging.getLogger(__name__)

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mia_commands (
    id INTEGER PRIMARY KEY,
    received_at TEXT NOT NULL,
    cell_id INTEGER,
    param_name TEXT NOT NULL,
    value REAL,
    believed_current REAL,
    approved_by TEXT,
    approved_at TEXT,
    state TEXT NOT NULL,                -- 'staged','applied','refused'
    reason TEXT NOT NULL,
    proposal_id INTEGER REFERENCES parameter_change_proposals(id)
)
"""
APPROVALS = ("node", "mia")


class MiaCommands(Describable):
    """The node's check on MIA's directions (see the module docstring)."""

    def __init__(self, db: sqlite3.Connection, experiments, config_path: str = "config/command_limits.yaml"):
        self.db = db
        self.experiments = experiments
        self.config_path = config_path
        self.db.execute(TABLE_SQL)  # additive: a node set up before this table existed gains it here
        self.db.commit()

    def limits(self) -> dict:
        """config/command_limits.yaml, read fresh each time (a person may edit it); a missing or broken file means
        nothing is on the whitelist, never a guessed default."""
        try:
            raw = yaml.safe_load(Path(self.config_path).read_text()) or {}
        except (OSError, yaml.YAMLError):
            logger.warning("command_limits.yaml couldn't be read; MIA's directions are all refused")
            raw = {}
        approval = raw.get("approval", "node")
        return {"approval": approval if approval in APPROVALS else "node",
                "min_minutes": float(raw.get("min_minutes_between_changes", 60) or 60),
                "parameters": dict(raw.get("parameters") or {})}

    def _current(self, cell_id: int, param: str) -> float | None:
        """The real current target (an active override, else config/modules.yaml), as the cell itself reads it."""
        return self.experiments._current_target(cell_id, param)

    def _refuse(self, row: dict, reason: str) -> dict:
        """Records a refusal with its reason and says so."""
        return self._record(row, "refused", reason)

    def _record(self, row: dict, state: str, reason: str, proposal_id: int | None = None) -> dict:
        """One mia_commands row: what came in, what the node decided and why."""
        cur = self.db.execute(
            "INSERT INTO mia_commands (received_at, cell_id, param_name, value, believed_current, approved_by, "
            "approved_at, state, reason, proposal_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(timespec="seconds"), row.get("cell_id"), str(row.get("param_name", ""))[:60],
             row.get("value"), row.get("believed_current"), str(row.get("approved_by", ""))[:80],
             str(row.get("approved_at", ""))[:40], state, reason, proposal_id),
        )
        self.db.commit()
        if state == "refused":
            logger.info("MIA's direction refused (%s): %s", row.get("param_name"), reason)
        return {"command_id": cur.lastrowid, "state": state, "reason": reason, "proposal_id": proposal_id}

    def submit(self, command: dict, now: datetime | None = None) -> dict:
        """Checks one direction and stages or applies it (see the module docstring). Returns {command_id, state
        ('staged','applied','refused'), reason, proposal_id}. Never raises on a bad direction: it's refused."""
        now = now or datetime.utcnow()
        limits = self.limits()
        param = str(command.get("param_name", "") or "")
        row = {"cell_id": command.get("cell_id"), "param_name": param, "value": None,
               "believed_current": None, "approved_by": command.get("approved_by", ""),
               "approved_at": command.get("approved_at", "")}
        spec = limits["parameters"].get(param)
        if spec is None:
            return self._refuse(row, f"{param or 'that'} isn't on this node's list of what MIA may adjust")
        try:
            cell_id = int(command.get("cell_id"))
            value = float(command.get("value"))
            believed = float(command.get("believed_current"))
        except (TypeError, ValueError):
            return self._refuse(row, "the cell, value or current value isn't a number")
        row.update(cell_id=cell_id, value=value, believed_current=believed)
        if not self.db.execute("SELECT 1 FROM cells WHERE id = ?", (cell_id,)).fetchone():
            return self._refuse(row, f"there's no cell {cell_id}")
        if not str(command.get("approved_by", "") or "").strip():
            return self._refuse(row, "no one approved it")
        if not (float(spec["low"]) <= value <= float(spec["high"])):
            return self._refuse(row, f"{value:g} is outside {param}'s limits ({spec['low']}-{spec['high']})")
        current = self._current(cell_id, param)
        if current is None or abs(current - believed) > 1e-6:
            return self._refuse(row, f"stale: MIA believed {believed:g}, it's {current if current is not None else 'unset'}")
        pair, band = spec.get("pair"), float(spec.get("min_band", 0) or 0)
        other = self._current(cell_id, pair) if pair else None
        if other is not None:
            is_min = param.endswith("_min")
            if (is_min and value > other - band) or (not is_min and value < other + band):
                return self._refuse(row, f"{value:g} would leave less than {band:g} between {param} and {pair} "
                                         f"({other:g})")
        since = (now - timedelta(minutes=limits["min_minutes"])).isoformat(timespec="seconds")
        recent = self.db.execute(
            "SELECT 1 FROM mia_commands WHERE cell_id = ? AND param_name = ? AND state IN ('staged','applied') "
            "AND received_at >= ?", (cell_id, param, since)).fetchone()
        if recent:
            return self._refuse(row, f"{param} changed less than {limits['min_minutes']:g} minutes ago")
        if abs(value - current) < 1e-9:
            return self._refuse(row, f"{param} is already {value:g}")
        rationale = (f"Direction from MIA, approved by {row['approved_by']} at {row['approved_at'] or 'an unstated time'}: "
                     f"{param} {current:g} -> {value:g}. {str(command.get('why', '') or '')[:200]}").strip()
        cur = self.db.execute(
            "INSERT INTO parameter_change_proposals (cell_id, param_name, current_value, proposed_value, rationale) "
            "VALUES (?, ?, ?, ?, ?)", (cell_id, param, current, value, rationale))
        self.db.commit()
        proposal_id = cur.lastrowid
        if limits["approval"] == "mia":
            self.experiments.approve_parameter_change(proposal_id)
            return self._record(row, "applied", "applied within its limits (approval: mia)", proposal_id)
        return self._record(row, "staged", "waiting for your Approve on the node (approval: node)", proposal_id)

    def recent(self, limit: int = 20) -> list[dict]:
        """The latest directions and what became of each, newest first (for the exports MIA reads, step 3)."""
        self.db.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in self.db.execute(
                "SELECT * FROM mia_commands ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
        finally:
            self.db.row_factory = None

    def describe_capabilities(self):
        """What the node's check on MIA's directions does, with the scenarios that prove it."""
        from contracts.capability import Capability
        return Capability(
            module_id="mia_commands",
            display_name="MIA's Directions (the node's check)",
            purpose=("Checks a target change MIA directs (DEC-0185) against config/command_limits.yaml on this node: "
                     "whitelisted parameter, hard limits, band kept, current value as MIA believed, one change an "
                     "hour; then stages it for approval here, or applies it through the experiment approval path."),
            data_produced=["a mia_commands row per direction (staged, applied or refused, with why)",
                           "a parameter_change_proposals row for each direction that passes"],
            actions_possible=["stage or apply a whitelisted target change from MIA within its limits"],
            limits_and_safety=(
                "Never doses, switches an actuator, sends a notification, rolls back config or touches the safety "
                "MCU. Only the parameters in config/command_limits.yaml, which MIA can't edit; a missing file "
                "refuses everything. The default approval (node) waits for a press on this node. The safety MCU's "
                "hard limits still apply on top. Not reachable from outside this process until the signed "
                "endpoint (step 2) is built."),
            example_questions=["What has MIA asked to change?", "Why was MIA's pH change refused?"],
            verification_evidence=[
                "scenarios.py::scenario_mia_command_inside_limits_is_staged_for_the_node",
                "scenarios.py::scenario_mia_command_outside_limits_is_refused",
                "scenarios.py::scenario_mia_command_stale_current_value_is_refused",
                "scenarios.py::scenario_mia_command_second_change_within_the_hour_is_refused",
                "scenarios.py::scenario_mia_command_off_the_list_or_crossing_its_band_is_refused",
                "scenarios.py::scenario_mia_command_with_mia_approval_reaches_the_control_loop",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        """None: it only reads and writes this node's database."""
        return []
