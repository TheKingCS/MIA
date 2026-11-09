"""
MIA Homestead — Circulation Flow Monitor
v0.1

Real gap closed from the same schema audit that surfaced climate
control / DO / irrigation (see CLAUDE.md, 2026-08-31): sensors.type
forward-declares 'flow' with zero implementing code. This gives it a
real actuation story: SAFETY_SPEC.md names water circulation as the
SECOND highest-priority load after aeration ("biofilter needs flow to
avoid ammonia spikes") — but nothing in this codebase could ever tell
the difference between "circulation_pump is commanded on" and
"circulation_pump is actually moving water." A seized impeller or a
clogged prefilter leaves the pump drawing power and the control loop
believing everything's fine; core/leak_detector.py's level-based check
wouldn't catch this either, since a stalled-but-sealed pump doesn't
necessarily lose tank volume at all.

Deliberately opt-in per cell (same pattern as aquaponics_cell.py's DO
monitoring) — a flow sensor isn't in any tier's hardware BOM yet, so a
cell without one stays completely silent rather than alerting on
hardware nobody bought.

Alert-only, same reasoning as leak_detector.py: no "restart the pump"
actuator exists in this system's model, and there's real danger in
software self-restarting a mechanically-failed pump anyway — a human
response is correct here, this just makes sure they find out fast.
"""

import logging
import sqlite3

from contracts.capability import Describable
from contracts.mia_homestead_contract import Severity, raise_alert

logger = logging.getLogger("mia_homestead.circulation_monitor")

# A flow reading this low or lower, while the pump is commanded on,
# means "not meaningfully moving water" regardless of the pump's real
# rated GPH — deliberately unit-agnostic and conservative (only flags
# near-total stoppage, not "underperforming spec") since no per-pump
# expected flow rate is calibrated anywhere in this system yet.
FLOW_STOPPED_THRESHOLD = 1.0
# Require this many consecutive low readings before alerting — avoids
# a single sensor glitch, same "don't trust one reading" discipline
# used everywhere else in this project.
MIN_CONSECUTIVE_LOW_READINGS = 2


