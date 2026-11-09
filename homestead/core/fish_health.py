"""
MIA Homestead — Fish Health, Feeding, and Mortality Tracking
v0.1

This is called an aquaponics manager, but everything else in this
codebase is water-chemistry/plant-centric — nothing tracks the fish
themselves. That's not just a completeness gap: bioload (how much
waste the fish are actually producing) is exactly what drives the
nitrogen cycle core/biofilter_model.py reasons about, and that model
currently has no real signal for it beyond test-kit readings after the
fact — get_feeding_trend() below is a real, honest step toward closing
that loop (a feeding-rate signal, not a precise bioload number).

Same reasoning as core/biofilter_model.py's water_quality_tests: real
periodic manual entries logged by a human, not fabricated continuous
data — there's no cheap way to continuously weigh or count fish any
more than there's a cheap continuous ammonia sensor.
"""

import logging
import sqlite3
from datetime import datetime, timedelta

from contracts.capability import Describable
from contracts.mia_homestead_contract import Severity, raise_alert

logger = logging.getLogger("mia_homestead.fish_health")

# Absolute-count fallback threshold, used only when a tank's
# quantity_stocked isn't known — deliberately conservative (a real,
# if less precise, safety signal beats none).
MORTALITY_ABSOLUTE_THRESHOLD = 3
# Population-relative threshold, used when quantity_stocked IS known —
# a real percentage is a much more meaningful signal than an absolute
# count alone.
MORTALITY_PERCENT_THRESHOLD = 10.0
MORTALITY_WINDOW_DAYS = 7

# Feeding-trend comparison windows — same recent-vs-baseline shape
# core/trend_analyzer.py already uses, by READING COUNT so it's robust
# to whatever the real feeding cadence turns out to be.
FEEDING_RECENT_COUNT = 3
FEEDING_BASELINE_COUNT = 10


