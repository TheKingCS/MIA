"""
MIA Homestead — Cost / Profitability Accounting
v0.1

Yield is tracked (yield_events); the actual economics weren't. Real gap
found while building this: revenue_transactions has a full schema and
is already READ by viewer/export_dashboard_state.py and
export_home_snapshot.py, but nothing anywhere WROTE to it — no
record_revenue() existed, and it had zero capability registration
(never in main.py's all_describables), a real structural gap CLAUDE.md's
own rule 2 exists to prevent. Fixed here, not just cost/profitability
added alongside it.

v0.2 (docs/SUSTAINING_FEATURES.md #24, 2026-09-03): inventory_transactions
now has a real, nullable cell_id (traced through dosing_events for the
one consumption path that's genuinely per-cell — dosing). Passing
cell_id to get_cost_summary()/get_profitability_summary() now gives a
REAL per-cell breakdown, honestly scoped to dosing consumption only —
a restock, repair part, or any pre-migration historical transaction
has no cell_id and is correctly excluded from a per-cell view, not
silently folded in. Omit cell_id for the original system-wide total,
unaffected by any of this. Revenue was already cell-attributed via
yield_events/revenue_transactions.cell_id.

Feeding cost (core/fish_health.py's feeding_events) is deliberately NOT
cross-referenced into cost here either — food_type is free text, not a
real foreign key into inventory_items, and guessing a unit conversion
(feeding logged in oz vs. inventory tracked in g/each/ml) would be a
fragile, likely-wrong estimate dressed up as a real number. Left as a
known, stated gap rather than a confident wrong one.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.finance_tracker")


class FinanceTracker(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    # ---------- Revenue ----------

    def record_revenue(self, item: str, quantity: float, unit: str, unit_price: float,
                        cell_id: int = None, yield_event_id: int = None,
                        channel: str = None, notes: str = None) -> int:
        total_amount = quantity * unit_price
        cur = self.db.execute(
            "INSERT INTO revenue_transactions (cell_id, yield_event_id, item, quantity, unit, "
            "unit_price, total_amount, channel, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cell_id, yield_event_id, item, quantity, unit, unit_price, total_amount, channel, notes),
        )
        self.db.commit()
        logger.info("Revenue recorded: %s x%s %s @ %s = $%.2f", item, quantity, unit, unit_price, total_amount)
        return cur.lastrowid

    def get_revenue_summary(self, days: int = 30, cell_id: int = None) -> dict:
        self.db.row_factory = sqlite3.Row
        q = "SELECT * FROM revenue_transactions WHERE timestamp >= datetime('now', ?)"
        params = [f"-{days} days"]
        if cell_id is not None:
            q += " AND cell_id = ?"
            params.append(cell_id)
        q += " ORDER BY timestamp DESC"
        rows = self.db.execute(q, params).fetchall()
        total = sum(r["total_amount"] for r in rows)
        return {"transactions": [dict(r) for r in rows], "total_revenue": total, "window_days": days}

    # ---------- Cost ----------

    def get_cost_summary(self, days: int = 30, cell_id: int = None) -> dict:
        """Real per-cell breakdown when cell_id is given (docs/
        SUSTAINING_FEATURES.md #24) — inventory_transactions.cell_id is
        real for dosing consumption (traced through dosing_events),
        honestly NULL for anything not tied to one cell (a restock, a
        repair part) or a historical row from before this column
        existed. A cell_id filter therefore only ever sees dosing-
        consumption cost for that cell, explicitly noted below, not
        silently presented as total cost for that cell. Omitting
        cell_id keeps the original system-wide total, unaffected by
        this. Only counts consumption (change_qty < 0) of items with a
        real, known unit_cost; items consumed without a known cost are
        excluded from the total and listed separately, never silently
        treated as $0."""
        q = ("SELECT ii.category, ii.name, ii.unit_cost, -it.change_qty as consumed "
             "FROM inventory_transactions it JOIN inventory_items ii ON ii.id = it.item_id "
             "WHERE it.change_qty < 0 AND it.timestamp >= datetime('now', ?)")
        params = [f"-{days} days"]
        if cell_id is not None:
            q += " AND it.cell_id = ?"
            params.append(cell_id)
        rows = self.db.execute(q, params).fetchall()

        total_cost = 0.0
        by_category: dict[str, float] = {}
        unknown_cost_items: set[str] = set()
        for category, name, unit_cost, consumed in rows:
            if unit_cost is None:
                unknown_cost_items.add(name)
                continue
            cost = unit_cost * consumed
            total_cost += cost
            by_category[category] = by_category.get(category, 0.0) + cost

        return {
            "total_cost": round(total_cost, 2),
            "by_category": {k: round(v, 2) for k, v in by_category.items()},
            "items_with_unknown_cost": sorted(unknown_cost_items),
            "window_days": days,
            "cell_id": cell_id,
            "note": (
                "system-wide total across all consumption" if cell_id is None else
                "only dosing consumption attributed to this cell — a restock, repair part, or "
                "any pre-migration historical row has no cell_id and is correctly excluded here, "
                "not silently folded into this cell's total"
            ),
        }

    def get_profitability_summary(self, days: int = 30, cell_id: int = None) -> dict:
        revenue = self.get_revenue_summary(days, cell_id=cell_id)
        cost = self.get_cost_summary(days, cell_id=cell_id)
        return {
            "total_revenue": revenue["total_revenue"],
            "total_cost": cost["total_cost"],
            "net_margin": round(revenue["total_revenue"] - cost["total_cost"], 2),
            "items_with_unknown_cost": cost["items_with_unknown_cost"],
            "window_days": days,
            "cell_id": cell_id,
            "note": (
                (
                    "System-wide: revenue and cost both cover every cell. Feeding costs "
                    "(core/fish_health.py) aren't included — no reliable unit-cost link exists "
                    "from feeding_events to inventory_items yet."
                ) if cell_id is None else (
                    "Per-cell (docs/SUSTAINING_FEATURES.md #24): revenue is real cell-attributed "
                    "revenue; cost is ONLY dosing consumption traced to this cell — a restock, "
                    "repair part, or pre-migration historical transaction has no cell_id and is "
                    "correctly excluded, so this margin may overstate profitability if real "
                    "non-dosing costs (e.g. a repair) were actually attributable to this cell. "
                    "Feeding costs aren't included here either, same reason as system-wide."
                )
            ),
        }

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="finance_tracker",
            display_name="Cost / Profitability Accounting",
            purpose=(
                "Ties real inventory consumption cost to real recorded revenue for a genuine "
                "profitability picture, not just yield or revenue in isolation. Also the first "
                "real write path for revenue_transactions — that table existed and was already "
                "read by the dashboard/home-snapshot exporters, but nothing ever wrote to it."
            ),
            data_produced=["revenue transactions", "consumable cost by category (system-wide or per-cell)", "net margin over a window"],
            actions_possible=[
                "record a real revenue transaction", "get revenue for a window (system-wide or per-cell)",
                "get consumable cost for a window (system-wide or per-cell, by category)",
                "get a combined profitability summary (revenue - cost) for a window, system-wide or per-cell",
            ],
            limits_and_safety=(
                "Purely a logging/reasoning layer — never touches dosing, actuators, or any "
                "control-loop decision. Per-cell cost (v0.2) is honestly scoped to dosing "
                "consumption only — inventory_transactions.cell_id is real for dosing (traced "
                "through dosing_events) but NULL for a restock, repair part, or pre-migration "
                "historical row, all correctly excluded from a per-cell total rather than "
                "silently folded in. Items consumed without a known unit_cost are excluded "
                "from the total and listed separately, never silently counted as $0. Feeding "
                "costs are deliberately not included — no reliable link from feeding_events' "
                "free-text food_type to a real inventory_items unit cost exists yet."
            ),
            example_questions=[
                "What's our profit margin this month?",
                "How much have we spent on consumables this month?",
                "Log a sale: 5 lbs of lettuce at $4/lb through the farmers market",
            ],
            verification_evidence=[
                "scenarios.py::scenario_cost_profitability — confirmed record_revenue() computes "
                "total_amount correctly and get_revenue_summary() reflects it; confirmed "
                "get_cost_summary() correctly sums real seeded consumption cost for items with a "
                "known unit_cost, correctly EXCLUDES an item with no known unit_cost from the "
                "total while listing it separately (not silently treated as $0); confirmed "
                "get_profitability_summary() nets real revenue minus real cost correctly. "
                "scenarios.py::scenario_per_crop_profitability — confirmed a per-cell cost/"
                "profitability breakdown correctly isolates one cell's real dosing consumption "
                "from another's, and correctly excludes a non-cell-attributed transaction "
                "(e.g. a restock) from a per-cell total.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure logging/reasoning layer, no hardware of its own