class CirculationMonitor(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def check_circulation(self) -> list[dict]:
        """Called periodically (main.py). For every cell with an active
        flow sensor, compares its recent readings against whether the
        circulation_pump actuator is currently commanded on. Returns
        cells found with a real, confirmed stoppage."""
        stopped = []
        cells = self.db.execute(
            "SELECT DISTINCT cell_id FROM sensors WHERE type = 'flow' AND active = 1"
        ).fetchall()
        for (cell_id,) in cells:
            if self._pump_stalled(cell_id):
                stopped.append({"cell_id": cell_id})
        return stopped

    def _pump_stalled(self, cell_id: int) -> bool:
        pump_state = self._pump_commanded_state(cell_id)
        if pump_state != "on":
            return False  # deliberately off (e.g. load-shed) — no flow expected, nothing to flag

        readings = self.db.execute(
            """
            SELECT sr.value FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.cell_id = ? AND s.type = 'flow' AND s.active = 1
            ORDER BY sr.id DESC LIMIT ?
            """,
            (cell_id, MIN_CONSECUTIVE_LOW_READINGS),
        ).fetchall()
        if len(readings) < MIN_CONSECUTIVE_LOW_READINGS:
            return False  # not enough history yet to be confident

        all_stopped = all(v is not None and v <= FLOW_STOPPED_THRESHOLD for (v,) in readings)
        if not all_stopped:
            return False

        raise_alert(
            self.db, "circulation_monitor", Severity.CRITICAL.value,
            f"cell {cell_id}: circulation pump commanded ON but flow reads near zero "
            f"({MIN_CONSECUTIVE_LOW_READINGS} consecutive readings <= {FLOW_STOPPED_THRESHOLD}) "
            f"— probable seized pump or clogged filter, biofilter/aeration flow at risk",
            self.notifier,
        )
        return True

    def get_circulation_status(self, cell_id: int | None = None) -> list[dict]:
        """Read-only view for the assistant — every cell with a flow
        sensor configured, its latest reading, and the pump's currently
        commanded state."""
        query = "SELECT DISTINCT cell_id FROM sensors WHERE type = 'flow' AND active = 1"
        params = ()
        if cell_id is not None:
            query += " AND cell_id = ?"
            params = (cell_id,)
        cells = self.db.execute(query, params).fetchall()

        out = []
        for (cid,) in cells:
            row = self.db.execute(
                """
                SELECT sr.value, sr.timestamp FROM sensor_readings sr
                JOIN sensors s ON s.id = sr.sensor_id
                WHERE s.cell_id = ? AND s.type = 'flow' AND s.active = 1
                ORDER BY sr.id DESC LIMIT 1
                """,
                (cid,),
            ).fetchone()
            out.append({
                "cell_id": cid,
                "latest_flow_reading": row[0] if row else None,
                "reading_timestamp": row[1] if row else None,
                "pump_commanded_state": self._pump_commanded_state(cid),
            })
        return out

    def _pump_commanded_state(self, cell_id: int) -> str | None:
        row = self.db.execute(
            """
            SELECT ae.action FROM actuator_events ae
            JOIN actuators a ON a.id = ae.actuator_id
            WHERE a.cell_id = ? AND a.type = 'circulation_pump'
            ORDER BY ae.id DESC LIMIT 1
            """,
            (cell_id,),
        ).fetchone()
        if row is not None:
            return row[0]
        # No actuator_events row yet (real deployments never touch this
        # actuator's state via a command — see aquaponics_cell.py's own
        # _safety_fallback_commands() comment) — fall back to its
        # configured safe_default_state, which is always 'on' for
        # circulation_pump in every real config so far.
        default = self.db.execute(
            "SELECT safe_default_state FROM actuators WHERE cell_id = ? AND type = 'circulation_pump' LIMIT 1",
            (cell_id,),
        ).fetchone()
        return default[0] if default else None

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="circulation_monitor",
            display_name="Circulation Flow Monitor",
            purpose=(
                "Detects a circulation pump that's commanded on but not actually moving "
                "water — a seized impeller or clogged filter that power/level monitoring alone "
                "would miss. Distinct from leak_detector.py: this catches stalled-but-sealed "
                "circulation, not water loss."
            ),
            data_produced=["flow reading history (if a flow sensor is configured)"],
            actions_possible=["raise a critical alert when a commanded-on pump reads near-zero flow"],
            limits_and_safety=(
                f"Opt-in per cell — silent entirely if no flow sensor is configured (not in "
                f"any tier's hardware BOM yet). Requires {MIN_CONSECUTIVE_LOW_READINGS} "
                f"consecutive readings at or below {FLOW_STOPPED_THRESHOLD} before alerting "
                "— avoids a single sensor glitch. Never alerts when the pump is deliberately "
                "off (e.g. load-shed). Alert-only — no 'restart the pump' actuator exists, and "
                "software self-restarting a mechanically-failed pump would be unsafe; a human "
                "response is correct here."
            ),
            example_questions=["Is the circulation pump actually moving water?", "Why is the biofilter alarm firing?"],
            verification_evidence=[
                "scenarios.py::scenario_circulation_stall_detected — confirmed a pump commanded "
                "on with 2 consecutive near-zero flow readings raises a real critical alert",
                "scenarios.py::scenario_circulation_off_no_alert — confirmed a deliberately-off "
                "pump with zero flow raises nothing",
                "scenarios.py::scenario_circulation_no_sensor_silent — confirmed a cell with no "
                "flow sensor configured raises zero circulation alerts",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="Inline water flow sensor (hall-effect, e.g. YF-S201 class)", category="sensor",
                quantity=1, purpose="confirms circulation is actually moving water, not just commanded on",
                est_unit_cost=10.0,
                notes="Estimate, not independently live-fetched this session — typical current "
                      "market price for this class of hobbyist flow sensor. Not in any tier's "
                      "hardware BOM yet (docs/HARDWARE_BOM_FULL_TIERS.md) — a real add candidate.",
            ),
        ]