class FishHealth(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    # ---------- Feeding ----------

    def record_feeding(self, cell_id: int, amount: float, unit: str = "oz",
                        food_type: str = None, notes: str = None) -> int:
        cur = self.db.execute(
            "INSERT INTO feeding_events (cell_id, amount, unit, food_type, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (cell_id, amount, unit, food_type, notes),
        )
        self.db.commit()
        return cur.lastrowid

    def get_feeding_history(self, cell_id: int, days: int = 7) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute(
            "SELECT * FROM feeding_events WHERE cell_id = ? AND timestamp >= datetime('now', ?) "
            "ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_feeding_trend(self, cell_id: int) -> dict:
        """A real, honest feeding-rate signal — recent-window average
        amount vs. an older baseline window, same comparison shape
        core/trend_analyzer.py already uses for sensor drift. This is
        NOT a precise bioload calculation (that would need real fish
        weight/count data this system doesn't have) — just "is feeding
        trending up, down, or flat," presented as exactly that, not
        overclaimed as more."""
        rows = self.db.execute(
            "SELECT amount FROM feeding_events WHERE cell_id = ? AND amount IS NOT NULL "
            "ORDER BY id DESC LIMIT ?",
            (cell_id, FEEDING_RECENT_COUNT + FEEDING_BASELINE_COUNT),
        ).fetchall()
        values = [r[0] for r in rows]
        if len(values) < FEEDING_RECENT_COUNT + FEEDING_BASELINE_COUNT:
            return {"trend": "insufficient_data", "feedings_logged": len(values)}

        recent = values[:FEEDING_RECENT_COUNT]
        baseline = values[FEEDING_RECENT_COUNT:]
        recent_avg = sum(recent) / len(recent)
        baseline_avg = sum(baseline) / len(baseline)
        if baseline_avg == 0:
            return {"trend": "insufficient_data", "feedings_logged": len(values)}

        pct_change = ((recent_avg - baseline_avg) / baseline_avg) * 100
        if pct_change > 20:
            trend = "increasing"
        elif pct_change < -20:
            trend = "decreasing"
        else:
            trend = "stable"
        return {
            "trend": trend, "recent_avg": round(recent_avg, 2), "baseline_avg": round(baseline_avg, 2),
            "pct_change": round(pct_change, 1), "feedings_logged": len(values),
        }

    # ---------- Mortality & health observations ----------

    def record_mortality(self, cell_id: int, count: int, cause: str = None, notes: str = None) -> int:
        description = f"{count} fish died" + (f" — suspected cause: {cause}" if cause else "")
        cur = self.db.execute(
            "INSERT INTO fish_health_events (cell_id, event_type, count, description, notes) "
            "VALUES (?, 'mortality', ?, ?, ?)",
            (cell_id, count, description, notes),
        )
        self.db.commit()
        logger.info("Mortality logged for cell %s: %s", cell_id, description)
        return cur.lastrowid

    def record_health_observation(self, cell_id: int, description: str, notes: str = None) -> int:
        cur = self.db.execute(
            "INSERT INTO fish_health_events (cell_id, event_type, description, notes) "
            "VALUES (?, 'observation', ?, ?)",
            (cell_id, description, notes),
        )
        self.db.commit()
        return cur.lastrowid

    def get_mortality_history(self, cell_id: int, days: int = 30) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute(
            "SELECT * FROM fish_health_events WHERE cell_id = ? AND event_type = 'mortality' "
            "AND timestamp >= datetime('now', ?) ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_health_events(self, cell_id: int, days: int = 30) -> list[dict]:
        """Observations only — mortality has its own get_mortality_history()
        above, and the two are meant to be complementary fields (see
        _tool_get_fish_health_summary), not overlapping ones."""
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute(
            "SELECT * FROM fish_health_events WHERE cell_id = ? AND event_type = 'observation' "
            "AND timestamp >= datetime('now', ?) ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return [dict(r) for r in rows]

    def check_mortality_spike(self) -> list[dict]:
        """Called periodically (main.py) — a real, deduplicated alert
        (via the existing raise_alert()) when recent mortality crosses a
        real threshold. Uses the population-relative threshold when
        tanks.quantity_stocked is known (a real percentage is a much
        more meaningful signal); falls back to the absolute-count
        threshold, honestly, when it isn't — never silently assumes a
        population size it doesn't have."""
        findings = []
        tanks = self.db.execute(
            "SELECT cell_id, quantity_stocked FROM tanks WHERE stocked_date IS NOT NULL"
        ).fetchall()
        for cell_id, quantity_stocked in tanks:
            total = self.db.execute(
                "SELECT COALESCE(SUM(count), 0) FROM fish_health_events WHERE cell_id = ? "
                "AND event_type = 'mortality' AND timestamp >= datetime('now', ?)",
                (cell_id, f"-{MORTALITY_WINDOW_DAYS} days"),
            ).fetchone()[0]
            if total == 0:
                continue

            if quantity_stocked:
                pct = (total / quantity_stocked) * 100
                if pct < MORTALITY_PERCENT_THRESHOLD:
                    continue
                message = (
                    f"cell {cell_id}: {total} fish died in the last {MORTALITY_WINDOW_DAYS} days "
                    f"({pct:.1f}% of the {quantity_stocked} stocked) — worth investigating"
                )
            else:
                if total < MORTALITY_ABSOLUTE_THRESHOLD:
                    continue
                message = (
                    f"cell {cell_id}: {total} fish died in the last {MORTALITY_WINDOW_DAYS} days "
                    f"(population size not tracked — set tanks.quantity_stocked for a precise "
                    f"percentage) — worth investigating"
                )
            raise_alert(self.db, "fish_health", Severity.WARNING, message, self.notifier)
            findings.append({"cell_id": cell_id, "mortality_count": total})
        return findings

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="fish_health",
            display_name="Fish Health, Feeding, and Mortality Tracking",
            purpose=(
                "Tracks the fish themselves — feeding events, mortality, and health "
                "observations — closing the biggest gap in an otherwise water-chemistry/"
                "plant-centric system, and giving core/biofilter_model.py a real feeding-rate "
                "signal instead of none."
            ),
            data_produced=["feeding history", "feeding trend", "mortality history", "health observations"],
            actions_possible=[
                "log a feeding event", "log fish mortality", "log a fish health observation",
                "get the feeding trend for a cell (recent vs. baseline rate)",
                "remind (via a real, deduplicated alert) when recent mortality crosses a real "
                "threshold — population-relative when tanks.quantity_stocked is known, an "
                "honest absolute-count fallback when it isn't",
            ],
            limits_and_safety=(
                "Purely a logging/reasoning layer — never touches dosing, actuators, or any "
                "control-loop decision. get_feeding_trend() is a rate signal (recent vs. "
                "baseline average), explicitly not a precise bioload calculation, which would "
                "need real fish weight/count data this system doesn't have. Mortality alerting "
                "never invents a population size — it uses the real percentage when "
                "quantity_stocked is set, and says so plainly when it falls back to an absolute "
                "count instead."
            ),
            example_questions=[
                "How much have the fish been fed this week?",
                "Has there been any fish mortality lately?",
                "Log 2 fish died today, looked lethargic beforehand",
            ],
            verification_evidence=[
                "scenarios.py::scenario_fish_health_tracking — confirmed feeding events log and "
                "summarize correctly; confirmed get_feeding_trend() correctly reports "
                "'increasing' from a real seeded rate change and 'insufficient_data' honestly "
                "when too few feedings are logged; confirmed check_mortality_spike() alerts on "
                "a real percentage when quantity_stocked is set, alerts on the absolute-count "
                "fallback when it isn't, and stays silent below both thresholds; confirmed "
                "health observations log and retrieve correctly.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure logging/reasoning layer, no hardware of its own
