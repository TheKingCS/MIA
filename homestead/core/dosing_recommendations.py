"""
MIA Homestead — Data-Driven Dosing/Climate Recommendations
v0.1

docs/SUSTAINING_FEATURES.md #23. The control loop is real but purely
reactive/threshold-based (dose when out of range, hold when
inconsistent) — nothing looks at trend + weather forecast together and
proactively suggests a check before a threshold is even crossed, the
kind of thing commercial platforms researched (Priva) advertise as
"data-driven recommendations" layered on top of a reactive climate
computer.

This is an ADVISORY layer only — reads two signals that already exist
(core/trend_analyzer.py's real z-score drift, core/weather_awareness.py's
real forecast check) and composes them into a human-readable suggestion.
It NEVER changes a dosing target, control parameter, or actuator state
itself — that stays behind approve_parameter_change()/experiments, this
project's own non-negotiable propose-then-human-approves gate
(CLAUDE.md rule 6). Suggestion only, same as
propose_experiments_for_underperformance().
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.dosing_recommendations")


class RecommendationEngine(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    def get_recommendations(self, cell_id: int = None) -> list[dict]:
        """Real recommendations composed from real, already-computed
        signals — never a new detection mechanism of its own. Empty
        list is an honest "nothing worth flagging right now", not a
        sign of failure."""
        recs = []
        recs.extend(self._drift_recommendations(cell_id))
        recs.extend(self._weather_recommendations(cell_id))
        return recs

    def _drift_recommendations(self, cell_id: int = None) -> list[dict]:
        from core.trend_analyzer import TrendAnalyzer
        drifts = TrendAnalyzer(self.db).get_drift_status(cell_id=cell_id)
        recs = []
        for d in drifts:
            recs.append({
                "type": "drift_advisory",
                "cell_id": d["cell_id"],
                "sensor_type": d["sensor_type"],
                "message": (
                    f"{d['sensor_type']} on cell {d['cell_id']} has been trending {d['direction']} "
                    f"(z-score {d['z_score']} vs. its own recent baseline) — still inside normal "
                    f"thresholds, but worth a proactive look before it crosses one."
                ),
                "source_signal": "trend_analyzer",
                "z_score": d["z_score"],
            })
        return recs

    def _weather_recommendations(self, cell_id: int = None) -> list[dict]:
        from core.weather_awareness import WeatherAwareness
        last_check = WeatherAwareness(self.db).get_last_check()
        if not last_check:
            return []
        recs = []
        if last_check["frost_risk"]:
            recs.append({
                "type": "weather_advisory",
                "cell_id": cell_id,
                "message": (
                    f"Frost risk in the current forecast (low {last_check['forecast_low_f']}°F) — "
                    "consider proactive supplemental heat or covering before it hits, rather than "
                    "reacting after a cold-stress reading."
                ),
                "source_signal": "weather_awareness",
            })
        if last_check["species_range_violation"]:
            recs.append({
                "type": "weather_advisory",
                "cell_id": cell_id,
                "message": (
                    f"Forecast conflicts with a currently-planted species' documented range: "
                    f"{last_check['species_range_violation']} — worth a proactive check."
                ),
                "source_signal": "weather_awareness",
            })
        return recs

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="dosing_recommendations",
            display_name="Data-Driven Dosing/Climate Recommendations",
            purpose=(
                "Composes real drift (trend_analyzer) and weather-forecast (weather_awareness) "
                "signals into a proactive, human-readable suggestion — the control loop stays "
                "purely reactive/threshold-based; this is the advisory layer commercial "
                "platforms researched (Priva) advertise as 'data-driven recommendations' on top "
                "of that."
            ),
            data_produced=["proactive dosing/climate advisories, composed from already-computed real signals"],
            actions_possible=["get real proactive recommendations for a cell or the whole system, based on current drift and weather signals"],
            limits_and_safety=(
                "Suggestion-only — NEVER changes a dosing target, control parameter, or "
                "actuator state. Dosing targets stay behind approve_parameter_change()/"
                "experiments, this project's own non-negotiable propose-then-human-approves "
                "gate (CLAUDE.md rule 6); this module cannot and does not bypass it. Composes "
                "existing signals only — introduces no new detection mechanism of its own, so "
                "it's exactly as reliable (and exactly as limited) as trend_analyzer and "
                "weather_awareness already are."
            ),
            example_questions=["Any proactive recommendations right now?", "Should I be worried about anything before it becomes a real problem?"],
            verification_evidence=["scenarios.py::scenario_dosing_recommendations"],
        )

    def describe_hardware_requirements(self) -> list:
        return []
