"""
MIA Homestead — Fast Water-Loss / Leak Detection
v0.1

core/trend_analyzer.py catches SLOW drift against a rolling baseline —
it's not built to catch a sudden leak (a level sensor dropping fast,
right now, not over a multi-reading window). A major leak is one of
the most common real aquaponics failure modes, and SAFETY_SPEC.md's own
alerting escalation section names "water level critical" as a CRITICAL-
tier example explicitly — this closes that gap with a focused,
purpose-built check rather than stretching trend_analyzer's baseline-
comparison shape to cover a fundamentally different failure mode (fast
rate-of-change right now vs. slow mean-shift over many readings).

Computes rate from REAL WALL-CLOCK TIMESTAMPS between the two most
recent readings, not a reading-count/tick basis — this is deliberately
different from trend_analyzer's own "robust to whatever the poll
interval turns out to be" reasoning applied to a different problem:
here, the actual RATE (inches per minute) is the whole signal, so it
must be measured in real time, not readings-elapsed. This also means
it's correct regardless of the simulator's own deliberately compressed
evaporation rate (drivers/physics_sim.py's EVAPORATION_LEVEL_DRIFT_PER_TICK
is a fast, compressed-for-testing value, not a real physical rate — see
that module's own docstring) — this module reasons from real elapsed
minutes, never simulator tick counts.

Purely read/alert — never touches dosing, never touches any actuator.
No "shut off water inflow" actuator even exists in this system's model;
a real physical response stays a human action (or, longer-term, the
physical override switch SAFETY_SPEC.md already specifies), same
reasoning every other core/*.py reasoning-only service in this project
applies to its own read-only role.
"""

import logging
import sqlite3
from datetime import datetime

from contracts.capability import Describable
from contracts.mia_homestead_contract import Severity, raise_alert

logger = logging.getLogger("mia_homestead.leak_detector")

# A real, physically-grounded starting threshold, not a calibrated one —
# same honesty as dosing_limits' own placeholder values pending real
# hardware. Real evaporation for an open greenhouse tank is roughly
# 0.25-0.5 inches per DAY even under aggressive conditions (hot, low
# humidity, no lid) — on the order of 0.0003-0.0007 in/min. This
# threshold sits well above that (~30x a realistic evaporation upper
# bound) so ordinary evaporation can never trigger it, while a real leak
# (which drains far faster) reliably does. Tune once real tank geometry
# exists.
LEAK_RATE_THRESHOLD_INCHES_PER_MINUTE = 0.02


class LeakDetector(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def _rate_for_sensor(self, sensor_id: int) -> dict | None:
        rows = self.db.execute(
            "SELECT value, timestamp FROM sensor_readings WHERE sensor_id = ? "
            "ORDER BY id DESC LIMIT 2",
            (sensor_id,),
        ).fetchall()
        if len(rows) < 2:
            return None
        (newer_value, newer_ts), (older_value, older_ts) = rows
        try:
            newer_dt = datetime.fromisoformat(newer_ts)
            older_dt = datetime.fromisoformat(older_ts)
        except ValueError:
            return None
        elapsed_minutes = (newer_dt - older_dt).total_seconds() / 60
        if elapsed_minutes <= 0:
            return None

        drop = older_value - newer_value  # positive = level fell
        rate = drop / elapsed_minutes
        return {"sensor_id": sensor_id, "rate_per_minute": rate, "elapsed_minutes": elapsed_minutes,
                "newer_value": newer_value, "older_value": older_value}

    def check_for_leaks(self) -> list[dict]:
        """Called every control-loop cycle (main.py) — deliberately NOT
        gated to the 60-cycle periodic block every other periodic check
        uses. A real leak needs detection within one cycle, not up to
        60 cycles later; that delay is the whole gap this module exists
        to close."""
        findings = []
        sensors = self.db.execute(
            "SELECT id, cell_id FROM sensors WHERE active = 1 AND type = 'level'"
        ).fetchall()
        for sensor_id, cell_id in sensors:
            result = self._rate_for_sensor(sensor_id)
            if result is None or result["rate_per_minute"] <= LEAK_RATE_THRESHOLD_INCHES_PER_MINUTE:
                continue  # not falling, or falling no faster than a real leak-implausible rate
            message = (
                f"cell {cell_id}: water level sensor (id {sensor_id}) dropped "
                f"{result['older_value']:.2f} -> {result['newer_value']:.2f} in "
                f"{result['elapsed_minutes']:.1f} minute(s) ({result['rate_per_minute']:.3f} in/min) "
                f"— far faster than plausible evaporation, possible leak"
            )
            raise_alert(self.db, "leak_detector", Severity.CRITICAL, message, self.notifier)
            logger.warning("Possible leak detected: %s", message)
            findings.append({"cell_id": cell_id, **result})
        return findings

    def get_leak_status(self, cell_id: int | None = None) -> list[dict]:
        """Read-only assistant-facing lookup — current rate for every
        active level sensor (optionally filtered by cell), computed
        fresh, whether or not it currently crosses the alert threshold."""
        query = "SELECT id, cell_id FROM sensors WHERE active = 1 AND type = 'level'"
        params = ()
        if cell_id is not None:
            query += " AND cell_id = ?"
            params = (cell_id,)
        results = []
        for sensor_id, sid_cell_id in self.db.execute(query, params).fetchall():
            result = self._rate_for_sensor(sensor_id)
            if result is not None:
                results.append({**result, "cell_id": sid_cell_id,
                                 "above_leak_threshold": result["rate_per_minute"] > LEAK_RATE_THRESHOLD_INCHES_PER_MINUTE})
        return results

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="leak_detector",
            display_name="Fast Water-Loss / Leak Detection",
            purpose=(
                "Catches a water level dropping far faster than evaporation could explain — "
                "within one control cycle, not the up-to-60-cycle delay every other periodic "
                "check tolerates — since SAFETY_SPEC.md names water level critical as a "
                "CRITICAL-tier alert explicitly, and a real leak is one of the most common "
                "aquaponics failure modes."
            ),
            data_produced=["real-time level drop rate per cell, and whether it crosses the leak threshold"],
            actions_possible=["scan all level sensors for a leak-implausible drop rate every cycle",
                               "look up current level-drop rate for a cell"],
            limits_and_safety=(
                "Strictly read-only — never touches dosing, actuators, or any control-loop "
                "decision; no 'shut off water inflow' actuator even exists in this system's "
                "model, a real physical response stays a human action. Computes rate from real "
                "wall-clock timestamps between the two most recent readings, never simulator "
                "tick counts, so it's correct regardless of poll cadence. The threshold "
                "(0.02 in/min, ~30x a realistic evaporation upper bound) is a real, "
                "physically-grounded starting point, not yet calibrated against real tank "
                "geometry — same honesty as dosing_limits' own placeholder values."
            ),
            example_questions=["Is anything leaking?", "How fast is the water level dropping right now?"],
            verification_evidence=[
                "scenarios.py::scenario_leak_detection — confirmed a slow, evaporation-plausible "
                "drop over a real 10-minute gap does NOT trigger; confirmed a fast drop over a "
                "real 2-minute gap (well past the threshold) DOES raise a real CRITICAL alert; "
                "confirmed a level RISE (e.g. after a refill) never falsely triggers regardless "
                "of magnitude.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure reasoning layer over existing sensor_readings, no hardware of its own
