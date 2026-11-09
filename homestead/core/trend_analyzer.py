"""
MIA Homestead — Sensor Trend Analyzer
v0.1

Everything else that watches sensor_readings is threshold-based:
`modules/aquaponics_cell.py` only reacts once a reading is already
outside a hard target range. That's correct for safety (dosing must
never guess), but it means a sensor that's slowly drifting toward
trouble — still technically "in range" every single cycle — produces
no signal at all until the moment it crosses the line. This is the
"efficient and scientific, not just reactive" half of the project's
own stated goal: catch the drift, not just the breach.

Deliberately read-only and separate from the control loop
(`modules/aquaponics_cell.py`) rather than added to it — this only
ever raises an INFO/WARNING alert, never touches dosing logic or
target ranges, so it can't destabilize anything CLAUDE.md's safety
rules govern. A core/*.py service, not a MiaHomesteadModule subclass,
for the same reason diagnostics.py isn't one: nothing physical to
actuate, no `evaluate()`/hardware-requirements shape that fits.

Method: for each active sensor, split its most recent readings into a
"recent" window and an older "baseline" window (by READING COUNT, not
wall-clock time — robust to whatever the real poll interval turns out
to be). If the recent window's mean is more than `z_threshold` standard
deviations from the baseline window's mean, and there's enough baseline
history to make that a meaningful comparison at all, raise a WARNING
alert via contracts.mia_homestead_contract.raise_alert() (same
dedup-by-source+message path every other alert in this project goes
through — see that function's own docstring for why a repeat doesn't
re-notify).
"""

import logging
import sqlite3
import statistics

from contracts.capability import Describable
from contracts.mia_homestead_contract import raise_alert

logger = logging.getLogger("mia_homestead.trend_analyzer")

# Below this many baseline readings, there simply isn't enough history
# to call anything a "baseline" yet — silently skip rather than flag a
# fresh sensor's first few readings as "drift" against nothing.
MIN_BASELINE_READINGS = 20
RECENT_WINDOW = 6
Z_THRESHOLD = 3.0
# Guards against a division blow-up when a baseline happens to be
# almost perfectly flat (e.g. very early simulator noise) — a tiny but
# nonzero floor rather than skipping the check whenever variance is low.
MIN_BASELINE_STDEV = 0.01


class TrendAnalyzer(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def _drift_for_sensor(self, sensor_id: int) -> dict | None:
        rows = self.db.execute(
            "SELECT value FROM sensor_readings WHERE sensor_id = ? ORDER BY id DESC LIMIT ?",
            (sensor_id, MIN_BASELINE_READINGS + RECENT_WINDOW),
        ).fetchall()
        if len(rows) < MIN_BASELINE_READINGS + RECENT_WINDOW:
            return None

        values = [r[0] for r in rows]
        recent = values[:RECENT_WINDOW]
        baseline = values[RECENT_WINDOW:]

        baseline_mean = statistics.mean(baseline)
        baseline_stdev = max(statistics.pstdev(baseline), MIN_BASELINE_STDEV)
        recent_mean = statistics.mean(recent)

        z = (recent_mean - baseline_mean) / baseline_stdev
        if abs(z) < Z_THRESHOLD:
            return None

        return {
            "sensor_id": sensor_id,
            "baseline_mean": round(baseline_mean, 3),
            "baseline_stdev": round(baseline_stdev, 3),
            "recent_mean": round(recent_mean, 3),
            "z_score": round(z, 2),
            "direction": "up" if z > 0 else "down",
        }

    def check_all_sensors(self) -> list[dict]:
        """Called periodically (main.py) — evaluates every active
        sensor, raises a WARNING alert (never critical — this is an
        early-warning signal about a trend, not a confirmed problem the
        way a hard threshold breach is) for anything drifting, and
        returns every finding either way so a caller can log/inspect
        without re-querying."""
        findings = []
        sensors = self.db.execute(
            "SELECT id, cell_id, type FROM sensors WHERE active = 1"
        ).fetchall()
        for sensor_id, cell_id, sensor_type in sensors:
            drift = self._drift_for_sensor(sensor_id)
            if drift is None:
                continue
            findings.append({**drift, "cell_id": cell_id, "sensor_type": sensor_type})
            message = (
                f"{sensor_type} sensor (cell {cell_id}) trending {drift['direction']} — "
                f"recent avg {drift['recent_mean']} vs. baseline {drift['baseline_mean']} "
                f"± {drift['baseline_stdev']} ({drift['z_score']} std devs). Still within "
                f"target range if no other alert has fired — worth watching before it "
                f"isn't."
            )
            raise_alert(self.db, f"trend_analyzer_cell_{cell_id}", "warning", message, self.notifier)
            logger.info("Drift detected: %s", message)
        return findings

    def get_drift_status(self, cell_id: int | None = None) -> list[dict]:
        """Read-only — the assistant-facing lookup (get_sensor_trends
        tool), computed fresh rather than cached so it always reflects
        the current buffer, not whatever check_all_sensors() last saw."""
        query = "SELECT id, cell_id, type FROM sensors WHERE active = 1"
        params = ()
        if cell_id is not None:
            query += " AND cell_id = ?"
            params = (cell_id,)
        results = []
        for sensor_id, sid_cell_id, sensor_type in self.db.execute(query, params).fetchall():
            drift = self._drift_for_sensor(sensor_id)
            if drift is not None:
                results.append({**drift, "cell_id": sid_cell_id, "sensor_type": sensor_type})
        return results

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="trend_analyzer",
            display_name="Sensor Trend Analyzer",
            purpose=(
                "Catches a sensor slowly drifting toward trouble before it crosses a hard "
                "threshold — every other check in this project is reactive (alert once "
                "already out of range); this one is proactive, comparing a short recent "
                "window against each sensor's own longer rolling baseline."
            ),
            data_produced=["drift finding: sensor, baseline mean/stdev, recent mean, z-score, direction"],
            actions_possible=["scan all active sensors for drift", "look up current drift status for a cell"],
            limits_and_safety=(
                "Strictly read-only and separate from the control loop — never touches dosing "
                "logic, target ranges, or actuators, and only ever raises a WARNING (never "
                "critical) since this is an early-warning trend signal, not a confirmed "
                "problem. Requires at least 20 baseline readings per sensor before evaluating "
                "it at all, specifically to avoid flagging a freshly-added sensor's first few "
                "readings as 'drift' against no real history."
            ),
            example_questions=["Is anything drifting?", "Is the pH trending in a bad direction?"],
            verification_evidence=[
                "Live manual test 2026-08-30: seeded a real pH sensor with 20 baseline "
                "readings (mean 6.404, real noise, stdev 0.015) + 6 readings shifted to "
                "exactly +5 baseline-stdevs, confirmed check_all_sensors() correctly flagged "
                "it (z-score 5.0, direction 'up') and raised exactly one WARNING alert; "
                "confirmed a perfectly flat 26-reading series produces zero findings; "
                "confirmed fewer than 26 total readings produces zero findings (insufficient "
                "baseline, not a false positive from too little data); confirmed calling "
                "check_all_sensors() again immediately bumps the existing alert's "
                "occurrence_count (2) rather than inserting a second row — the dedup fix in "
                "contracts.mia_homestead_contract.raise_alert() composes correctly with this "
                "module, its second real caller.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure reasoning layer over existing sensor_readings, no hardware of its own
