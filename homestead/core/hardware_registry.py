"""
MIA Homestead — Hardware Needs Registry
v0.1

Collects `describe_hardware_requirements()` from every loaded module
and service into a running bill of materials. This is what directly
answers "what do I need to buy" without ever reconstructing a shopping
list from memory or scattered notes after the fact — every module
declared its own needs the moment it was written.

Call register_all() alongside CapabilityRegistry.register_all() in
main.py. Query the aggregate BOM via render_bom() or the assistant's
get_hardware_needs_list tool.
"""

import logging
import sqlite3

from contracts.capability import Describable, HardwareRequirement

logger = logging.getLogger("mia_homestead.hardware_registry")


class HardwareRegistry:
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    def register(self, item: Describable, module_id: str) -> list[HardwareRequirement]:
        reqs = item.describe_hardware_requirements()
        for req in reqs:
            self._log_hardware_change(module_id, req)
            self._persist(module_id, req)
        return reqs

    def _log_hardware_change(self, module_id: str, req: HardwareRequirement) -> None:
        existing = self.db.execute(
            "SELECT quantity, est_unit_cost, purpose FROM hardware_requirements "
            "WHERE module_id = ? AND item = ?",
            (module_id, req.item),
        ).fetchone()

        if existing is None:
            self.db.execute(
                "INSERT INTO system_changelog (module_id, change_type, field_name, old_value, new_value) "
                "VALUES (?, 'first_registered', 'hardware', NULL, ?)",
                (module_id, f"{req.item} (qty {req.quantity})"),
            )
            self.db.commit()
            return

        old_qty, old_cost, old_purpose = existing
        if old_qty != req.quantity:
            self._log_change(module_id, req.item, "quantity", old_qty, req.quantity)
        if old_cost != req.est_unit_cost:
            self._log_change(module_id, req.item, "est_unit_cost", old_cost, req.est_unit_cost)

    def _log_change(self, module_id: str, item: str, field: str, old_value, new_value) -> None:
        self.db.execute(
            "INSERT INTO system_changelog (module_id, change_type, field_name, old_value, new_value) "
            "VALUES (?, 'hardware_changed', ?, ?, ?)",
            (module_id, f"{item}.{field}", str(old_value), str(new_value)),
        )
        self.db.commit()
        logger.info("Changelog: %s %s.%s changed: %s -> %s", module_id, item, field, old_value, new_value)

    def register_all(self, items_with_ids: list[tuple[Describable, str]]) -> int:
        total = 0
        for item, module_id in items_with_ids:
            total += len(self.register(item, module_id))
        return total

    def _persist(self, module_id: str, req: HardwareRequirement) -> None:
        self.db.execute(
            """
            INSERT INTO hardware_requirements
            (module_id, item, category, quantity, purpose, est_unit_cost, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(module_id, item) DO UPDATE SET
                category = excluded.category,
                quantity = excluded.quantity,
                purpose = excluded.purpose,
                est_unit_cost = excluded.est_unit_cost,
                notes = excluded.notes,
                updated_at = datetime('now')
            """,
            (module_id, req.item, req.category, req.quantity, req.purpose,
             req.est_unit_cost, req.notes),
        )
        self.db.commit()

    @staticmethod
    def render_bom(db_conn: sqlite3.Connection, group_by_module: bool = False) -> str:
        """The actual shopping list. Grouped by module by default is
        useful while building; grouped/aggregated by item is useful once
        you're actually about to order (same item needed by two modules
        should be bought once, in the combined quantity)."""
        if group_by_module:
            rows = db_conn.execute(
                "SELECT module_id, item, category, quantity, purpose, est_unit_cost, notes "
                "FROM hardware_requirements ORDER BY module_id, category"
            ).fetchall()
            lines = []
            current_module = None
            for module_id, item, category, qty, purpose, cost, notes in rows:
                if module_id != current_module:
                    lines.append(f"\n== {module_id} ==")
                    current_module = module_id
                cost_str = f" (~${cost:.2f} ea)" if cost else ""
                lines.append(f"  - {qty}x {item} [{category}]{cost_str} — {purpose}")
                if notes:
                    lines.append(f"      note: {notes}")
            return "\n".join(lines).strip()

        # Aggregated by item name — the actual buy-this-once list
        rows = db_conn.execute(
            """
            SELECT item, category, SUM(quantity) as total_qty,
                   AVG(est_unit_cost) as avg_cost,
                   GROUP_CONCAT(DISTINCT module_id) as needed_by
            FROM hardware_requirements
            GROUP BY item, category
            ORDER BY category, item
            """
        ).fetchall()
        lines = []
        running_total = 0.0
        current_category = None
        for item, category, total_qty, avg_cost, needed_by in rows:
            if category != current_category:
                lines.append(f"\n== {category.upper()} ==")
                current_category = category
            cost_str = ""
            if avg_cost:
                subtotal = avg_cost * total_qty
                running_total += subtotal
                cost_str = f" — ~${subtotal:.2f}"
            lines.append(f"  {total_qty}x {item}{cost_str}  (needed by: {needed_by})")
        if running_total:
            lines.append(f"\nEstimated total: ~${running_total:.2f}")
        return "\n".join(lines).strip()

    @staticmethod
    def get_all(db_conn: sqlite3.Connection) -> list[dict]:
        db_conn.row_factory = sqlite3.Row
        rows = db_conn.execute("SELECT * FROM hardware_requirements ORDER BY category, item").fetchall()
        return [dict(r) for r in rows]
