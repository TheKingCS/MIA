"""
MIA Homestead — Inventory Manager
v0.1

Tracks stock for anything the system consumes or might need replaced:
dosing chemicals, spare sensors, spare parts. Raises alerts through the
same notification path as everything else when stock drops below
reorder threshold — a dosing chemical running out unnoticed is exactly
the kind of failure this whole system exists to prevent.

Not wired to any real ordering API — "order" here means creating a
tracked record of intent (what, how much, when), which you action
manually. Real Amazon/supplier API integration is a clear future step
once a specific supplier workflow is chosen.
"""

import logging
import sqlite3
from datetime import datetime

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.inventory")


class InventoryManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier

    def add_item(
        self, name: str, category: str, unit: str = "each",
        quantity_on_hand: float = 0, reorder_threshold: float = 0,
        reorder_quantity: float = 0, unit_cost: float = None,
        supplier: str = None, supplier_url: str = None, sku: str = None,
    ) -> int:
        cur = self.db.execute(
            """
            INSERT INTO inventory_items
            (sku, name, category, unit, quantity_on_hand, reorder_threshold,
             reorder_quantity, unit_cost, supplier, supplier_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sku, name, category, unit, quantity_on_hand, reorder_threshold,
             reorder_quantity, unit_cost, supplier, supplier_url),
        )
        self.db.commit()
        return cur.lastrowid

    def adjust_stock(self, item_id: int, delta: float, reason: str, reference: str = None) -> None:
        self.db.execute(
            "UPDATE inventory_items SET quantity_on_hand = quantity_on_hand + ? WHERE id = ?",
            (delta, item_id),
        )
        self.db.execute(
            "INSERT INTO inventory_transactions (item_id, change_qty, reason, reference) "
            "VALUES (?, ?, ?, ?)",
            (item_id, delta, reason, reference),
        )
        self.db.commit()
        self._check_reorder(item_id)

    def record_consumption_from_dose(self, dose_type: str, amount_ml: float, dosing_event_id: int) -> None:
        """Called after a dosing event to decrement matching inventory,
        keyed by item name containing the dose_type string. If no
        matching inventory item exists, this is a no-op — inventory
        tracking is opt-in per chemical, not mandatory for control logic
        to function."""
        row = self.db.execute(
            "SELECT id FROM inventory_items WHERE name LIKE ? AND category = 'chemical' LIMIT 1",
            (f"%{dose_type}%",),
        ).fetchone()
        if row:
            self.adjust_stock(
                row[0], -amount_ml, "dosing_consumption", f"dosing_event:{dosing_event_id}"
            )

    def _check_reorder(self, item_id: int) -> None:
        row = self.db.execute(
            "SELECT name, quantity_on_hand, reorder_threshold, unit FROM inventory_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if not row:
            return
        name, qty, threshold, unit = row
        if qty <= threshold:
            message = f"{name}: {qty}{unit or ''} on hand, at or below reorder threshold ({threshold}{unit or ''})"
            logger.warning("LOW STOCK: %s", message)
            if self.notifier:
                self.notifier.dispatch("warning", message, source="inventory")

    def get_low_stock(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, name, category, quantity_on_hand, reorder_threshold, "
            "reorder_quantity, unit, supplier FROM inventory_items "
            "WHERE quantity_on_hand <= reorder_threshold"
        ).fetchall()
        cols = ["id", "name", "category", "quantity_on_hand", "reorder_threshold",
                "reorder_quantity", "unit", "supplier"]
        return [dict(zip(cols, r)) for r in rows]

    def get_status(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, name, category, quantity_on_hand, unit, reorder_threshold FROM inventory_items"
        ).fetchall()
        cols = ["id", "name", "category", "quantity_on_hand", "unit", "reorder_threshold"]
        return [dict(zip(cols, r)) for r in rows]

    def record_order(self, item_id: int, quantity: float, cost: float = None,
                      expected_arrival: str = None, notes: str = None) -> int:
        """Logs an order you've already placed yourself — skips the
        approval queue since you're the one who just did it."""
        cur = self.db.execute(
            "INSERT INTO inventory_orders (item_id, quantity, cost, expected_arrival, notes, status) "
            "VALUES (?, ?, ?, ?, ?, 'ordered')",
            (item_id, quantity, cost, expected_arrival, notes),
        )
        self.db.commit()
        logger.info("Order recorded: item_id=%s qty=%s (status=ordered)", item_id, quantity)
        return cur.lastrowid

    def receive_order(self, order_id: int) -> None:
        row = self.db.execute(
            "SELECT item_id, quantity FROM inventory_orders WHERE id = ?", (order_id,)
        ).fetchone()
        if not row:
            return
        item_id, quantity = row
        self.db.execute(
            "UPDATE inventory_orders SET status = 'received', received_at = datetime('now') "
            "WHERE id = ?", (order_id,),
        )
        self.db.commit()
        self.adjust_stock(item_id, quantity, "restock", f"order:{order_id}")

    # ---------- To-Order queue (approve/deny workflow) ----------

    def propose_reorder(self, item_id: int, quantity: float = None, note: str = None) -> int:
        """Creates a pending order proposal — NOT placed, NOT counted as
        stock, sits in the to-order queue until approve_order() or
        deny_order() is called. This is the automated path; record_order()
        above is the 'I already bought it myself' path."""
        row = self.db.execute(
            "SELECT reorder_quantity, unit_cost FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"no inventory item with id {item_id}")
        default_qty, unit_cost = row
        qty = quantity if quantity is not None else default_qty
        est_cost = (unit_cost * qty) if unit_cost else None

        cur = self.db.execute(
            "INSERT INTO inventory_orders (item_id, quantity, cost, notes, status) "
            "VALUES (?, ?, ?, ?, 'proposed')",
            (item_id, qty, est_cost, note),
        )
        self.db.commit()
        logger.info("Proposed reorder: item_id=%s qty=%s (pending approval)", item_id, qty)
        return cur.lastrowid

    def auto_propose_reorders(self) -> int:
        """Scans low-stock items and proposes a reorder for any that
        don't already have an open proposal or order in flight. Returns
        count of new proposals created. Call this periodically (e.g.
        from main.py's maintenance scan) — it never places anything,
        only queues it for your approval."""
        low_stock = self.get_low_stock()
        created = 0
        for item in low_stock:
            existing = self.db.execute(
                "SELECT id FROM inventory_orders WHERE item_id = ? "
                "AND status IN ('proposed', 'approved', 'ordered')",
                (item["id"],),
            ).fetchone()
            if existing:
                continue
            self.propose_reorder(item["id"], note="auto-proposed: at/below reorder threshold")
            created += 1
        return created

    def approve_order(self, order_id: int) -> None:
        """Approves a proposed order. Doesn't place it anywhere — you
        still buy it yourself. This just confirms 'yes, get this' and
        moves it out of the pending queue so it stops nagging you."""
        self.db.execute(
            "UPDATE inventory_orders SET status = 'approved' WHERE id = ? AND status = 'proposed'",
            (order_id,),
        )
        self.db.commit()

    def deny_order(self, order_id: int, reason: str = None) -> None:
        notes_suffix = f" | denied: {reason}" if reason else " | denied"
        self.db.execute(
            "UPDATE inventory_orders SET status = 'denied', "
            "notes = COALESCE(notes, '') || ? WHERE id = ? AND status = 'proposed'",
            (notes_suffix, order_id),
        )
        self.db.commit()

    def get_to_order_list(self) -> list[dict]:
        """Everything awaiting your approve/deny decision."""
        rows = self.db.execute(
            """
            SELECT io.id AS order_id, ii.name, ii.category, io.quantity, ii.unit,
                   io.cost, io.notes, io.ordered_at, ii.supplier, ii.supplier_url
            FROM inventory_orders io
            JOIN inventory_items ii ON ii.id = io.item_id
            WHERE io.status = 'proposed'
            ORDER BY io.ordered_at ASC
            """
        ).fetchall()
        cols = ["order_id", "name", "category", "quantity", "unit", "cost",
                "notes", "proposed_at", "supplier", "supplier_url"]
        return [dict(zip(cols, r)) for r in rows]

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="inventory",
            display_name="Inventory Manager",
            purpose=(
                "Tracks stock of dosing chemicals, spare sensors, and spare "
                "parts. Auto-proposes reorders when stock drops to the "
                "reorder threshold, and queues them for approval rather "
                "than placing anything automatically."
            ),
            data_produced=[
                "stock levels per item", "consumption history",
                "order history (proposed/approved/denied/ordered/received)",
            ],
            actions_possible=[
                "adjust stock on hand", "propose a reorder",
                "record an order you placed yourself", "mark an order received",
            ],
            limits_and_safety=(
                "NEVER places a real order or spends money — 'approve' only "
                "confirms intent to buy; the human still executes the "
                "purchase. No live supplier API integration exists."
            ),
            example_questions=[
                "What's low on stock?", "What's in the to-order queue?",
                "How much pH-up chemical have we used this month?",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software — inventory doesn't need hardware of its own
