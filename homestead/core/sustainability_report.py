"""
MIA Homestead — Resource-Efficiency Reporting
v0.1

docs/SUSTAINING_FEATURES.md #20. Water usage is already logged
(bed_planting.record_water_usage()) and yield is already logged
(traceability.record_yield()) — nothing computed efficiency from
either. This composes both into a real gallons-per-lb figure.

Deliberately water-only, not water+energy: power_telemetry only ever
logs solar GENERATION and battery SOC (drivers/simulator.py), never
actual load/consumption — there's no real watts-drawn signal anywhere
in this system, and SAFETY_SPEC.md's own open items list "battery
capacity" as not yet sized. A kWh-per-lb figure would have to guess a
capacity number that doesn't exist yet — exactly the kind of fabricated
number this project's own established discipline (finance_tracker's
unknown-cost exclusion, biofilter's uncertainty bands) refuses to
produce. Energy efficiency is a real, named follow-up once load
metering exists as real hardware, not built here.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.sustainability_report")


class SustainabilityReport(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    def get_water_efficiency(self, cell_id: int = None, days: int = 30) -> dict:
        """Gallons used per lb yielded, over a real window. Only yield
        rows logged in 'lb' count toward the yield side — a count/oz
        yield (e.g. fish by count) can't honestly convert to lb without
        a real weight, so it's excluded from the ratio and listed
        separately rather than silently dropped or guessed."""
        water_q = "SELECT COALESCE(SUM(amount_gallons), 0) FROM water_usage_events WHERE timestamp >= datetime('now', ?)"
        yield_q = ("SELECT COALESCE(SUM(quantity), 0) FROM yield_events "
                   "WHERE unit = 'lb' AND timestamp >= datetime('now', ?)")
        excluded_q = ("SELECT item, unit, SUM(quantity) FROM yield_events "
                      "WHERE unit != 'lb' AND unit IS NOT NULL AND timestamp >= datetime('now', ?) "
                      "GROUP BY item, unit")
        params_water = [f"-{days} days"]
        params_yield = [f"-{days} days"]
        params_excluded = [f"-{days} days"]
        if cell_id is not None:
            water_q += " AND cell_id = ?"
            yield_q += " AND cell_id = ?"
            excluded_q += " AND cell_id = ?"
            params_water.append(cell_id)
            params_yield.append(cell_id)
            params_excluded.append(cell_id)

        gallons_used = self.db.execute(water_q, params_water).fetchone()[0]
        lb_yielded = self.db.execute(yield_q, params_yield).fetchone()[0]
        excluded = [
            {"item": item, "unit": unit, "quantity": qty}
            for item, unit, qty in self.db.execute(excluded_q, params_excluded).fetchall()
        ]

        # Real bug caught by a live smoke test, not just scenarios: gallons_used == 0
        # with real yield present computed a literal 0.0 ratio — mathematically
        # correct but misleading, since it reads as "perfect efficiency" rather
        # than "no water usage has actually been logged in this window." Both
        # sides need real, positive data before the ratio means anything.
        gallons_per_lb = (
            round(gallons_used / lb_yielded, 2) if lb_yielded > 0 and gallons_used > 0 else None
        )

        if lb_yielded == 0:
            note = "no lb-unit yield logged in this window — gallons_per_lb is unavailable, not zero"
        elif gallons_used == 0:
            note = "no water usage logged in this window — gallons_per_lb is unavailable, not a real 0.0"
        else:
            note = (
                "gallons_per_lb is water use divided by lb-unit yield only; "
                "non-lb yield (count/oz) is listed separately, not converted or dropped"
            )

        return {
            "window_days": days,
            "cell_id": cell_id,
            "gallons_used": round(gallons_used, 2),
            "lb_yielded": round(lb_yielded, 2),
            "gallons_per_lb": gallons_per_lb,
            "excluded_non_lb_yield": excluded,
            "note": note,
        }

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="sustainability_report",
            display_name="Resource-Efficiency Reporting",
            purpose=(
                "Computes real water-use efficiency (gallons per lb yielded) from data already "
                "logged elsewhere (water_usage_events, yield_events) — neither had anything "
                "computing efficiency from it before this."
            ),
            data_produced=["water-use efficiency (gallons per lb yielded), per cell or system-wide"],
            actions_possible=["get a real water-use efficiency figure for a cell or the whole system, over a real window"],
            limits_and_safety=(
                "Read-only, purely informational — never touches irrigation or control logic. "
                "Deliberately does NOT report an energy-per-yield figure: power_telemetry only "
                "logs solar generation and battery SOC, never real load/consumption, and battery "
                "capacity isn't sized yet (SAFETY_SPEC.md's own open item) — a kWh figure would "
                "have to guess a number that doesn't exist. Non-lb-unit yield (count/oz) is "
                "listed separately, never silently converted or dropped from the ratio."
            ),
            example_questions=["How much water per pound of lettuce are we using?", "What's our water-use efficiency this month?"],
            verification_evidence=["scenarios.py::scenario_water_efficiency_reporting"],
        )

    def describe_hardware_requirements(self) -> list:
        return []
