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

**Debt** (2026-09-27) is a payoff-tracked liability — credit cards,
personal/auto/student loans, medical debt — deliberately NOT a
mortgage: `core/real_estate_manager.py`'s `Property` already owns
`mortgage_balance` plus real amortization, and duplicating that here
would just create two disagreeing numbers for the same real loan.
`effective_apr()` is the one real piece of domain logic: a debt can
carry an optional promotional APR with its own expiration date (a
"0% for 12 months" card offer), and the effective rate in force on any
given day is the promo rate before that date, the standard
`interest_rate` after — a promo with no real expiration date doesn't
mean anything, so it's treated as already expired rather than assumed
permanent. `record_debt_payment()` mirrors `mark_bill_paid()`'s "one
action, two real effects" shape: a real `ExpenseEntry` (category
`"Debt Payment"`) plus a real balance reduction, clamped at $0 rather
than going negative (same stance `MaterialManager.adjust_quantity()`
already takes for a shared numeric quantity). `rank_debts()` is a pure
function over a plain list — no persisted ranking, same "reporting is
computed on demand" precedent every other report in this file follows
— offering three real strategies: `"avalanche"` (highest effective APR
first, mathematically optimal total interest), `"snowball"` (smallest
balance first, for payoff-momentum motivation), and `"hybrid"`
(avalanche order, except a debt whose promo is expiring within
`_PROMO_URGENCY_WINDOW_DAYS` jumps to the front — a 0% balance about to
revert to 24.99% is a real, time-boxed emergency that pure APR-today
ordering would otherwise miss entirely).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.calendar_manager import RECURRENCE_TYPES, date_recurs_on
from core.gamification import SkillWeight, grant_xp
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.region import money

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_BILLS_FILE = _DATA_DIR / "bills.json"
_INCOME_FILE = _DATA_DIR / "income.json"
_EXPENSES_FILE = _DATA_DIR / "budget_expenses.json"
_INCOME_SOURCES_FILE = _DATA_DIR / "income_sources.json"
_BUDGET_TARGETS_FILE = _DATA_DIR / "budget_targets.json"
_BUSINESS_ENTITIES_FILE = _DATA_DIR / "business_entities.json"
_DEBTS_FILE = _DATA_DIR / "debts.json"

INCOME_CATEGORIES = ["Salary", "Rental Income", "Investment", "Other"]
EXPENSE_CATEGORIES = [
    "Utilities", "Mortgage/Rent", "Insurance", "Groceries", "Maintenance", "Transportation", "Taxes",
    # 2026-09-09: added so core.plaid_manager.map_plaid_category() has a
    # real home for these six real Plaid primary categories — previously
    # all fell through to "Other", which meant a meaningful fraction of
    # real synced bank spending was invisible to category budgeting.
    "Medical", "Personal Care", "Shopping", "Bank Fees", "Entertainment", "Travel",
    # 2026-09-27: Debt.record_debt_payment()'s own ExpenseEntry category.
    "Debt Payment",
    # 2026-09-28, Finance #2 (homestead builds and tools, see
    # core/homestead_costs.py).
    "Building Materials", "Tools & Equipment",
    "Other",
]
BUSINESS_ENTITY_TYPES = ["LLC", "Sole Proprietorship", "Other"]
# Deliberately excludes "Mortgage" — see Debt's own docstring note above
# for why a mortgage stays owned by core.real_estate_manager.Property.
DEBT_TYPES = ["Credit Card", "Personal Loan", "Auto Loan", "Student Loan", "Medical Debt", "Other"]
DEBT_PAYOFF_STRATEGIES = ["avalanche", "snowball", "hybrid"]
# Inside this window, a debt's expiring promo APR outranks pure
# current-APR ordering in the "hybrid" strategy — see rank_debts().
_PROMO_URGENCY_WINDOW_DAYS = 45
# Real, stable IRS 1099-NEC threshold (years running) — see
# payees_over_1099_threshold() below.
US_1099_NEC_THRESHOLD = 600.0


