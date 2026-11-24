"""
MIA's directions to this node: the node's own check (DEC-0185; docs/MIA_COMMAND_INTERFACE.md, steps 1-2 of 4).

MIA may adjust targets on this node, never actuate. A direction names one whitelisted parameter on one cell, the new
value, the value MIA believes is current, and who approved it and when. `submit()` checks it here, on the node,
against the node's limits (`config/command_limits.yaml`, the node's own copy that only a person edits and a push
never overwrites; until one exists, the shipped `config/command_limits.default.yaml`; MIA can change neither):

1. the parameter is on the whitelist, the cell exists, someone approved it;
2. the cell is a whole number, the values are finite numbers (never NaN, infinity, a bool or text), the value is
   inside the parameter's hard low/high, and it keeps its band against the other end (a new minimum stays at least
   `min_band` below the maximum, and the other way round; a missing other end refuses);
3. the value MIA believed was current is the real current target (else it's refused as stale);
4. nothing for that parameter or its other end is waiting for approval (two staged changes can't cross each other),
   and no change to that parameter on that cell in the last `min_minutes_between_changes`.

All of that runs in one write transaction (BEGIN IMMEDIATE), so two directions arriving together are decided one
after the other, never both against the same picture. A refusal is recorded with its reason (`mia_commands`) and
never retried around. A direction that passes becomes a `parameter_change_proposals` row (its rationale only says
who approved it and when, in safe characters: no free text from MIA reaches the node's assistant); with
`approval: node` (the default, WAITING_ON 0zu) it waits for his press on this node, with `approval: mia` it's
approved at once. Either way approval goes through ExperimentManager.approve_parameter_change, which re-runs these
checks for a proposal from MIA (`still_valid`) and refuses one the picture has moved past since it was staged. The
safety MCU's hard limits still apply on top. Nothing here doses, switches a pump or valve, sends a notification or
touches the MCU (CLAUDE.md rules 5 and 6).

It's reached from outside only through viewer/serve_exports.py's `POST /mia/command`, which refuses anything not
signed with the node's key, stale or replayed (core/command_auth.py) before calling submit(). Not built yet (steps
3-4): the command's state in the exports MIA reads, and MIA's side.
"""

from __future__ import annotations

import logging
import math
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from contracts.capability import Describable

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
LIMITS = ROOT / "config" / "command_limits.yaml"  # the node's own (git-ignored, never pushed over)
DEFAULT_LIMITS = ROOT / "config" / "command_limits.default.yaml"  # shipped; used until the node has its own
MODULES = ROOT / "config" / "modules.yaml"
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
_SAFE = re.compile(r"[^A-Za-z0-9 ._@:+-]")
MAX_CELL = 10 ** 9


