"""
core.ledger_manager
======================

MIA Home's revenue/expense ledger — the fourth and final slice of the
proposed `mia_home_schema.sql` (see `docs/VISION.md`'s "MIA Home's
expanded scope" section, and `core/material_manager.py`/
`core/job_manager.py`/`core/product_manager.py`'s docstrings for slices
1-3), adapted to this project's persisted-JSON-manager convention.

Named `ledger_manager`, deliberately NOT `finance_manager` —
`core/finance_manager.py` already exists and is a completely different
concept (watched-folder ingestion of *externally*-generated Kraken/
real-estate JSON snapshots). This module is the opposite: MIA Home's
own revenue/expense bookkeeping for its own workshop sales, not an
import of someone else's portfolio data.

`revenue` and `expenses` were two separate tables in the proposed
schema; here they're two separate lists (`data/revenue.json`,
`data/expenses.json`) owned by one `LedgerManager`, rather than two
near-duplicate manager classes — they're peers in one simple
bookkeeping concept (revenue in, expenses out, net profit is the
difference), not a parent/child "record owns its own sub-items"
relationship the way `Job.material_consumption`/`Product.listings` are.

`record_sale()` is this slice's real integration point, same shape as
`core/job_manager.py`'s `consume_material()`/`produce_product()`: it
both records a `RevenueEntry` *and* deducts the sold quantity from
`core/product_manager.py`'s own `quantity_in_stock` — a sale is a real
inventory movement, not just a dollar figure sitting next to an
unrelated stock count. Plain `add_revenue()` stays available for
revenue not tied to a specific product sale (a commission, a flat
fee, a hand-recorded historical entry).

`net_profit()`/`total_revenue()`/`total_expenses()` are computed on
demand over already-loaded entries — same "never a snapshot that could
drift" precedent as `core/material_manager.py`'s
`materials_needing_restock()` and `core/job_manager.py`'s cost
functions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REVENUE_FILE = _DATA_DIR / "revenue.json"
_EXPENSES_FILE = _DATA_DIR / "expenses.json"

EXPENSE_CATEGORIES = ("Materials", "Tools", "Shipping", "Fees", "Overhead", "Other")


@dataclass
class RevenueEntry:
    entry_id: str
    amount: float
    description: str = ""
    date: str = ""  # ISO date (YYYY-MM-DD) — when the sale/income happened, not when it was entered
    product_id: str = ""  # optional link to core/product_manager.py
    job_id: str = ""  # optional link to core/job_manager.py
    quantity_sold: float = 0.0  # only meaningful when product_id is set (see record_sale())
    notes: str = ""
    created_at: str = ""  # ISO datetime — when this entry was recorded

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "amount": self.amount,
            "description": self.description,
            "date": self.date,
            "product_id": self.product_id,
            "job_id": self.job_id,
            "quantity_sold": self.quantity_sold,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "RevenueEntry":
        return RevenueEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            amount=data.get("amount", 0.0),
            description=data.get("description", ""),
            date=data.get("date", ""),
            product_id=data.get("product_id", ""),
            job_id=data.get("job_id", ""),
            quantity_sold=data.get("quantity_sold", 0.0),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class ExpenseEntry:
    entry_id: str
    amount: float
    category: str = "Other"  # one of EXPENSE_CATEGORIES
    description: str = ""
    date: str = ""  # ISO date
    job_id: str = ""  # optional link to core/job_manager.py
    notes: str = ""
    created_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
            "job_id": self.job_id,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ExpenseEntry":
        return ExpenseEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            amount=data.get("amount", 0.0),
            category=data.get("category", "Other"),
            description=data.get("description", ""),
            date=data.get("date", ""),
            job_id=data.get("job_id", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


def _today_iso() -> str:
    return datetime.now().date().isoformat()


def _in_range(entry_date: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """Pure logic — testable without I/O. ISO dates sort correctly as
    plain strings, so this is a simple string comparison, same
    reasoning core/finance_manager.py's generated_at comparison uses."""
    if start_date and entry_date < start_date:
        return False
    if end_date and entry_date > end_date:
        return False
    return True


class LedgerManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._revenue: list[RevenueEntry] = []
        self._expenses: list[ExpenseEntry] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._revenue = self._load_file(_REVENUE_FILE, RevenueEntry.from_dict)
        self._expenses = self._load_file(_EXPENSES_FILE, ExpenseEntry.from_dict)

    @staticmethod
    def _load_file(path: Path, from_dict) -> list:
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            return []

    def _save_revenue(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_REVENUE_FILE, json.dumps([r.to_dict() for r in self._revenue], indent=2), encoding="utf-8")

    def _save_expenses(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_EXPENSES_FILE, json.dumps([e.to_dict() for e in self._expenses], indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Revenue
    # ------------------------------------------------------------------

    def add_revenue(
        self,
        amount: float,
        description: str = "",
        date: Optional[str] = None,
        product_id: str = "",
        job_id: str = "",
        quantity_sold: float = 0.0,
        notes: str = "",
    ) -> RevenueEntry:
        entry = RevenueEntry(
            entry_id=uuid.uuid4().hex[:10],
            amount=max(0.0, amount),
            description=description,
            date=date or _today_iso(),
            product_id=product_id,
            job_id=job_id,
            quantity_sold=max(0.0, quantity_sold),
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._revenue.append(entry)
        self._save_revenue()
        log.info("Revenue recorded: $%.2f (%s)", entry.amount, entry.description or "no description")
        return entry

    def record_sale(
        self,
        product_id: str,
        quantity_sold: float,
        amount: float,
        description: str = "",
        job_id: str = "",
        date: Optional[str] = None,
        notes: str = "",
    ) -> RevenueEntry:
        """
        The real integration point — records the revenue entry *and*
        deducts quantity_sold from core/product_manager.py's own
        quantity_in_stock (clamped at zero, same stance every other
        cross-manager stock adjustment in this pipeline takes). Use
        plain add_revenue() instead for revenue not tied to moving
        product stock (a commission, a flat fee).
        """
        entry = self.add_revenue(
            amount=amount, description=description, date=date, product_id=product_id,
            job_id=job_id, quantity_sold=quantity_sold, notes=notes,
        )
        if self.context.products is not None:
            product = self.context.products.get_product(product_id)
            if product is not None:
                self.context.products.adjust_stock(product_id, -entry.quantity_sold)
        return entry

    def update_revenue(self, entry_id: str, **fields) -> RevenueEntry:
        entry = self.get_revenue(entry_id)
        if entry is None:
            raise ValueError(f"No revenue entry with id '{entry_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_revenue().")
            if not hasattr(entry, key):
                raise ValueError(f"RevenueEntry has no field '{key}'.")
            setattr(entry, key, value)
        if entry.amount < 0:
            entry.amount = 0
        if entry.quantity_sold < 0:
            entry.quantity_sold = 0
        self._save_revenue()
        return entry

    def delete_revenue(self, entry_id: str) -> None:
        self._revenue = [r for r in self._revenue if r.entry_id != entry_id]
        self._save_revenue()

    def get_revenue(self, entry_id: str) -> Optional[RevenueEntry]:
        for entry in self._revenue:
            if entry.entry_id == entry_id:
                return entry
        return None

    def all_revenue(self) -> list[RevenueEntry]:
        return sorted(self._revenue, key=lambda r: r.date, reverse=True)

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def add_expense(
        self,
        amount: float,
        category: str = "Other",
        description: str = "",
        date: Optional[str] = None,
        job_id: str = "",
        notes: str = "",
    ) -> ExpenseEntry:
        entry = ExpenseEntry(
            entry_id=uuid.uuid4().hex[:10],
            amount=max(0.0, amount),
            category=category if category in EXPENSE_CATEGORIES else "Other",
            description=description,
            date=date or _today_iso(),
            job_id=job_id,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._expenses.append(entry)
        self._save_expenses()
        log.info("Expense recorded: $%.2f (%s)", entry.amount, entry.category)
        return entry

    def update_expense(self, entry_id: str, **fields) -> ExpenseEntry:
        entry = self.get_expense(entry_id)
        if entry is None:
            raise ValueError(f"No expense entry with id '{entry_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_expense().")
            if not hasattr(entry, key):
                raise ValueError(f"ExpenseEntry has no field '{key}'.")
            setattr(entry, key, value)
        if entry.amount < 0:
            entry.amount = 0
        if entry.category not in EXPENSE_CATEGORIES:
            entry.category = "Other"
        self._save_expenses()
        return entry

    def delete_expense(self, entry_id: str) -> None:
        self._expenses = [e for e in self._expenses if e.entry_id != entry_id]
        self._save_expenses()

    def get_expense(self, entry_id: str) -> Optional[ExpenseEntry]:
        for entry in self._expenses:
            if entry.entry_id == entry_id:
                return entry
        return None

    def all_expenses(self) -> list[ExpenseEntry]:
        return sorted(self._expenses, key=lambda e: e.date, reverse=True)

    # ------------------------------------------------------------------
    # Reporting — computed on demand, never persisted (see module docstring)
    # ------------------------------------------------------------------

    def total_revenue(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        return sum(r.amount for r in self._revenue if _in_range(r.date, start_date, end_date))

    def total_expenses(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        return sum(e.amount for e in self._expenses if _in_range(e.date, start_date, end_date))

    def net_profit(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        return self.total_revenue(start_date, end_date) - self.total_expenses(start_date, end_date)
