"""
MIA Homestead — Sensor Confidence
v0.1

Right now a sensor reading is binary: valid (used) or invalid (stale/
out-of-range, discarded — see contracts.mia_homestead_contract). There's
no middle ground for "this reading is probably fine but the sensor is
overdue for calibration, so weight it a little less" (SUSTAINING_FEATURES.md
#5). This is that middle ground — a synthesis, read-only layer combining
two signals that ALREADY exist and ALREADY alert on their own
(sensors.calibration_due, via core/maintenance.py's
generate_calibration_tasks(); drift, via core/trend_analyzer.py's
check_all_sensors()) into one convenient "how much should I trust this
sensor right now" answer, rather than a new detection mechanism.

Deliberately, permanently informational only. Confidence NEVER changes
dosing/control-loop behavior — modules/aquaponics_cell.py's "never dose
on a single reading, require 3 consistent readings" rule and the
recovery ladder's retry logic are unconditional safety gates, not
tunable by a soft trust score. Lowering the bar for a "low confidence"
reading would be exactly the kind of thing CLAUDE.md's safety rules
exist to prevent; this only ever surfaces the signal for a human or the
assistant to see, same reasoning core/trend_analyzer.py and
core/diagnostics.py already apply to their own read-only roles.
"""

import logging
import sqlite3
from datetime import date, datetime

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.sensor_confidence")

# How close to (or past) calibration_due counts as "get it done soon,"
# not yet "overdue" (that's already maintenance.py's own job to flag).
CALIBRATION_DUE_SOON_DAYS = 7


class SensorConfidence(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    def get_confidence(self, sensor_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT id, cell_id, type, calibration_due FROM sensors WHERE id = ?", (sensor_id,)
        ).fetchone()
        if not row:
            return None
        _, cell_id, sensor_type, calibration_due = row

        factors = []
        days_until_due = None
        if calibration_due:
            try:
                due_date = date.fromisoformat(calibration_due)
                # UTC, not local date.today() — calibration_due is always
                # written via SQLite's date('now', ...), which is UTC.
                # Near a UTC/local day boundary these disagree by a day —
                # same class of Python-stdlib-vs-SQLite mismatch as
                # CLAUDE.md's documented isoformat/space-separator bug,
                # just the UTC-vs-local variant. Found live, 2026-08-31.
                days_until_due = (due_date - datetime.utcnow().date()).days
            except ValueError:
                days_until_due = None
            if days_until_due is not None:
                if days_until_due < 0:
                    factors.append(f"calibration overdue by {-days_until_due} day(s)")
                elif days_until_due <= CALIBRATION_DUE_SOON_DAYS:
                    factors.append(f"calibration due in {days_until_due} day(s)")

        drift_flagged = False
        drift_finding = self._drift_finding_for(sensor_id)
        if drift_finding:
            drift_flagged = True
            factors.append(
                f"currently flagged as trending {drift_finding['direction']} "
                f"(z-score {drift_finding['z_score']})"
            )

        if drift_flagged or (days_until_due is not None and days_until_due < 0):
            level = "low"
        elif days_until_due is not None and days_until_due <= CALIBRATION_DUE_SOON_DAYS:
            level = "medium"
        else:
            level = "high"

        return {
            "sensor_id": sensor_id, "cell_id": cell_id, "sensor_type": sensor_type,
            "level": level, "factors": factors,
            "calibration_due": calibration_due, "days_until_calibration_due": days_until_due,
            "drift_flagged": drift_flagged,
        }

    def _drift_finding_for(self, sensor_id: int) -> dict | None:
        from core.trend_analyzer import TrendAnalyzer
        row = self.db.execute("SELECT cell_id FROM sensors WHERE id = ?", (sensor_id,)).fetchone()
        if not row:
            return None
        for finding in TrendAnalyzer(self.db).get_drift_status(row[0]):
            if finding["sensor_id"] == sensor_id:
                return finding
        return None

    def get_all_confidence(self, cell_id: int | None = None) -> list[dict]:
        query = "SELECT id FROM sensors WHERE active = 1"
        params = ()
        if cell_id is not None:
            query += " AND cell_id = ?"
            params = (cell_id,)
        return [
            self.get_confidence(sensor_id)
            for (sensor_id,) in self.db.execute(query, params).fetchall()
        ]

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="sensor_confidence",
            display_name="Sensor Confidence",
            purpose=(
                "Combines a sensor's calibration-due proximity and current drift status (both "
                "already tracked/alerted elsewhere) into one high/medium/low trust signal per "
                "sensor, instead of treating every currently-valid reading as equally trustworthy."
            ),
            data_produced=["per-sensor confidence level with the real factors behind it"],
            actions_possible=[
                "get confidence for one sensor", "get confidence for every active sensor in a cell",
            ],
            limits_and_safety=(
                "Purely informational — NEVER changes dosing or control-loop behavior. The "
                "'never dose on a single reading, require 3 consistent readings' rule and the "
                "recovery ladder's retry logic are unconditional safety gates, not tunable by "
                "this score. Synthesizes two signals that already alert on their own "
                "(calibration_due via core/maintenance.py, drift via core/trend_analyzer.py) "
                "rather than introducing new detection — this doesn't decide anything a human "
                "or the control loop wasn't already going to be told about, it just answers "
                "'how much should I trust this reading right now' in one place."
            ),
            example_questions=[
                "How much should I trust the pH reading right now?",
                "Which sensors have low confidence?",
            ],
            verification_evidence=[
                "scenarios.py::scenario_sensor_confidence — confirmed a sensor with no "
                "calibration_due set and no drift flagged reports 'high'; a sensor with "
                "calibration_due within 7 days reports 'medium' with a real factor string; a "
                "sensor with calibration_due already past reports 'low'; a sensor currently "
                "flagged by trend_analyzer as drifting reports 'low' regardless of its "
                "calibration status, with the real z-score cited in its factors.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure reasoning layer over existing data, no hardware of its own
