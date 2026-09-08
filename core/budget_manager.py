"""
core.budget_manager
======================

MIA Home's household bookkeeping — bills, income, and expenses. Named
`budget_manager`, deliberately neither `finance_manager` nor
`ledger_manager` — both already exist as different concepts.
`core/finance_manager.py` is a read-only watched-folder importer for
externally-generated Kraken trading-agent and real-estate-dashboard
JSON exports; it has no CRUD and never will (see its own docstring).
`core/ledger_manager.py` is MIA Home's Workshop fab-business
revenue/expense ledger, tied to `job_id`/`product_id`. This manager is
the household piece neither of those covers: recurring bills (energy,
mortgage, insurance, ...), day-to-day income and expenses, and rental
income — manual entry, same v1 discipline as every other manager here
before real bank/statement integration exists.

Same persisted-JSON pattern as core.ledger_manager.LedgerManager
(one manager, two peer entry types plus Bills, not three near-duplicate
managers) — `_in_range()` mirrors that file's own date-range filter
almost verbatim; small enough that duplicating it locally is the right
call, same "no shared base class for two instances of a shape" stance
ledger_manager.py's own docstring already took once.

Bill due/recurrence math reuses core.calendar_manager.date_recurs_on()
directly rather than a third hand-rolled copy of the same yearly/
monthly/weekly date arithmetic (Calendar's, and now Bill's) — a core/
module importing another core/ module is unrestricted (only modules/
has the no-cross-import layering rule).

No real tax computation lives here — no brackets, no liability
estimate, no filing support. `tax_relevant` is just a flag on income/
expense entries and the reporting functions can subtotal by it, same
honest boundary Maintenance's Prediction feature draws around
fabricated precision it doesn't actually have.

**IncomeSource** (2026-09-08, added for proactive nudges) is the
expected/recurring counterpart to `IncomeEntry` — a real paycheck
schedule to compute "when's the next payday" from, the exact gap
`Bill` already closed for expenses. Same shape, same due-date math
(`date_recurs_on()`, including "biweekly" — common enough for real
paychecks that it was added to `core.calendar_manager.RECURRENCE_TYPES`
itself, not a Budget-only special case). `mark_income_received()`
mirrors `mark_bill_paid()`'s "one action, two real effects" shape.

**BudgetTarget** is a plain planned-monthly-amount per expense
category — the one new concept with no existing precedent to mirror,
kept deliberately minimal (no yearly overrides, no envelope rollover)
to match the honest "budgeted amount per category" ask rather than
building a full budgeting system.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.calendar_manager import RECURRENCE_TYPES, date_recurs_on
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_BILLS_FILE = _DATA_DIR / "bills.json"
_INCOME_FILE = _DATA_DIR / "income.json"
_EXPENSES_FILE = _DATA_DIR / "budget_expenses.json"
_INCOME_SOURCES_FILE = _DATA_DIR / "income_sources.json"
_BUDGET_TARGETS_FILE = _DATA_DIR / "budget_targets.json"

INCOME_CATEGORIES = ["Salary", "Rental Income", "Investment", "Other"]
EXPENSE_CATEGORIES = ["Utilities", "Mortgage/Rent", "Insurance", "Groceries", "Maintenance", "Transportation", "Taxes", "Other"]


@dataclass
class IncomeEntry:
    entry_id: str
    amount: float
    category: str = "Other"  # one of INCOME_CATEGORIES
    description: str = ""
    date: str = ""  # ISO date — when the income was received
    tax_relevant: bool = True  # most income is taxable by default
    property_id: str = ""  # set when this is rental income for a core.real_estate_manager.Property
    notes: str = ""
    created_at: str = ""  # ISO datetime — when this entry was recorded

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id, "amount": self.amount, "category": self.category,
            "description": self.description, "date": self.date, "tax_relevant": self.tax_relevant,
            "property_id": self.property_id, "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "IncomeEntry":
        return IncomeEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            amount=data.get("amount", 0.0),
            category=data.get("category", "Other"),
            description=data.get("description", ""),
            date=data.get("date", ""),
            tax_relevant=data.get("tax_relevant", True),
            property_id=data.get("property_id", ""),
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
    tax_relevant: bool = False  # most household expenses aren't deductible; user opts in
    bill_id: str = ""  # set when this entry came from BudgetManager.mark_bill_paid()
    property_id: str = ""  # set when this is an expense for a core.real_estate_manager.Property
    notes: str = ""
    created_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id, "amount": self.amount, "category": self.category,
            "description": self.description, "date": self.date, "tax_relevant": self.tax_relevant,
            "bill_id": self.bill_id, "property_id": self.property_id, "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ExpenseEntry":
        return ExpenseEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            amount=data.get("amount", 0.0),
            category=data.get("category", "Other"),
            description=data.get("description", ""),
            date=data.get("date", ""),
            tax_relevant=data.get("tax_relevant", False),
            bill_id=data.get("bill_id", ""),
            property_id=data.get("property_id", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class Bill:
    bill_id: str
    name: str
    amount: float
    category: str = "Utilities"  # one of EXPENSE_CATEGORIES
    due_date: str = ""  # ISO anchor date — same role as CalendarEvent.date
    recurrence: Optional[str] = None  # None, or one of core.calendar_manager.RECURRENCE_TYPES
    last_paid_date: Optional[str] = None
    tax_relevant: bool = False
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "bill_id": self.bill_id, "name": self.name, "amount": self.amount, "category": self.category,
            "due_date": self.due_date, "recurrence": self.recurrence, "last_paid_date": self.last_paid_date,
            "tax_relevant": self.tax_relevant, "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Bill":
        return Bill(
            bill_id=data.get("bill_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            amount=data.get("amount", 0.0),
            category=data.get("category", "Utilities"),
            due_date=data.get("due_date", ""),
            recurrence=data.get("recurrence"),
            last_paid_date=data.get("last_paid_date"),
            tax_relevant=data.get("tax_relevant", False),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


def _today_iso() -> str:
    return datetime.now().date().isoformat()


def _in_range(entry_date: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """Pure logic — testable without I/O. ISO dates sort correctly as
    plain strings, same reasoning core.ledger_manager's own _in_range()
    (and core.finance_manager's generated_at comparison) already use."""
    if start_date and entry_date < start_date:
        return False
    if end_date and entry_date > end_date:
        return False
    return True


def next_bill_due_date(bill: Bill) -> Optional[date]:
    """Pure logic — testable without Qt. Mirrors
    core.maintenance_manager.next_due_date()'s shape: None if there's
    nothing left to pay (a one-time bill already paid), the anchor
    due_date if never paid, otherwise the next occurrence after
    last_paid_date. Finds that next occurrence by walking forward one
    day at a time re-checking date_recurs_on() — a bounded loop (at
    most ~366 iterations for yearly recurrence, cheap and rarely
    called) rather than a second, potentially-divergent hand-rolled
    month/year-stepping implementation; date_recurs_on() stays the one
    source of truth for what counts as an occurrence."""
    try:
        anchor = date.fromisoformat(bill.due_date)
    except ValueError:
        return None
    if bill.last_paid_date is None:
        return anchor
    if bill.recurrence is None:
        return None  # one-time bill, already paid — nothing more due
    try:
        last_paid = date.fromisoformat(bill.last_paid_date)
    except ValueError:
        last_paid = anchor
    candidate = max(anchor, last_paid) + timedelta(days=1)
    for _ in range(370):
        if date_recurs_on(anchor, bill.recurrence, candidate):
            return candidate
        candidate += timedelta(days=1)
    return None  # unreachable for any of the real RECURRENCE_TYPES values


def days_until_bill_due(bill: Bill, today: date) -> Optional[int]:
    """Pure logic — testable without Qt. Negative = overdue by that many days."""
    due = next_bill_due_date(bill)
    if due is None:
        return None
    return (due - today).days


def is_bill_due(bill: Bill, today: date) -> bool:
    """Pure logic — testable without Qt. A bill counts as due once its
    due date has arrived, same "due today counts, not just overdue"
    stance modules.garage.module/modules.property.module already take
    for Maintenance tasks."""
    remaining = days_until_bill_due(bill, today)
    return remaining is not None and remaining <= 0


@dataclass
class IncomeSource:
    source_id: str
    name: str  # "Paycheck", "Rental — 123 Main St"
    expected_amount: float
    category: str = "Salary"  # one of INCOME_CATEGORIES
    next_date: str = ""  # ISO anchor date — same role as Bill.due_date
    recurrence: Optional[str] = None  # None, or one of core.calendar_manager.RECURRENCE_TYPES
    last_received_date: Optional[str] = None
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id, "name": self.name, "expected_amount": self.expected_amount,
            "category": self.category, "next_date": self.next_date, "recurrence": self.recurrence,
            "last_received_date": self.last_received_date, "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "IncomeSource":
        return IncomeSource(
            source_id=data.get("source_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            expected_amount=data.get("expected_amount", 0.0),
            category=data.get("category", "Salary"),
            next_date=data.get("next_date", ""),
            recurrence=data.get("recurrence"),
            last_received_date=data.get("last_received_date"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class BudgetTarget:
    category: str  # one of EXPENSE_CATEGORIES, one target per category
    monthly_amount: float

    def to_dict(self) -> dict:
        return {"category": self.category, "monthly_amount": self.monthly_amount}

    @staticmethod
    def from_dict(data: dict) -> "BudgetTarget":
        return BudgetTarget(category=data.get("category", "Other"), monthly_amount=data.get("monthly_amount", 0.0))


def next_income_due_date(source: IncomeSource) -> Optional[date]:
    """Pure logic — testable without Qt. Exact mirror of
    next_bill_due_date()'s shape, same bounded-forward-walk over
    date_recurs_on() — None once a one-time source has already been
    received, the anchor next_date if never received, otherwise the
    next occurrence after last_received_date."""
    try:
        anchor = date.fromisoformat(source.next_date)
    except ValueError:
        return None
    if source.last_received_date is None:
        return anchor
    if source.recurrence is None:
        return None  # one-time income, already received — nothing more expected
    try:
        last_received = date.fromisoformat(source.last_received_date)
    except ValueError:
        last_received = anchor
    candidate = max(anchor, last_received) + timedelta(days=1)
    for _ in range(370):
        if date_recurs_on(anchor, source.recurrence, candidate):
            return candidate
        candidate += timedelta(days=1)
    return None  # unreachable for any of the real RECURRENCE_TYPES values


def days_until_income_due(source: IncomeSource, today: date) -> Optional[int]:
    """Pure logic — testable without Qt. Negative = overdue (expected but not yet received) by that many days."""
    due = next_income_due_date(source)
    if due is None:
        return None
    return (due - today).days


class BudgetManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._bills: list[Bill] = []
        self._income: list[IncomeEntry] = []
        self._expenses: list[ExpenseEntry] = []
        self._income_sources: list[IncomeSource] = []
        self._budget_targets: list[BudgetTarget] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._bills = self._load_file(_BILLS_FILE, Bill.from_dict)
        self._income = self._load_file(_INCOME_FILE, IncomeEntry.from_dict)
        self._expenses = self._load_file(_EXPENSES_FILE, ExpenseEntry.from_dict)
        self._income_sources = self._load_file(_INCOME_SOURCES_FILE, IncomeSource.from_dict)
        self._budget_targets = self._load_file(_BUDGET_TARGETS_FILE, BudgetTarget.from_dict)

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

    def _save_bills(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _BILLS_FILE.write_text(json.dumps([b.to_dict() for b in self._bills], indent=2), encoding="utf-8")

    def _save_income(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _INCOME_FILE.write_text(json.dumps([i.to_dict() for i in self._income], indent=2), encoding="utf-8")

    def _save_expenses(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _EXPENSES_FILE.write_text(json.dumps([e.to_dict() for e in self._expenses], indent=2), encoding="utf-8")

    def _save_income_sources(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _INCOME_SOURCES_FILE.write_text(json.dumps([s.to_dict() for s in self._income_sources], indent=2), encoding="utf-8")

    def _save_budget_targets(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _BUDGET_TARGETS_FILE.write_text(json.dumps([t.to_dict() for t in self._budget_targets], indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Bills
    # ------------------------------------------------------------------

    def add_bill(
        self,
        name: str,
        amount: float,
        due_date: str,
        category: str = "Utilities",
        recurrence: Optional[str] = None,
        tax_relevant: bool = False,
        notes: str = "",
    ) -> Bill:
        bill = Bill(
            bill_id=uuid.uuid4().hex[:10],
            name=name,
            amount=max(0.0, amount),
            category=category if category in EXPENSE_CATEGORIES else "Other",
            due_date=due_date,
            recurrence=recurrence if recurrence in RECURRENCE_TYPES else None,
            tax_relevant=tax_relevant,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._bills.append(bill)
        self._save_bills()
        log.info("Bill added: '%s' $%.2f due %s", bill.name, bill.amount, bill.due_date)
        return bill

    def update_bill(self, bill_id: str, **fields) -> Bill:
        bill = self.get_bill(bill_id)
        if bill is None:
            raise ValueError(f"No bill with id '{bill_id}'.")
        for key, value in fields.items():
            if not hasattr(bill, key):
                raise ValueError(f"Bill has no field '{key}'.")
            setattr(bill, key, value)
        if bill.amount < 0:
            bill.amount = 0
        if bill.category not in EXPENSE_CATEGORIES:
            bill.category = "Other"
        if bill.recurrence not in (None, *RECURRENCE_TYPES):
            bill.recurrence = None
        self._save_bills()
        return bill

    def delete_bill(self, bill_id: str) -> None:
        self._bills = [b for b in self._bills if b.bill_id != bill_id]
        self._save_bills()

    def get_bill(self, bill_id: str) -> Optional[Bill]:
        for bill in self._bills:
            if bill.bill_id == bill_id:
                return bill
        return None

    def all_bills(self) -> list[Bill]:
        return sorted(self._bills, key=lambda b: b.due_date)

    def mark_bill_paid(self, bill_id: str, paid_date: Optional[str] = None, amount: Optional[float] = None) -> ExpenseEntry:
        """Records a real ExpenseEntry (category/tax_relevant inherited
        from the bill, amount overridable for a bill that varies month
        to month, e.g. an energy bill) AND updates last_paid_date — one
        action, two real effects, same shape as
        core.ledger_manager.LedgerManager.record_sale() deducting stock
        while recording revenue."""
        bill = self.get_bill(bill_id)
        if bill is None:
            raise ValueError(f"No bill with id '{bill_id}'.")
        paid_date = paid_date or _today_iso()
        paid_amount = bill.amount if amount is None else max(0.0, amount)

        entry = self.add_expense(
            amount=paid_amount,
            category=bill.category,
            description=bill.name,
            date=paid_date,
            tax_relevant=bill.tax_relevant,
            bill_id=bill.bill_id,
        )
        bill.last_paid_date = paid_date
        self._save_bills()
        log.info("Bill paid: '%s' $%.2f on %s", bill.name, paid_amount, paid_date)
        return entry

    # ------------------------------------------------------------------
    # Income sources — expected/recurring income, the counterpart to
    # Bills for the money coming IN (2026-09-08, added for proactive
    # nudges — "when's the next paycheck" needs this exact shape).
    # ------------------------------------------------------------------

    def add_income_source(
        self,
        name: str,
        expected_amount: float,
        next_date: str,
        category: str = "Salary",
        recurrence: Optional[str] = None,
        notes: str = "",
    ) -> IncomeSource:
        source = IncomeSource(
            source_id=uuid.uuid4().hex[:10],
            name=name,
            expected_amount=max(0.0, expected_amount),
            category=category if category in INCOME_CATEGORIES else "Other",
            next_date=next_date,
            recurrence=recurrence if recurrence in RECURRENCE_TYPES else None,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._income_sources.append(source)
        self._save_income_sources()
        log.info("Income source added: '%s' $%.2f expected %s", source.name, source.expected_amount, source.next_date)
        return source

    def update_income_source(self, source_id: str, **fields) -> IncomeSource:
        source = self.get_income_source(source_id)
        if source is None:
            raise ValueError(f"No income source with id '{source_id}'.")
        for key, value in fields.items():
            if not hasattr(source, key):
                raise ValueError(f"IncomeSource has no field '{key}'.")
            setattr(source, key, value)
        if source.expected_amount < 0:
            source.expected_amount = 0
        if source.category not in INCOME_CATEGORIES:
            source.category = "Other"
        if source.recurrence not in (None, *RECURRENCE_TYPES):
            source.recurrence = None
        self._save_income_sources()
        return source

    def delete_income_source(self, source_id: str) -> None:
        self._income_sources = [s for s in self._income_sources if s.source_id != source_id]
        self._save_income_sources()

    def get_income_source(self, source_id: str) -> Optional[IncomeSource]:
        for source in self._income_sources:
            if source.source_id == source_id:
                return source
        return None

    def all_income_sources(self) -> list[IncomeSource]:
        return sorted(self._income_sources, key=lambda s: s.next_date)

    def mark_income_received(self, source_id: str, received_date: Optional[str] = None, amount: Optional[float] = None) -> IncomeEntry:
        """Records a real IncomeEntry (category inherited from the
        source, amount overridable for a paycheck that varies) AND
        updates last_received_date — exact mirror of mark_bill_paid()'s
        "one action, two real effects" shape."""
        source = self.get_income_source(source_id)
        if source is None:
            raise ValueError(f"No income source with id '{source_id}'.")
        received_date = received_date or _today_iso()
        received_amount = source.expected_amount if amount is None else max(0.0, amount)

        entry = self.add_income(
            amount=received_amount,
            category=source.category,
            description=source.name,
            date=received_date,
        )
        source.last_received_date = received_date
        self._save_income_sources()
        log.info("Income received: '%s' $%.2f on %s", source.name, received_amount, received_date)
        return entry

    # ------------------------------------------------------------------
    # Income
    # ------------------------------------------------------------------

    def add_income(
        self,
        amount: float,
        category: str = "Other",
        description: str = "",
        date: Optional[str] = None,
        tax_relevant: bool = True,
        property_id: str = "",
        notes: str = "",
    ) -> IncomeEntry:
        entry = IncomeEntry(
            entry_id=uuid.uuid4().hex[:10],
            amount=max(0.0, amount),
            category=category if category in INCOME_CATEGORIES else "Other",
            description=description,
            date=date or _today_iso(),
            tax_relevant=tax_relevant,
            property_id=property_id,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._income.append(entry)
        self._save_income()
        log.info("Income recorded: $%.2f (%s)", entry.amount, entry.category)
        return entry

    def update_income(self, entry_id: str, **fields) -> IncomeEntry:
        entry = self.get_income(entry_id)
        if entry is None:
            raise ValueError(f"No income entry with id '{entry_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_income().")
            if not hasattr(entry, key):
                raise ValueError(f"IncomeEntry has no field '{key}'.")
            setattr(entry, key, value)
        if entry.amount < 0:
            entry.amount = 0
        if entry.category not in INCOME_CATEGORIES:
            entry.category = "Other"
        self._save_income()
        return entry

    def delete_income(self, entry_id: str) -> None:
        self._income = [i for i in self._income if i.entry_id != entry_id]
        self._save_income()

    def get_income(self, entry_id: str) -> Optional[IncomeEntry]:
        for entry in self._income:
            if entry.entry_id == entry_id:
                return entry
        return None

    def all_income(self) -> list[IncomeEntry]:
        return sorted(self._income, key=lambda i: i.date, reverse=True)

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def add_expense(
        self,
        amount: float,
        category: str = "Other",
        description: str = "",
        date: Optional[str] = None,
        tax_relevant: bool = False,
        bill_id: str = "",
        property_id: str = "",
        notes: str = "",
    ) -> ExpenseEntry:
        entry = ExpenseEntry(
            entry_id=uuid.uuid4().hex[:10],
            amount=max(0.0, amount),
            category=category if category in EXPENSE_CATEGORIES else "Other",
            description=description,
            date=date or _today_iso(),
            tax_relevant=tax_relevant,
            bill_id=bill_id,
            property_id=property_id,
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

    def total_income(self, start_date: Optional[str] = None, end_date: Optional[str] = None, tax_relevant_only: bool = False) -> float:
        return sum(
            i.amount for i in self._income
            if _in_range(i.date, start_date, end_date) and (not tax_relevant_only or i.tax_relevant)
        )

    def total_expenses(self, start_date: Optional[str] = None, end_date: Optional[str] = None, tax_relevant_only: bool = False) -> float:
        return sum(
            e.amount for e in self._expenses
            if _in_range(e.date, start_date, end_date) and (not tax_relevant_only or e.tax_relevant)
        )

    def net_cash_flow(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        return self.total_income(start_date, end_date) - self.total_expenses(start_date, end_date)

    def total_expenses_by_category(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict[str, float]:
        """Actual spending per category over a date range — the
        "actual" half of a budget-target comparison. Only categories
        with at least one matching expense are present in the result
        (no zero-filled entries for untouched categories)."""
        totals: dict[str, float] = {}
        for expense in self._expenses:
            if not _in_range(expense.date, start_date, end_date):
                continue
            totals[expense.category] = totals.get(expense.category, 0.0) + expense.amount
        return totals

    # ------------------------------------------------------------------
    # Budget targets — planned monthly spending per category, deliberately
    # minimal (no yearly overrides, no envelope rollover), see module docstring
    # ------------------------------------------------------------------

    def set_budget_target(self, category: str, monthly_amount: float) -> BudgetTarget:
        """Upsert — one target per category; calling again for the same category replaces it."""
        if category not in EXPENSE_CATEGORIES:
            raise ValueError(f"Unknown expense category '{category}'.")
        existing = self.get_budget_target(category)
        if existing is not None:
            existing.monthly_amount = max(0.0, monthly_amount)
        else:
            self._budget_targets.append(BudgetTarget(category=category, monthly_amount=max(0.0, monthly_amount)))
        self._save_budget_targets()
        return self.get_budget_target(category)

    def delete_budget_target(self, category: str) -> None:
        self._budget_targets = [t for t in self._budget_targets if t.category != category]
        self._save_budget_targets()

    def get_budget_target(self, category: str) -> Optional[BudgetTarget]:
        for target in self._budget_targets:
            if target.category == category:
                return target
        return None

    def all_budget_targets(self) -> list[BudgetTarget]:
        return sorted(self._budget_targets, key=lambda t: t.category)