def _number(raw, whole: bool = False):
    """Pure logic. A finite number from JSON (an int, or a float unless `whole`), else None: never a bool, text, NaN,
    infinity or a number too large to be one."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    if whole:
        return raw if isinstance(raw, int) and 0 < raw <= MAX_CELL else None
    try:
        value = float(raw)
    except (OverflowError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _safe(text, limit: int) -> str:
    """Pure logic. Who and when, in safe characters only, cut short: nothing MIA sends is read as instructions."""
    return _SAFE.sub("", str(text or ""))[:limit]


class MiaCommands(Describable):
    """The node's check on MIA's directions (see the module docstring)."""

    def __init__(self, db: sqlite3.Connection, experiments, config_path: str | Path | None = None):
        self.db = db
        self.experiments = experiments
        self.config_path = Path(config_path) if config_path else None
        self.db.execute(TABLE_SQL)  # additive: a node set up before this table existed gains it here
        self.db.commit()

    def limits(self) -> dict:
        """The node's limits, read fresh each time (a person may edit them): the given file, else the node's own,
        else the shipped default. Anything missing, broken or shaped wrong leaves nothing on the whitelist (every
        direction refused), never a guessed default."""
        path = self.config_path or (LIMITS if LIMITS.exists() else DEFAULT_LIMITS)
        try:
            raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError, UnicodeDecodeError):
            raw = None
        if not isinstance(raw, dict):
            logger.warning("command limits couldn't be read; MIA's directions are all refused")
            raw = {}
        approval = raw.get("approval", "node")
        minutes = _number(raw.get("min_minutes_between_changes", 60))
        params = {}
        for name, spec in (raw.get("parameters") or {}).items() if isinstance(raw.get("parameters"), dict) else ():
            if not isinstance(spec, dict):
                continue
            low, high, band = _number(spec.get("low")), _number(spec.get("high")), _number(spec.get("min_band", 0))
            if low is None or high is None or band is None or low > high or not isinstance(spec.get("pair"), str):
                continue  # a parameter whose limits aren't clear isn't adjustable
            params[str(name)] = {"low": low, "high": high, "min_band": band, "pair": spec["pair"]}
        return {"approval": approval if approval in APPROVALS else "node",
                "min_minutes": minutes if minutes is not None and minutes >= 0 else 60.0, "parameters": params}

    def _current(self, cell_id: int, param: str) -> float | None:
        """The real current target (an active override, else config/modules.yaml), as the cell itself reads it."""
        return self.experiments._current_target(cell_id, param, str(MODULES))

    def _record(self, row: dict, state: str, reason: str, proposal_id: int | None = None) -> dict:
        """One mia_commands row: what came in, what the node decided and why (inside the caller's transaction)."""
        cur = self.db.execute(
            "INSERT INTO mia_commands (received_at, cell_id, param_name, value, believed_current, approved_by, "
            "approved_at, state, reason, proposal_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(timespec="seconds"), row.get("cell_id"), row.get("param_name", ""),
             row.get("value"), row.get("believed_current"), row.get("approved_by", ""), row.get("approved_at", ""),
             state, reason, proposal_id),
        )
        if state == "refused":
            logger.info("MIA's direction refused (%s): %s", row.get("param_name"), reason)
        return {"command_id": cur.lastrowid, "state": state, "reason": reason, "proposal_id": proposal_id}

    def _check(self, limits: dict, cell_id: int, param: str, value: float, believed: float,
               pending_ok: int | None = None) -> str:
        """Pure check against the limits and the picture now: "" when it may go, else why not. `pending_ok` is a
        proposal that may be waiting (the one being approved)."""
        spec = limits["parameters"].get(param)
        if spec is None:
            return f"{param or 'that'} isn't on this node's list of what MIA may adjust"
        if not self.db.execute("SELECT 1 FROM cells WHERE id = ?", (cell_id,)).fetchone():
            return f"there's no cell {cell_id}"
        if not (spec["low"] <= value <= spec["high"]):
            return f"{value:g} is outside {param}'s limits ({spec['low']:g}-{spec['high']:g})"
        current = self._current(cell_id, param)
        if current is None or abs(current - believed) > 1e-6:
            return "stale: the current value isn't what MIA believed"
        other = self._current(cell_id, spec["pair"])
        if other is None:
            return f"{spec['pair']} isn't set, so the band can't be kept"
        band = spec["min_band"]
        if (param.endswith("_min") and value > other - band) or (not param.endswith("_min") and value < other + band):
            return f"{value:g} would leave less than {band:g} between {param} and {spec['pair']} ({other:g})"
        waiting = self.db.execute(
            "SELECT id FROM parameter_change_proposals WHERE cell_id = ? AND param_name IN (?, ?) "
            "AND status = 'proposed'", (cell_id, param, spec["pair"])).fetchall()
        if any(w[0] != pending_ok for w in waiting):
            return f"a change to {param} or {spec['pair']} is already waiting for approval"
        if abs(value - current) < 1e-9:
            return f"{param} is already {value:g}"
        return ""

    def submit(self, command: dict, now: datetime | None = None) -> dict:
        """Checks one direction and stages or applies it (see the module docstring). Returns {command_id, state
        ('staged','applied','refused'), reason, proposal_id}. A bad direction is refused, never raised."""
        now = now or datetime.utcnow()
        limits = self.limits()
        command = command if isinstance(command, dict) else {}
        param = command.get("param_name") if isinstance(command.get("param_name"), str) else ""
        row = {"cell_id": None, "param_name": _safe(param, 60), "value": None, "believed_current": None,
               "approved_by": _safe(command.get("approved_by"), 60), "approved_at": _safe(command.get("approved_at"), 32)}
        if self.db.in_transaction:
            self.db.commit()
        self.db.execute("BEGIN IMMEDIATE")  # one direction decided at a time, from check to record
        try:
            answer = self._decide(command, row, param, limits, now)
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        if answer["state"] == "staged" and limits["approval"] == "mia":
            try:
                self.experiments.approve_parameter_change(answer["proposal_id"])
            except ValueError as problem:  # the re-check at approval refused it
                return {**answer, "state": "refused", "reason": str(problem)}
            self.db.execute("UPDATE mia_commands SET state = 'applied', reason = ? WHERE id = ?",
                            ("applied within its limits (approval: mia)", answer["command_id"]))
            self.db.commit()
            return {**answer, "state": "applied", "reason": "applied within its limits (approval: mia)"}
        return answer

    def _decide(self, command: dict, row: dict, param: str, limits: dict, now: datetime) -> dict:
        """Inside submit's transaction: the checks, then the record (and the proposal for one that passes)."""
        if param not in limits["parameters"]:
            return self._record(row, "refused", f"{param or 'that'} isn't on this node's list of what MIA may adjust")
        cell_id = _number(command.get("cell_id"), whole=True)
        value, believed = _number(command.get("value")), _number(command.get("believed_current"))
        if cell_id is None or value is None or believed is None:
            return self._record(row, "refused", "the cell, value or current value isn't a finite number")
        row.update(cell_id=cell_id, value=value, believed_current=believed)
        if not row["approved_by"].strip():
            return self._record(row, "refused", "no one approved it")
        why = self._check(limits, cell_id, param, value, believed)
        if why:
            return self._record(row, "refused", why)
        since = (now - timedelta(minutes=limits["min_minutes"])).isoformat(timespec="seconds")
        if self.db.execute("SELECT 1 FROM mia_commands WHERE cell_id = ? AND param_name = ? AND state IN "
                           "('staged','applied') AND received_at >= ?", (cell_id, param, since)).fetchone():
            return self._record(row, "refused", f"{param} changed less than {limits['min_minutes']:g} minutes ago")
        current = self._current(cell_id, param)
        rationale = (f"Direction from MIA, approved by {row['approved_by']} at {row['approved_at'] or 'an unstated time'}: "
                     f"{param} {current:g} -> {value:g}.")
        cur = self.db.execute(
            "INSERT INTO parameter_change_proposals (cell_id, param_name, current_value, proposed_value, rationale) "
            "VALUES (?, ?, ?, ?, ?)", (cell_id, param, current, value, rationale))
        return self._record(row, "staged", "waiting for your Approve on the node (approval: node)", cur.lastrowid)

    def still_valid(self, proposal_id: int) -> str:
        """For ExperimentManager.approve_parameter_change: "" when the proposal didn't come from MIA, or still passes
        every check against the picture now (its current value unchanged, limits, band, nothing else waiting);
        else why it can't be approved any more."""
        if not self.db.execute("SELECT 1 FROM mia_commands WHERE proposal_id = ?", (proposal_id,)).fetchone():
            return ""
        row = self.db.execute("SELECT cell_id, param_name, current_value, proposed_value, status FROM "
                              "parameter_change_proposals WHERE id = ?", (proposal_id,)).fetchone()
        if row is None or row[4] != "proposed":
            return "it isn't waiting for approval"
        return self._check(self.limits(), row[0], row[1], row[3], row[2], pending_ok=proposal_id)

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
            purpose=("Checks a target change MIA directs (DEC-0185) against this node's own command limits: "
                     "whitelisted parameter, finite values inside hard limits, band kept, current value as MIA "
                     "believed, nothing else waiting, one change an hour; then stages it for approval here, or "
                     "applies it through the experiment approval path, which checks it again."),
            data_produced=["a mia_commands row per direction (staged, applied or refused, with why)",
                           "a parameter_change_proposals row for each direction that passes"],
            actions_possible=["stage or apply a whitelisted target change from MIA within its limits"],
            limits_and_safety=(
                "Never doses, switches an actuator, sends a notification, rolls back config or touches the safety "
                "MCU. Only the parameters in the node's command limits, which MIA can't edit and a push never "
                "overwrites; a missing or malformed file refuses everything. Decided one at a time in a single "
                "transaction; re-checked when approved. The default approval (node) waits for a press on this "
                "node. The safety MCU's hard limits still apply on top. Reached from outside only by a request "
                "signed with this node's key, fresh and never seen before (core/command_auth.py)."),
            example_questions=["What has MIA asked to change?", "Why was MIA's pH change refused?"],
            verification_evidence=[
                "scenarios.py::scenario_mia_command_inside_limits_is_staged_for_the_node",
                "scenarios.py::scenario_mia_command_outside_limits_is_refused",
                "scenarios.py::scenario_mia_command_stale_current_value_is_refused",
                "scenarios.py::scenario_mia_command_second_change_within_the_hour_is_refused",
                "scenarios.py::scenario_mia_command_off_the_list_or_crossing_its_band_is_refused",
                "scenarios.py::scenario_mia_command_with_mia_approval_reaches_the_control_loop",
                "scenarios.py::scenario_mia_command_endpoint_takes_a_signed_direction",
                "scenarios.py::scenario_mia_command_endpoint_refuses_unsigned_wrong_old_and_replayed",
                "scenarios.py::scenario_mia_command_endpoint_without_a_key_refuses_everything",
                "scenarios.py::scenario_mia_command_staged_changes_never_cross_and_approval_rechecks",
                "scenarios.py::scenario_mia_command_two_at_once_are_decided_one_after_the_other",
                "scenarios.py::scenario_mia_command_nan_huge_and_odd_types_are_refused_not_raised",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        """None: it only reads and writes this node's database."""
        return []