@dataclass
class IncomeEntry:
    entry_id: str
    amount: float
    category: str = "Other"  # one of INCOME_CATEGORIES
    description: str = ""
    date: str = ""  # ISO date — when the income was received
    tax_relevant: bool = True  # most income is taxable by default
    property_id: str = ""  # set when this is rental income for a core.real_estate_manager.Property
    entity_id: str = ""  # set when this belongs to a BusinessEntity (LLC/sole prop/etc.)
    plaid_transaction_id: str = ""  # set when imported by core.plaid_manager — the dedup key on repeat sync
    notes: str = ""
    created_at: str = ""  # ISO datetime — when this entry was recorded

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id, "amount": self.amount, "category": self.category,
            "description": self.description, "date": self.date, "tax_relevant": self.tax_relevant,
            "property_id": self.property_id, "entity_id": self.entity_id,
            "plaid_transaction_id": self.plaid_transaction_id,
            "notes": self.notes, "created_at": self.created_at,
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
            entity_id=data.get("entity_id", ""),
            plaid_transaction_id=data.get("plaid_transaction_id", ""),
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
    entity_id: str = ""  # set when this belongs to a BusinessEntity (LLC/sole prop/etc.)
    plaid_transaction_id: str = ""  # set when imported by core.plaid_manager — the dedup key on repeat sync
    # 2026-09-09: who was paid — distinct from `description` (what the
    # expense was for). Only used for 1099-NEC threshold tracking, see
    # payees_over_1099_threshold() below.
    payee: str = ""
    notes: str = ""
    created_at: str = ""  # ISO datetime
    # 2026-09-28, Finance #2 (core/homestead_costs.py): what the money was
    # for. project_id: a build (core.project_manager.Project, e.g. the
    # greenhouse); asset_id: a tool or piece of equipment
    # (core.maintenance_manager.MaintenanceAsset). Either, both or neither.
    # asset_purchase marks the expense that bought the tool itself, so its
    # cost of ownership counts the purchase once (it's also the asset's
    # purchase_price).
    project_id: str = ""
    asset_id: str = ""
    asset_purchase: bool = False
    # 2026-09-28, business tagging (core/business_tagging.py): the owner
    # (or MIA, confidently) decided which business this is for, or that
    # it's personal (entity_id ""); entity_auto marks MIA's own choice.
    entity_reviewed: bool = False
    entity_auto: bool = False
    # 2026-09-28: what was bought, from a filed receipt's lines
    # (core/inbox_classify.receipt_items): [{description, amount, quantity, unit_price}].
    items: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id, "amount": self.amount, "category": self.category,
            "description": self.description, "date": self.date, "tax_relevant": self.tax_relevant,
            "bill_id": self.bill_id, "property_id": self.property_id, "entity_id": self.entity_id,
            "plaid_transaction_id": self.plaid_transaction_id, "payee": self.payee,
            "notes": self.notes, "created_at": self.created_at,
            "project_id": self.project_id, "asset_id": self.asset_id, "asset_purchase": self.asset_purchase,
            "entity_reviewed": self.entity_reviewed, "entity_auto": self.entity_auto,
            "items": list(self.items),
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
            entity_id=data.get("entity_id", ""),
            plaid_transaction_id=data.get("plaid_transaction_id", ""),
            payee=data.get("payee", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            project_id=data.get("project_id", ""),
            asset_id=data.get("asset_id", ""),
            asset_purchase=bool(data.get("asset_purchase", False)),
            entity_reviewed=bool(data.get("entity_reviewed", False)),
            entity_auto=bool(data.get("entity_auto", False)),
            items=list(data.get("items", []) or []),
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
    entity_id: str = ""  # set when this belongs to a BusinessEntity (LLC/sole prop/etc.)
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "bill_id": self.bill_id, "name": self.name, "amount": self.amount, "category": self.category,
            "due_date": self.due_date, "recurrence": self.recurrence, "last_paid_date": self.last_paid_date,
            "tax_relevant": self.tax_relevant, "entity_id": self.entity_id,
            "notes": self.notes, "created_at": self.created_at,
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
            entity_id=data.get("entity_id", ""),
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
    entity_id: str = ""  # set when this belongs to a BusinessEntity (LLC/sole prop/etc.)
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id, "name": self.name, "expected_amount": self.expected_amount,
            "category": self.category, "next_date": self.next_date, "recurrence": self.recurrence,
            "last_received_date": self.last_received_date, "entity_id": self.entity_id,
            "notes": self.notes, "created_at": self.created_at,
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
            entity_id=data.get("entity_id", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class BudgetTarget:
    category: str  # one of EXPENSE_CATEGORIES
    monthly_amount: float
    # 2026-09-09: one target per (category, entity_id) pair, not per
    # category alone — "" (default) is the household/no-specific-entity
    # bucket, same "" convention every other entity_id field in this
    # codebase already uses. Lets a household and an LLC sharing one
    # Budget keep separate planned amounts for the same category name.
    entity_id: str = ""

    def to_dict(self) -> dict:
        return {"category": self.category, "monthly_amount": self.monthly_amount, "entity_id": self.entity_id}

    @staticmethod
    def from_dict(data: dict) -> "BudgetTarget":
        return BudgetTarget(
            category=data.get("category", "Other"),
            monthly_amount=data.get("monthly_amount", 0.0),
            entity_id=data.get("entity_id", ""),
        )


@dataclass
class BusinessEntity:
    entity_id: str
    name: str  # "Sunrise Rentals LLC" — arbitrary, user-defined, no fixed universe
    entity_type: str = "LLC"  # one of BUSINESS_ENTITY_TYPES
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id, "name": self.name, "entity_type": self.entity_type,
            "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "BusinessEntity":
        return BusinessEntity(
            entity_id=data.get("entity_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            entity_type=data.get("entity_type", "LLC"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class Debt:
    debt_id: str
    name: str  # "Chase Freedom", "Sallie Mae — Student Loan"
    balance: float
    interest_rate: float  # standard APR, percent (e.g. 24.99, not 0.2499) — in effect once any promo expires
    minimum_payment: float = 0.0
    debt_type: str = "Credit Card"  # one of DEBT_TYPES
    # A promotional APR (e.g. a "0% for 12 months" card offer) and the
    # real date it reverts to interest_rate. promo_apr with no
    # promo_expires_date is treated as already expired — see
    # effective_apr() below.
    promo_apr: Optional[float] = None
    promo_expires_date: Optional[str] = None  # ISO date
    entity_id: str = ""  # set when this belongs to a BusinessEntity (LLC/sole prop/etc.)
    last_payment_date: Optional[str] = None
    # Set when core.plaid_manager created/syncs this debt from a real
    # linked account — the dedup key on repeat sync, same role as
    # IncomeEntry/ExpenseEntry's plaid_transaction_id.
    plaid_account_id: str = ""
    # Which connected Plaid item (bank login) this debt came from — lets
    # disconnecting one bank unlink only its own debts.
    plaid_item_id: str = ""
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "debt_id": self.debt_id, "name": self.name, "balance": self.balance,
            "interest_rate": self.interest_rate, "minimum_payment": self.minimum_payment,
            "debt_type": self.debt_type, "promo_apr": self.promo_apr,
            "promo_expires_date": self.promo_expires_date, "entity_id": self.entity_id,
            "last_payment_date": self.last_payment_date, "plaid_account_id": self.plaid_account_id,
            "plaid_item_id": self.plaid_item_id, "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Debt":
        return Debt(
            debt_id=data.get("debt_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            balance=data.get("balance", 0.0),
            interest_rate=data.get("interest_rate", 0.0),
            minimum_payment=data.get("minimum_payment", 0.0),
            debt_type=data.get("debt_type", "Credit Card"),
            promo_apr=data.get("promo_apr"),
            promo_expires_date=data.get("promo_expires_date"),
            entity_id=data.get("entity_id", ""),
            last_payment_date=data.get("last_payment_date"),
            plaid_account_id=data.get("plaid_account_id", ""),
            plaid_item_id=data.get("plaid_item_id", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


def effective_apr(debt: Debt, today: date) -> float:
    """Pure logic — testable without Qt. The real APR in force today:
    the promotional rate if one is set and hasn't expired yet,
    otherwise the standard interest_rate. A promo_apr with no real
    promo_expires_date (or an unparseable one) is treated as already
    expired — same "don't guess a schema MIA can't confirm" stance
    core.homestead_manager's own docstring takes, applied here to a
    promo offer that needs a real end date to mean anything."""
    if debt.promo_apr is not None and debt.promo_expires_date:
        try:
            expires = date.fromisoformat(debt.promo_expires_date)
        except ValueError:
            return debt.interest_rate
        if today <= expires:
            return debt.promo_apr
    return debt.interest_rate


def days_until_promo_expires(debt: Debt, today: date) -> Optional[int]:
    """Pure logic — testable without Qt. None when there's no active
    promo to expire (no promo_apr, no/unparseable promo_expires_date).
    Negative means the promo has already lapsed."""
    if debt.promo_apr is None or not debt.promo_expires_date:
        return None
    try:
        expires = date.fromisoformat(debt.promo_expires_date)
    except ValueError:
        return None
    return (expires - today).days


@dataclass
class DebtPriority:
    """A computed, never-persisted payoff-order entry — same "reporting
    is computed on demand" stance every other report in this file
    takes. `reason` is a short, human-facing explanation of why this
    debt landed at this rank, meant to be shown directly in the GUI."""
    debt: Debt
    rank: int
    effective_apr: float
    reason: str


def rank_debts(debts: list[Debt], today: date, strategy: str = "hybrid") -> list[DebtPriority]:
    """Pure logic — testable without Qt. Orders open (balance > 0)
    debts by real payoff priority under one of DEBT_PAYOFF_STRATEGIES;
    an unknown strategy falls back to "hybrid" rather than raising, same
    "unmapped falls to a safe default" precedent category validation
    elsewhere in this file already uses.

    - "avalanche": highest effective_apr() first (tie-broken by larger
      balance first) — mathematically minimizes total interest paid.
    - "snowball": smallest balance first — payoff-momentum motivation,
      not mathematically optimal but a real, common preference.
    - "hybrid": avalanche order, except any debt whose promo is
      expiring within _PROMO_URGENCY_WINDOW_DAYS jumps to the front
      (soonest-expiring first) — a 0% balance about to revert to a
      real double-digit rate is a time-boxed emergency pure
      current-APR ordering would otherwise miss until the day it's
      already too late to act.
    """
    if strategy not in DEBT_PAYOFF_STRATEGIES:
        strategy = "hybrid"
    open_debts = [d for d in debts if d.balance > 0]

    def apr(d: Debt) -> float:
        return effective_apr(d, today)

    reasons: dict[str, str] = {}

    if strategy == "snowball":
        ordered = sorted(open_debts, key=lambda d: d.balance)
        for d in ordered:
            reasons[d.debt_id] = f"Smallest balance ({money(d.balance, ',.2f')})"
    elif strategy == "avalanche":
        ordered = sorted(open_debts, key=lambda d: (-apr(d), -d.balance))
        for d in ordered:
            reasons[d.debt_id] = f"Highest current APR ({apr(d):.2f}%)"
    else:  # hybrid
        urgent = [
            d for d in open_debts
            if (days_until_promo_expires(d, today) or -1) >= 0
            and (days_until_promo_expires(d, today) or 0) <= _PROMO_URGENCY_WINDOW_DAYS
        ]
        urgent.sort(key=lambda d: days_until_promo_expires(d, today))
        urgent_ids = {d.debt_id for d in urgent}
        rest = sorted((d for d in open_debts if d.debt_id not in urgent_ids), key=lambda d: (-apr(d), -d.balance))
        ordered = urgent + rest
        for d in urgent:
            days_left = days_until_promo_expires(d, today)
            reasons[d.debt_id] = (
                f"Promo {apr(d):.2f}% APR ends in {days_left}d — jumps to {d.interest_rate:.2f}%"
            )
        for d in rest:
            reasons[d.debt_id] = f"Highest current APR ({apr(d):.2f}%)"

    return [
        DebtPriority(debt=d, rank=i + 1, effective_apr=apr(d), reason=reasons[d.debt_id])
        for i, d in enumerate(ordered)
    ]


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
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._bills_file = self.data_dir / "bills.json" if data_dir is not None else _BILLS_FILE
        self._income_file = self.data_dir / "income.json" if data_dir is not None else _INCOME_FILE
        self._expenses_file = self.data_dir / "budget_expenses.json" if data_dir is not None else _EXPENSES_FILE
        self._income_sources_file = self.data_dir / "income_sources.json" if data_dir is not None else _INCOME_SOURCES_FILE
        self._budget_targets_file = self.data_dir / "budget_targets.json" if data_dir is not None else _BUDGET_TARGETS_FILE
        self._business_entities_file = self.data_dir / "business_entities.json" if data_dir is not None else _BUSINESS_ENTITIES_FILE
        self._debts_file = self.data_dir / "debts.json" if data_dir is not None else _DEBTS_FILE
        self.context = context
        self._bills: list[Bill] = []
        self._income: list[IncomeEntry] = []
        self._expenses: list[ExpenseEntry] = []
        self._income_sources: list[IncomeSource] = []
        self._budget_targets: list[BudgetTarget] = []
        self._business_entities: list[BusinessEntity] = []
        self._debts: list[Debt] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._bills = self._load_file(self._bills_file, Bill.from_dict)
        self._income = self._load_file(self._income_file, IncomeEntry.from_dict)
        self._expenses = self._load_file(self._expenses_file, ExpenseEntry.from_dict)
        self._income_sources = self._load_file(self._income_sources_file, IncomeSource.from_dict)
        self._budget_targets = self._load_file(self._budget_targets_file, BudgetTarget.from_dict)
        self._business_entities = self._load_file(self._business_entities_file, BusinessEntity.from_dict)
        self._debts = self._load_file(self._debts_file, Debt.from_dict)

    def _load_file(self, path: Path, from_dict) -> list:
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load %s — starting with an empty list.", path.name)
            notify_data_corruption(self.context, path.name)
            return []

    def _save_bills(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._bills_file, json.dumps([b.to_dict() for b in self._bills], indent=2), encoding="utf-8")

    def _save_income(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._income_file, json.dumps([i.to_dict() for i in self._income], indent=2), encoding="utf-8")

    def _save_expenses(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._expenses_file, json.dumps([e.to_dict() for e in self._expenses], indent=2), encoding="utf-8")

    def _save_income_sources(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._income_sources_file, json.dumps([s.to_dict() for s in self._income_sources], indent=2), encoding="utf-8")

    def _save_budget_targets(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._budget_targets_file, json.dumps([t.to_dict() for t in self._budget_targets], indent=2), encoding="utf-8")

    def _save_business_entities(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._business_entities_file, json.dumps([e.to_dict() for e in self._business_entities], indent=2), encoding="utf-8")

    def _save_debts(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._debts_file, json.dumps([d.to_dict() for d in self._debts], indent=2), encoding="utf-8")

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
        entity_id: str = "",
        notes: str = "",
    ) -> Bill:
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}")
        bill = Bill(
            bill_id=uuid.uuid4().hex[:10],
            name=name,
            amount=amount,
            category=category if category in EXPENSE_CATEGORIES else "Other",
            due_date=due_date,
            recurrence=recurrence if recurrence in RECURRENCE_TYPES else None,
            tax_relevant=tax_relevant,
            entity_id=entity_id,
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
            entity_id=bill.entity_id,
        )
        bill.last_paid_date = paid_date
        self._save_bills()
        log.info("Bill paid: '%s' $%.2f on %s", bill.name, paid_amount, paid_date)
        # 2026-09-11 gamification pass — same "recurring completion is a
        # real, distinct event each time" reasoning as
        # core.maintenance_manager.MaintenanceManager.mark_complete().
        # Hooked here, not inside add_expense() above — a plain expense
        # entry isn't a "completion" the way deliberately marking a bill
        # paid is.
        # "My Hero's Path" (2026-09-11) — Household Management (Social
        # category) is the natural skill for staying on top of bills.
        grant_xp(
            self.context,
            5,
            "\U0001F4B0 Bill paid!",
            f"'{bill.name}' is squared away.",
            skill_weights=[SkillWeight("household_management", 5)],
        )
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
        entity_id: str = "",
        notes: str = "",
    ) -> IncomeSource:
        if expected_amount < 0:
            raise ValueError(f"expected_amount must not be negative, got {expected_amount}")
        source = IncomeSource(
            source_id=uuid.uuid4().hex[:10],
            name=name,
            expected_amount=expected_amount,
            category=category if category in INCOME_CATEGORIES else "Other",
            next_date=next_date,
            recurrence=recurrence if recurrence in RECURRENCE_TYPES else None,
            entity_id=entity_id,
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
            entity_id=source.entity_id,
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
        entity_id: str = "",
        plaid_transaction_id: str = "",
        notes: str = "",
    ) -> IncomeEntry:
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}")
        entry = IncomeEntry(
            entry_id=uuid.uuid4().hex[:10],
            amount=amount,
            category=category if category in INCOME_CATEGORIES else "Other",
            description=description,
            date=date or _today_iso(),
            tax_relevant=tax_relevant,
            property_id=property_id,
            entity_id=entity_id,
            plaid_transaction_id=plaid_transaction_id,
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

    def get_income_by_plaid_transaction_id(self, transaction_id: str) -> Optional[IncomeEntry]:
        """The dedup lookup a repeat core.plaid_manager sync uses before
        deciding whether to add a new entry or update an existing one."""
        if not transaction_id:
            return None
        for entry in self._income:
            if entry.plaid_transaction_id == transaction_id:
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
        entity_id: str = "",
        plaid_transaction_id: str = "",
        payee: str = "",
        notes: str = "",
        project_id: str = "",
        asset_id: str = "",
        asset_purchase: bool = False,
        items: Optional[list] = None,
    ) -> ExpenseEntry:
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}")
        entry = ExpenseEntry(
            entry_id=uuid.uuid4().hex[:10],
            amount=amount,
            category=category if category in EXPENSE_CATEGORIES else "Other",
            description=description,
            date=date or _today_iso(),
            tax_relevant=tax_relevant,
            bill_id=bill_id,
            property_id=property_id,
            entity_id=entity_id,
            plaid_transaction_id=plaid_transaction_id,
            payee=payee,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
            project_id=project_id,
            asset_id=asset_id,
            asset_purchase=asset_purchase,
            items=list(items or []),
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

    def get_expense_by_plaid_transaction_id(self, transaction_id: str) -> Optional[ExpenseEntry]:
        """The dedup lookup a repeat core.plaid_manager sync uses before
        deciding whether to add a new entry or update an existing one."""
        if not transaction_id:
            return None
        for entry in self._expenses:
            if entry.plaid_transaction_id == transaction_id:
                return entry
        return None

    def all_expenses(self) -> list[ExpenseEntry]:
        return sorted(self._expenses, key=lambda e: e.date, reverse=True)

    # ------------------------------------------------------------------
    # Reporting — computed on demand, never persisted (see module docstring)
    # ------------------------------------------------------------------

    def total_income(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None,
        tax_relevant_only: bool = False, entity_id: Optional[str] = None,
    ) -> float:
        return sum(
            i.amount for i in self._income
            if _in_range(i.date, start_date, end_date) and (not tax_relevant_only or i.tax_relevant)
            and (entity_id is None or i.entity_id == entity_id)
        )

    def total_expenses(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None,
        tax_relevant_only: bool = False, entity_id: Optional[str] = None,
    ) -> float:
        return sum(
            e.amount for e in self._expenses
            if _in_range(e.date, start_date, end_date) and (not tax_relevant_only or e.tax_relevant)
            and (entity_id is None or e.entity_id == entity_id)
        )

    def net_cash_flow(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        return self.total_income(start_date, end_date) - self.total_expenses(start_date, end_date)

    def total_expenses_by_category(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None, entity_id: Optional[str] = None,
    ) -> dict[str, float]:
        """Actual spending per category over a date range — the
        "actual" half of a budget-target comparison. Only categories
        with at least one matching expense are present in the result
        (no zero-filled entries for untouched categories)."""
        totals: dict[str, float] = {}
        for expense in self._expenses:
            if not _in_range(expense.date, start_date, end_date):
                continue
            if entity_id is not None and expense.entity_id != entity_id:
                continue
            totals[expense.category] = totals.get(expense.category, 0.0) + expense.amount
        return totals

    def total_income_by_category(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None, entity_id: Optional[str] = None,
    ) -> dict[str, float]:
        """Actual income per category over a date range — the income-side
        counterpart to total_expenses_by_category(). Only categories with
        at least one matching income entry are present (no zero-filled
        entries for untouched categories)."""
        totals: dict[str, float] = {}
        for entry in self._income:
            if not _in_range(entry.date, start_date, end_date):
                continue
            if entity_id is not None and entry.entity_id != entity_id:
                continue
            totals[entry.category] = totals.get(entry.category, 0.0) + entry.amount
        return totals

    def payees_over_1099_threshold(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        entity_id: Optional[str] = None,
        threshold: float = US_1099_NEC_THRESHOLD,
    ) -> dict[str, float]:
        """Real IRS 1099-NEC threshold applied to real business-tagged
        payments — a factual comparison, never a computed tax liability
        or a "you must file" directive. Only expenses tied to a
        property (property_id) or a BusinessEntity (entity_id) count —
        1099-NEC obligations arise from payments made in the course of
        a trade or business; a household's personal payment to a
        contractor for their own primary residence generally doesn't
        trigger one. Grouped case-insensitively by payee (trimmed) so
        "Ace Plumbing"/"ace plumbing" aggregate together; the first-
        seen exact casing is used for display. Only payees at or over
        threshold are returned — an empty dict is a real "nobody's
        crossed it yet" answer, not "nothing computed"."""
        totals: dict[str, float] = {}
        display_names: dict[str, str] = {}
        for expense in self._expenses:
            payee = expense.payee.strip()
            if not payee:
                continue
            if not (expense.property_id or expense.entity_id):
                continue
            if entity_id is not None and expense.entity_id != entity_id:
                continue
            if not _in_range(expense.date, start_date, end_date):
                continue
            key = payee.lower()
            totals[key] = totals.get(key, 0.0) + expense.amount
            display_names.setdefault(key, payee)
        return {display_names[key]: amount for key, amount in totals.items() if amount >= threshold}

    # ------------------------------------------------------------------
    # Budget targets — planned monthly spending per category, deliberately
    # minimal (no yearly overrides, no envelope rollover), see module docstring
    # ------------------------------------------------------------------

    def set_budget_target(self, category: str, monthly_amount: float, entity_id: str = "") -> BudgetTarget:
        """Upsert — one target per (category, entity_id) pair; calling
        again for the same pair replaces it. entity_id="" (default) is
        the household/no-specific-entity bucket."""
        if category not in EXPENSE_CATEGORIES:
            raise ValueError(f"Unknown expense category '{category}'.")
        if monthly_amount < 0:
            raise ValueError(f"monthly_amount must not be negative, got {monthly_amount}")
        existing = self.get_budget_target(category, entity_id)
        if existing is not None:
            existing.monthly_amount = monthly_amount
        else:
            self._budget_targets.append(
                BudgetTarget(category=category, monthly_amount=monthly_amount, entity_id=entity_id)
            )
        self._save_budget_targets()
        return self.get_budget_target(category, entity_id)

    def delete_budget_target(self, category: str, entity_id: str = "") -> None:
        self._budget_targets = [
            t for t in self._budget_targets if not (t.category == category and t.entity_id == entity_id)
        ]
        self._save_budget_targets()

    def get_budget_target(self, category: str, entity_id: str = "") -> Optional[BudgetTarget]:
        for target in self._budget_targets:
            if target.category == category and target.entity_id == entity_id:
                return target
        return None

    def all_budget_targets(self, entity_id: Optional[str] = None) -> list[BudgetTarget]:
        """entity_id=None (default) returns every stored target across
        every entity, unfiltered — same "None means no filter"
        convention total_income()/total_expenses() already use. Pass an
        explicit entity_id (including "" for the household/unassigned
        bucket) to scope to one entity's own target set — callers that
        display "one row per category" (the Summary tab's Budget
        Targets section, the Business Report) always pass an explicit
        value, since an unfiltered mix could have more than one target
        for the same category name."""
        targets = self._budget_targets if entity_id is None else [t for t in self._budget_targets if t.entity_id == entity_id]
        return sorted(targets, key=lambda t: t.category)

    # ------------------------------------------------------------------
    # Business entities (LLCs/sole props/etc.) — a real, user-named record
    # with a stable generated id, same shape as Property/IncomeSource, NOT
    # BudgetTarget's "upsert keyed by a fixed category" shape (an entity
    # name has no fixed universe to key off).
    # ------------------------------------------------------------------

    def add_business_entity(self, name: str, entity_type: str = "LLC", notes: str = "") -> BusinessEntity:
        entity = BusinessEntity(
            entity_id=uuid.uuid4().hex[:10],
            name=name,
            entity_type=entity_type if entity_type in BUSINESS_ENTITY_TYPES else "Other",
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._business_entities.append(entity)
        self._save_business_entities()
        log.info("Business entity added: '%s' (%s)", entity.name, entity.entity_type)
        return entity

    def update_business_entity(self, entity_id: str, **fields) -> BusinessEntity:
        entity = self.get_business_entity(entity_id)
        if entity is None:
            raise ValueError(f"No business entity with id '{entity_id}'.")
        for key, value in fields.items():
            if not hasattr(entity, key):
                raise ValueError(f"BusinessEntity has no field '{key}'.")
            setattr(entity, key, value)
        if entity.entity_type not in BUSINESS_ENTITY_TYPES:
            entity.entity_type = "Other"
        self._save_business_entities()
        return entity

    def delete_business_entity(self, entity_id: str) -> None:
        """Deletes the BusinessEntity record only — does NOT touch any
        Income/Expense/Property rows already tagged with this entity_id
        (same 'deleting a parent doesn't delete real history' stance
        RealEstateManager.delete_property() already takes). Those rows
        are left pointing at a now-nonexistent id; every reader (GUI
        combos, filters) treats that the same as unassigned."""
        self._business_entities = [e for e in self._business_entities if e.entity_id != entity_id]
        self._save_business_entities()

    def get_business_entity(self, entity_id: str) -> Optional[BusinessEntity]:
        for entity in self._business_entities:
            if entity.entity_id == entity_id:
                return entity
        return None

    def all_business_entities(self) -> list[BusinessEntity]:
        return sorted(self._business_entities, key=lambda e: e.name.lower())

    # ------------------------------------------------------------------
    # Debts — payoff-tracked liabilities (credit cards, personal/auto/
    # student loans). NOT mortgages — see Debt's own docstring above.
    # ------------------------------------------------------------------

    def add_debt(
        self,
        name: str,
        balance: float,
        interest_rate: float,
        minimum_payment: float = 0.0,
        debt_type: str = "Credit Card",
        promo_apr: Optional[float] = None,
        promo_expires_date: Optional[str] = None,
        entity_id: str = "",
        notes: str = "",
        plaid_account_id: str = "",
        plaid_item_id: str = "",
    ) -> Debt:
        if balance < 0:
            raise ValueError(f"balance must not be negative, got {balance}")
        if interest_rate < 0:
            raise ValueError(f"interest_rate must not be negative, got {interest_rate}")
        if minimum_payment < 0:
            raise ValueError(f"minimum_payment must not be negative, got {minimum_payment}")
        debt = Debt(
            debt_id=uuid.uuid4().hex[:10],
            name=name,
            balance=balance,
            interest_rate=interest_rate,
            minimum_payment=minimum_payment,
            debt_type=debt_type if debt_type in DEBT_TYPES else "Other",
            promo_apr=promo_apr,
            # A promo rate with no expiration date doesn't mean
            # anything real — see effective_apr()'s own reasoning.
            promo_expires_date=promo_expires_date if promo_apr is not None else None,
            entity_id=entity_id,
            plaid_account_id=plaid_account_id,
            plaid_item_id=plaid_item_id,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._debts.append(debt)
        self._save_debts()
        log.info("Debt added: '%s' $%.2f at %.2f%% APR", debt.name, debt.balance, debt.interest_rate)
        return debt

    def update_debt(self, debt_id: str, **fields) -> Debt:
        debt = self.get_debt(debt_id)
        if debt is None:
            raise ValueError(f"No debt with id '{debt_id}'.")
        for key, value in fields.items():
            if not hasattr(debt, key):
                raise ValueError(f"Debt has no field '{key}'.")
            setattr(debt, key, value)
        if debt.balance < 0:
            debt.balance = 0.0
        if debt.interest_rate < 0:
            debt.interest_rate = 0.0
        if debt.minimum_payment < 0:
            debt.minimum_payment = 0.0
        if debt.debt_type not in DEBT_TYPES:
            debt.debt_type = "Other"
        if debt.promo_apr is None:
            debt.promo_expires_date = None
        self._save_debts()
        return debt

    def delete_debt(self, debt_id: str) -> None:
        self._debts = [d for d in self._debts if d.debt_id != debt_id]
        self._save_debts()

    def get_debt(self, debt_id: str) -> Optional[Debt]:
        for debt in self._debts:
            if debt.debt_id == debt_id:
                return debt
        return None

    def get_debt_by_plaid_account_id(self, account_id: str) -> Optional[Debt]:
        """The dedup lookup a repeat core.plaid_manager liabilities sync
        uses before deciding whether to add a new debt or update one."""
        if not account_id:
            return None
        for debt in self._debts:
            if debt.plaid_account_id == account_id:
                return debt
        return None

    def unlink_plaid_debts_for_item(self, item_id: str) -> int:
        """Called when one Plaid bank connection is disconnected: its
        debts stay (they're still real money owed, possibly with the
        user's own promo/notes edits) but become manual debts that no
        future sync will touch. Returns how many were unlinked."""
        if not item_id:
            return 0
        unlinked = 0
        for debt in self._debts:
            if debt.plaid_item_id == item_id:
                debt.plaid_item_id = ""
                debt.plaid_account_id = ""
                unlinked += 1
        if unlinked:
            self._save_debts()
        return unlinked

    def remove_plaid_imported_data(self) -> tuple[int, int, int]:
        """Deletes every income/expense entry and debt that came from a
        Plaid sync (non-empty plaid_transaction_id/plaid_account_id),
        leaving manual entries untouched. Used by a Plaid reset — e.g.
        to clear fake Sandbox data before connecting real accounts.
        Everything removed is re-importable by syncing again. Returns
        (income_removed, expenses_removed, debts_removed)."""
        income_before, expenses_before, debts_before = len(self._income), len(self._expenses), len(self._debts)
        self._income = [i for i in self._income if not i.plaid_transaction_id]
        self._expenses = [e for e in self._expenses if not e.plaid_transaction_id]
        self._debts = [d for d in self._debts if not d.plaid_account_id]
        removed = (
            income_before - len(self._income),
            expenses_before - len(self._expenses),
            debts_before - len(self._debts),
        )
        if removed[0]:
            self._save_income()
        if removed[1]:
            self._save_expenses()
        if removed[2]:
            self._save_debts()
        return removed

    def all_debts(self, entity_id: Optional[str] = None) -> list[Debt]:
        """entity_id=None (default) returns every stored debt, unfiltered
        — same "None means no filter" convention total_income()/
        all_budget_targets() already use."""
        debts = self._debts if entity_id is None else [d for d in self._debts if d.entity_id == entity_id]
        return sorted(debts, key=lambda d: d.name.lower())

    def record_debt_payment(
        self, debt_id: str, amount: float, date: Optional[str] = None, notes: str = "",
    ) -> ExpenseEntry:
        """Records a real ExpenseEntry (category "Debt Payment") AND
        reduces the debt's balance — one action, two real effects, same
        shape as mark_bill_paid()/mark_income_received(). Balance is
        clamped at $0 rather than going negative — an overpayment's
        excess isn't tracked as a separate credit, same boundary
        core.material_manager.MaterialManager.adjust_quantity() already
        draws for a shared numeric quantity."""
        debt = self.get_debt(debt_id)
        if debt is None:
            raise ValueError(f"No debt with id '{debt_id}'.")
        if amount < 0:
            raise ValueError(f"amount must not be negative, got {amount}")
        payment_date = date or _today_iso()

        entry = self.add_expense(
            amount=amount,
            category="Debt Payment",
            description=debt.name,
            date=payment_date,
            entity_id=debt.entity_id,
            notes=notes,
        )
        debt.balance = max(0.0, debt.balance - amount)
        debt.last_payment_date = payment_date
        self._save_debts()
        log.info("Debt payment recorded: '%s' $%.2f on %s (balance now $%.2f)", debt.name, amount, payment_date, debt.balance)
        # "My Hero's Path" (2026-09-11) — same household-management XP
        # hook mark_bill_paid() already grants for squaring away a bill.
        grant_xp(
            self.context,
            5,
            "\U0001F4B3 Debt payment made!",
            f"Paid down '{debt.name}'.",
            skill_weights=[SkillWeight("household_management", 5)],
        )
        return entry

    def debt_payoff_priority(
        self, strategy: str = "hybrid", entity_id: Optional[str] = None, today: Optional[date] = None,
    ) -> list[DebtPriority]:
        """Reporting — computed on demand, never persisted (see module
        docstring). Thin wrapper: the real ordering logic is the pure
        rank_debts() function above, testable without a manager."""
        return rank_debts(self.all_debts(entity_id), today or date.today(), strategy)

    def total_debt_balance(self, entity_id: Optional[str] = None) -> float:
        return sum(d.balance for d in self.all_debts(entity_id))

    def total_minimum_debt_payments(self, entity_id: Optional[str] = None) -> float:
        return sum(d.minimum_payment for d in self.all_debts(entity_id) if d.balance > 0)

    def weighted_average_debt_apr(self, entity_id: Optional[str] = None, today: Optional[date] = None) -> float:
        """Balance-weighted average of each open debt's effective_apr()
        today — a single real "how bad is this, on average" figure,
        rather than a bare unweighted average that'd let a small
        high-rate balance and a large low-rate one look equally
        concerning. Returns 0.0 when there's no open debt (a real
        answer, not a division-by-zero guard treated as an error)."""
        today = today or date.today()
        open_debts = [d for d in self.all_debts(entity_id) if d.balance > 0]
        total_balance = sum(d.balance for d in open_debts)
        if total_balance <= 0:
            return 0.0
        return sum(effective_apr(d, today) * d.balance for d in open_debts) / total_balance
