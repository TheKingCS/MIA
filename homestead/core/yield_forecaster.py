"""
MIA Homestead — Multi-Week Yield Forecasting
v0.1

docs/SUSTAINING_FEATURES.md #22. BedPlantingManager.get_expected_vs_actual()
only ever compares expected vs actual AFTER harvest — nothing projects
forward while a planting is still growing, unlike commercial "crop
intelligence" platforms researched (IUNU LUNA, Root AI) that forecast
multi-weeks ahead.

Explicit uncertainty bands, not a fabricated confident date — same
honesty discipline core/biofilter_model.py already established for
exactly this reason (an 'insufficient_data' state, not a guessed one,
when there isn't enough real signal). The baseline comes from
species_profiles.days_to_maturity; the band widens from two REAL
signals already produced elsewhere (core/sensor_confidence.py's
per-sensor confidence level, and real stress-related alerts raised on
this cell during the planting's life) rather than a fabricated
statistical model this project has no real historical yield-vs-
conditions data to calibrate yet — that calibration is real future
work once real harvests accumulate, not built here.
"""

import logging
import sqlite3
from datetime import datetime, timedelta

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.yield_forecaster")

BASE_UNCERTAINTY_DAYS = 3       # never claim single-day precision, even with perfect signals
DAYS_PER_LOW_CONFIDENCE_SENSOR = 2
DAYS_PER_MEDIUM_CONFIDENCE_SENSOR = 1
DAYS_PER_STRESS_ALERT = 1
MAX_BAND_DAYS = 21              # a band this wide is functionally "we don't know" — capped, not unbounded


class YieldForecaster(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    def _module_ids_for_cell(self, cell_id: int) -> list[str]:
        """alerts.source is a module_id (free text, e.g.
        'cell_a_aquaponics'), not a cell_id — that mapping lives only in
        config/modules.yaml (same file core/self_audit.py already reads
        the same way). A cell can have multiple modules (aquaponics,
        climate, power, self-preservation all sharing one cell_id), so
        this is an approximation — an alert from that cell's power
        module could count toward its 'stress' signal too, not just
        water/climate — acceptable here since the message-content
        filter (stress/inconsistent) already narrows it, and this is a
        soft uncertainty-widening signal, never a hard gate."""
        import yaml
        from pathlib import Path
        config_path = Path(__file__).parent.parent / "config" / "modules.yaml"
        try:
            config = yaml.safe_load(config_path.read_text())
        except Exception:
            return []
        return [m["id"] for m in config.get("modules", []) if m.get("cell_id") == cell_id]

    def get_yield_forecast(self, planting_id: int) -> dict:
        self.db.row_factory = sqlite3.Row
        row = self.db.execute(
            "SELECT bp.*, sp.common_name, sp.days_to_maturity FROM bed_plantings bp "
            "JOIN species_profiles sp ON sp.id = bp.species_id WHERE bp.id = ?",
            (planting_id,),
        ).fetchone()
        if not row:
            return {"error": f"no planting {planting_id}"}
        planting = dict(row)

        if planting["status"] != "active":
            return {"error": f"planting {planting_id} is '{planting['status']}', not 'active' — nothing to forecast"}

        baseline_date = planting["expected_harvest_date"]
        if not baseline_date:
            if not planting["days_to_maturity"] or not planting["planted_date"]:
                return {
                    "planting_id": planting_id,
                    "status": "insufficient_data",
                    "note": (
                        f"no expected_harvest_date set and {planting['common_name']}'s "
                        "days_to_maturity or this planting's planted_date is unknown — "
                        "cannot forecast, not guessing a date from nothing"
                    ),
                }
            planted = datetime.fromisoformat(planting["planted_date"].replace(" ", "T"))
            baseline_date = (planted + timedelta(days=planting["days_to_maturity"])).isoformat(sep=" ")

        factors = []
        band_days = BASE_UNCERTAINTY_DAYS

        from core.sensor_confidence import SensorConfidence
        confidences = SensorConfidence(self.db).get_all_confidence(cell_id=planting["cell_id"])
        for c in confidences:
            if c["level"] == "low":
                band_days += DAYS_PER_LOW_CONFIDENCE_SENSOR
                factors.append(f"{c['sensor_type']} sensor confidence is low ({'; '.join(c['factors']) or 'flagged'})")
            elif c["level"] == "medium":
                band_days += DAYS_PER_MEDIUM_CONFIDENCE_SENSOR
                factors.append(f"{c['sensor_type']} sensor confidence is medium")

        module_ids = self._module_ids_for_cell(planting["cell_id"])
        stress_alerts = 0
        if module_ids:
            placeholders = ",".join("?" * len(module_ids))
            stress_alerts = self.db.execute(
                f"SELECT COUNT(*) FROM alerts WHERE source IN ({placeholders}) AND timestamp >= ? "
                "AND (message LIKE '%stress%' OR message LIKE '%inconsistent%')",
                (*module_ids, planting["planted_date"]),
            ).fetchone()[0]
        if stress_alerts:
            band_days += stress_alerts * DAYS_PER_STRESS_ALERT
            factors.append(f"{stress_alerts} stress/inconsistency alert(s) raised on this cell during this planting's life")

        band_days = min(band_days, MAX_BAND_DAYS)
        baseline_dt = datetime.fromisoformat(baseline_date.replace(" ", "T"))
        capped_note = " (capped — real signal quality suggests even less confidence than this)" if band_days == MAX_BAND_DAYS else ""

        return {
            "planting_id": planting_id,
            "grow_bed_name": planting["grow_bed_name"],
            "species": planting["common_name"],
            "baseline_expected_harvest_date": baseline_date,
            "earliest_likely": (baseline_dt - timedelta(days=band_days)).date().isoformat(),
            "latest_likely": (baseline_dt + timedelta(days=band_days)).date().isoformat(),
            "band_days": band_days,
            "factors": factors or ["no confidence or stress signals degrading the estimate — baseline uncertainty only"],
            "note": (
                f"uncertainty band widens from real sensor-confidence and stress-alert signals, "
                f"never from a fabricated statistical model — this project has no real "
                f"historical yield-vs-conditions data yet to calibrate one{capped_note}"
            ),
        }

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="yield_forecaster",
            display_name="Multi-Week Yield Forecasting",
            purpose=(
                "Projects a real, uncertainty-banded harvest-date estimate for an active planting, "
                "widened by real signals (sensor confidence, stress alerts) rather than a single "
                "fabricated confident date — nothing previously projected forward while a planting "
                "was still growing, only compared expected vs actual after the fact."
            ),
            data_produced=["a real harvest-date estimate with an explicit earliest/latest range for one active planting"],
            actions_possible=["forecast when an active planting is likely to be ready to harvest, with a real uncertainty range"],
            limits_and_safety=(
                "Read-only, purely informational — never touches planting/harvest/dosing logic. "
                "Never claims single-day precision (a minimum real band is always applied) and "
                "explicitly reports insufficient_data rather than guessing when no "
                "days_to_maturity or planted_date exists. The band widens from real signals "
                "already produced elsewhere (sensor_confidence, real alerts), never from a "
                "fabricated statistical model this project has no real historical data to "
                "calibrate yet."
            ),
            example_questions=["When will the lettuce in Bed A1 be ready?", "How confident are we in that harvest date?"],
            verification_evidence=["scenarios.py::scenario_yield_forecasting"],
        )

    def describe_hardware_requirements(self) -> list:
        return []
