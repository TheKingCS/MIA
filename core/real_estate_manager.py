"""
core.real_estate_manager
===========================

Property records for a real estate portfolio — values, mortgage
balance/equity, and links to the existing systems that already own the
rest of what a property needs tracked, rather than duplicating them:

- **Rental income/expenses** are core.budget_manager.IncomeEntry/
  ExpenseEntry rows with their (already-shipped) property_id field set
  — this manager doesn't store its own copy of transactions, it filters
  Budget's. record_rental_income()/record_property_expense() are thin
  wrappers over context.budget.add_income()/add_expense(); income_for_
  property()/expenses_for_property() filter context.budget.all_income()/
  all_expenses() by property_id.
- **Maintenance history/plans** are a core.maintenance_manager
  .MaintenanceAsset (category="Property") — Property.maintenance_asset_id
  is just a reference to one; this manager never reads or writes
  Maintenance data itself, the module layer calls
  context.maintenance.tasks_for_asset() directly when displaying it.

Deliberately supersedes docs/VISION.md's original "Real Estate
Portfolio" plan (a *separate* React dashboard exporting JSON snapshots
for core.finance_manager.py's read-only ingestion, same as the Kraken
agent) — the user chose a native module instead once maintenance-
history linking mattered, not an oversight.

current_value is a manually-updated estimate, same v1 discipline as
every other manager here before a real live-valuation feed exists (no
Zillow/Redfin API integration). cap_rate()/net_operating_income() are
computed on demand, never persisted, same stance core.ledger_manager
.LedgerManager.net_profit() and core.budget_manager's own reporting
functions already take.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

if TYPE_CHECKING:
    from core.budget_manager import ExpenseEntry, IncomeEntry

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROPERTIES_FILE = _DATA_DIR / "properties.json"

PROPERTY_TYPES = ["Primary Residence", "Rental", "Investment", "Land", "Other"]


@dataclass
class Property:
    property_id: str
    name: str  # "123 Main St", "Lake Cabin"
    property_type: str = "Rental"  # one of PROPERTY_TYPES
    purchase_date: str = ""
    purchase_price: float = 0.0
    current_value: float = 0.0  # manually updated estimate — no live valuation feed
    mortgage_balance: float = 0.0
    entity_id: str = ""  # set when this property belongs to a core.budget_manager.BusinessEntity (LLC/etc.)
    maintenance_asset_id: str = ""  # optional link to a core.maintenance_manager.MaintenanceAsset (category="Property")
    # 2026-09-09: depreciation tracking. land_value is the portion of
    # purchase_price that's NOT depreciable (land itself never
    # depreciates under US tax law); placed_in_service_date is when
    # depreciation starts — "" falls back to purchase_date, see
    # annual_depreciation()/accumulated_depreciation() below.
    land_value: float = 0.0
    placed_in_service_date: str = ""
    # 2026-09-09: mortgage amortization. All four are optional — 0.0/""
    # means "not entered," and every function below (has_loan_terms()
    # etc.) treats that as "no amortization data," never a guess.
    # loan_start_date falls back to purchase_date, same convention
    # placed_in_service_date uses.
    original_loan_amount: float = 0.0
    interest_rate_pct: float = 0.0  # annual rate, e.g. 6.5 for 6.5% APR
    loan_term_months: int = 0
    loan_start_date: str = ""
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id, "name": self.name, "property_type": self.property_type,
            "purchase_date": self.purchase_date, "purchase_price": self.purchase_price,
            "current_value": self.current_value, "mortgage_balance": self.mortgage_balance,
            "entity_id": self.entity_id,
            "maintenance_asset_id": self.maintenance_asset_id,
            "land_value": self.land_value, "placed_in_service_date": self.placed_in_service_date,
            "original_loan_amount": self.original_loan_amount, "interest_rate_pct": self.interest_rate_pct,
            "loan_term_months": self.loan_term_months, "loan_start_date": self.loan_start_date,
            "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Property":
        return Property(
            property_id=data.get("property_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            property_type=data.get("property_type", "Rental"),
            purchase_date=data.get("purchase_date", ""),
            purchase_price=data.get("purchase_price", 0.0),
            current_value=data.get("current_value", 0.0),
            mortgage_balance=data.get("mortgage_balance", 0.0),
            entity_id=data.get("entity_id", ""),
            maintenance_asset_id=data.get("maintenance_asset_id", ""),
            land_value=data.get("land_value", 0.0),
            placed_in_service_date=data.get("placed_in_service_date", ""),
            original_loan_amount=data.get("original_loan_amount", 0.0),
            interest_rate_pct=data.get("interest_rate_pct", 0.0),
            loan_term_months=data.get("loan_term_months", 0),
            loan_start_date=data.get("loan_start_date", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


def equity(property_: Property) -> float:
    """Pure logic — testable without Qt."""
    return property_.current_value - property_.mortgage_balance


# US IRS Publication 946's straight-line MACRS period for residential
# rental real property. Only Rental/Investment property types are
# eligible for depreciation at all — a Primary Residence is never
# depreciated for tax purposes even if it has a real depreciable basis.
RESIDENTIAL_USEFUL_LIFE_YEARS = 27.5
# Public (not the original _DEPRECIABLE_PROPERTY_TYPES name) since
# 2026-09-09: depreciation eligibility and Schedule E eligibility are
# the same real tax-law rule — core/business_report.py's Schedule E
# section shares this constant rather than hardcoding it a second time.
SCHEDULE_E_ELIGIBLE_PROPERTY_TYPES = {"Rental", "Investment"}


def depreciable_basis(property_: Property) -> float:
    """Pure logic — testable without Qt. Land is never depreciable —
    the depreciable basis is purchase price minus the land's own
    value, never negative (a land_value entered larger than
    purchase_price clamps to a $0 basis rather than going negative)."""
    return max(0.0, property_.purchase_price - property_.land_value)


def annual_depreciation(property_: Property, useful_life_years: float = RESIDENTIAL_USEFUL_LIFE_YEARS) -> float:
    """Pure logic — testable without Qt. Straight-line depreciation
    (basis / useful life) — a real, honest approximation, not a full
    tax-filing computation: it doesn't implement the mid-month
    convention IRS Form 4562 technically requires for the placed-in-
    service/disposal years, same "real correct-shaped number, not
    fabricated precision" boundary core.maintenance_manager's
    Prediction feature already draws."""
    if property_.property_type not in SCHEDULE_E_ELIGIBLE_PROPERTY_TYPES or useful_life_years <= 0:
        return 0.0
    return depreciable_basis(property_) / useful_life_years


def accumulated_depreciation(
    property_: Property, as_of: date, useful_life_years: float = RESIDENTIAL_USEFUL_LIFE_YEARS
) -> float:
    """Pure logic — testable without Qt. Years elapsed since the
    property was placed in service (placed_in_service_date, falling
    back to purchase_date if never set) times the annual rate, clamped
    to [0, depreciable_basis] — never negative (as_of before the start
    date) and never past the full basis (fully depreciated)."""
    annual = annual_depreciation(property_, useful_life_years)
    if annual <= 0.0:
        return 0.0
    start_str = property_.placed_in_service_date or property_.purchase_date
    try:
        start = date.fromisoformat(start_str)
    except ValueError:
        return 0.0
    years_elapsed = (as_of - start).days / 365.25
    if years_elapsed <= 0:
        return 0.0
    return min(depreciable_basis(property_), annual * years_elapsed)


def has_loan_terms(property_: Property) -> bool:
    """Pure logic — testable without Qt. True only when all three real
    inputs an amortization schedule needs are actually entered — every
    function below treats a missing/zero value as "no amortization
    data," never guesses a default rate/term."""
    return (
        property_.original_loan_amount > 0
        and property_.interest_rate_pct > 0
        and property_.loan_term_months > 0
    )


def monthly_payment(property_: Property) -> float:
    """Pure logic — testable without Qt. Standard fixed-rate
    amortization formula: M = P*r(1+r)^n / ((1+r)^n - 1), where r is
    the monthly interest rate and n the term in months. Returns 0.0
    when has_loan_terms() is False."""
    if not has_loan_terms(property_):
        return 0.0
    monthly_rate = property_.interest_rate_pct / 100 / 12
    n = property_.loan_term_months
    principal = property_.original_loan_amount
    if monthly_rate == 0:
        return principal / n
    factor = (1 + monthly_rate) ** n
    return principal * monthly_rate * factor / (factor - 1)


def amortization_schedule(property_: Property) -> list[dict]:
    """Pure logic — testable without Qt. Full month-by-month schedule
    from loan_start_date (falling back to purchase_date, same
    convention placed_in_service_date uses) for loan_term_months
    payments — real fixed-rate amortization math, not an
    approximation: each month's interest = remaining balance * monthly
    rate, principal = payment - interest (clamped to the remaining
    balance on the final payment so real rounding never drives the
    balance negative). Returns [] when has_loan_terms() is False or
    loan_start_date/purchase_date can't be parsed."""
    if not has_loan_terms(property_):
        return []
    start_str = property_.loan_start_date or property_.purchase_date
    try:
        start = date.fromisoformat(start_str)
    except ValueError:
        return []

    payment = monthly_payment(property_)
    monthly_rate = property_.interest_rate_pct / 100 / 12
    balance = property_.original_loan_amount
    schedule = []
    year, month = start.year, start.month
    for _ in range(property_.loan_term_months):
        interest = balance * monthly_rate
        principal = min(payment - interest, balance)
        balance = max(0.0, balance - principal)
        schedule.append({
            "date": date(year, month, 1).isoformat(),
            "payment": principal + interest,
            "principal": principal,
            "interest": interest,
            "balance": balance,
        })
        month += 1
        if month == 13:
            month = 1
            year += 1
    return schedule


def interest_paid_in_range(property_: Property, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
    """Pure logic — testable without Qt. The real interest-only
    portion of this property's mortgage payments over a date range —
    used by core/business_report.py's Schedule E section to replace
    the full Mortgage/Rent category amount (which includes non-
    deductible principal) once real loan terms are entered."""
    return sum(
        entry["interest"] for entry in amortization_schedule(property_)
        if _in_range(entry["date"], start_date, end_date)
    )


def principal_paid_in_range(property_: Property, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
    """Pure logic — testable without Qt."""
    return sum(
        entry["principal"] for entry in amortization_schedule(property_)
        if _in_range(entry["date"], start_date, end_date)
    )


def remaining_balance_as_of(property_: Property, as_of: date) -> Optional[float]:
    """Pure logic — testable without Qt. None when has_loan_terms() is
    False. This is a PROJECTION from the entered loan terms, not the
    same number as Property.mortgage_balance (the manually-tracked
    figure equity()/net_operating_income()/the portfolio table already
    use) — a real mortgage can diverge from a clean amortization
    schedule (extra principal payments, a refinance), so the two are
    deliberately never conflated. Before the first payment, the full
    original_loan_amount is still owed; after the last payment, 0.0."""
    schedule = amortization_schedule(property_)
    if not schedule:
        return None
    as_of_str = as_of.isoformat()
    balance = property_.original_loan_amount
    for entry in schedule:
        if entry["date"] > as_of_str:
            break
        balance = entry["balance"]
    return balance


def payoff_date(property_: Property) -> Optional[str]:
    """Pure logic — testable without Qt. None when has_loan_terms() is
    False."""
    schedule = amortization_schedule(property_)
    return schedule[-1]["date"] if schedule else None


def _in_range(entry_date: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
    """Pure logic — testable without I/O. Same ISO-date-string-compare
    shape as core.ledger_manager/core.budget_manager's own _in_range()."""
    if start_date and entry_date < start_date:
        return False
    if end_date and entry_date > end_date:
        return False
    return True


class RealEstateManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._properties: list[Property] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _PROPERTIES_FILE.exists():
            self._properties = []
            return
        try:
            raw = json.loads(_PROPERTIES_FILE.read_text(encoding="utf-8"))
            self._properties = [Property.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load properties.json — starting with an empty list.")
            notify_data_corruption(self.context, "properties.json")
            self._properties = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_PROPERTIES_FILE,
            json.dumps([p.to_dict() for p in self._properties], indent=2), encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Property CRUD
    # ------------------------------------------------------------------

    def add_property(
        self,
        name: str,
        property_type: str = "Rental",
        purchase_date: str = "",
        purchase_price: float = 0.0,
        current_value: float = 0.0,
        mortgage_balance: float = 0.0,
        entity_id: str = "",
        land_value: float = 0.0,
        placed_in_service_date: str = "",
        original_loan_amount: float = 0.0,
        interest_rate_pct: float = 0.0,
        loan_term_months: int = 0,
        loan_start_date: str = "",
        notes: str = "",
    ) -> Property:
        prop = Property(
            property_id=uuid.uuid4().hex[:10],
            name=name,
            property_type=property_type if property_type in PROPERTY_TYPES else "Other",
            purchase_date=purchase_date,
            purchase_price=max(0.0, purchase_price),
            current_value=max(0.0, current_value),
            mortgage_balance=max(0.0, mortgage_balance),
            entity_id=entity_id,
            land_value=max(0.0, land_value),
            placed_in_service_date=placed_in_service_date,
            original_loan_amount=max(0.0, original_loan_amount),
            interest_rate_pct=max(0.0, interest_rate_pct),
            loan_term_months=max(0, loan_term_months),
            loan_start_date=loan_start_date,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._properties.append(prop)
        self._save()
        log.info("Property added: '%s' (%s)", prop.name, prop.property_type)
        return prop

    def update_property(self, property_id: str, **fields) -> Property:
        prop = self.get_property(property_id)
        if prop is None:
            raise ValueError(f"No property with id '{property_id}'.")
        for key, value in fields.items():
            if not hasattr(prop, key):
                raise ValueError(f"Property has no field '{key}'.")
            setattr(prop, key, value)
        if prop.property_type not in PROPERTY_TYPES:
            prop.property_type = "Other"
        for numeric_field in (
            "purchase_price", "current_value", "mortgage_balance", "land_value",
            "original_loan_amount", "interest_rate_pct",
        ):
            if getattr(prop, numeric_field) < 0:
                setattr(prop, numeric_field, 0.0)
        if prop.loan_term_months < 0:
            prop.loan_term_months = 0
        self._save()
        return prop

    def delete_property(self, property_id: str) -> None:
        """Deletes the Property record only — does NOT delete its
        linked Maintenance asset (that's a real, independently-owned
        asset the user may still want tracked even if this Property
        record goes away) or any Budget income/expense entries already
        recorded against it (real financial history shouldn't vanish
        because a portfolio entry was removed — same "deleting a
        parent doesn't delete real history" stance
        core.ledger_manager's delete_project() already takes for its
        own linked Tasks)."""
        self._properties = [p for p in self._properties if p.property_id != property_id]
        self._save()

    def get_property(self, property_id: str) -> Optional[Property]:
        for prop in self._properties:
            if prop.property_id == property_id:
                return prop
        return None

    def all_properties(self) -> list[Property]:
        return sorted(self._properties, key=lambda p: p.name.lower())

    # ------------------------------------------------------------------
    # Rental income / property expenses — thin wrappers/filters over
    # core.budget_manager, not separately-stored data (see module docstring)
    # ------------------------------------------------------------------

    def record_rental_income(
        self, property_id: str, amount: float, date_str: Optional[str] = None, description: str = "", notes: str = ""
    ) -> "IncomeEntry":
        prop = self.get_property(property_id)
        if prop is None:
            raise ValueError(f"No property with id '{property_id}'.")
        return self.context.budget.add_income(
            amount=amount, category="Rental Income", description=description, date=date_str,
            property_id=property_id, entity_id=prop.entity_id, notes=notes,
        )

    def record_property_expense(
        self,
        property_id: str,
        amount: float,
        category: str = "Maintenance",
        date_str: Optional[str] = None,
        description: str = "",
        notes: str = "",
    ) -> "ExpenseEntry":
        prop = self.get_property(property_id)
        if prop is None:
            raise ValueError(f"No property with id '{property_id}'.")
        return self.context.budget.add_expense(
            amount=amount, category=category, description=description, date=date_str,
            property_id=property_id, entity_id=prop.entity_id, notes=notes,
        )

    def income_for_property(self, property_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> list["IncomeEntry"]:
        return [
            i for i in self.context.budget.all_income()
            if i.property_id == property_id and _in_range(i.date, start_date, end_date)
        ]

    def expenses_for_property(self, property_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> list["ExpenseEntry"]:
        return [
            e for e in self.context.budget.all_expenses()
            if e.property_id == property_id and _in_range(e.date, start_date, end_date)
        ]

    # ------------------------------------------------------------------
    # Reporting — computed on demand, never persisted
    # ------------------------------------------------------------------

    def net_operating_income(self, property_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        """Rental income minus operating expenses for this property.
        Standard real-estate NOI convention: mortgage principal/interest
        is never counted as an operating expense here (a mortgage
        payment is debt service, not an operating cost) — if the user
        logs mortgage payments as Budget expenses against this
        property, they'll still show up in expenses_for_property()'s
        raw list, just excluded from this specific NOI figure by
        category, same "honest about which convention this matches"
        approach cap_rate() below takes."""
        income = sum(i.amount for i in self.income_for_property(property_id, start_date, end_date))
        expenses = sum(
            e.amount for e in self.expenses_for_property(property_id, start_date, end_date)
            if e.category != "Mortgage/Rent"
        )
        return income - expenses

    def cap_rate(self, property_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[float]:
        """Net operating income / current property value, as a
        fraction (multiply by 100 for a percentage), for whatever date
        range is passed — deliberately not auto-annualized (a "days
        elapsed -> scale to 365" correction is fragile for open-ended
        ranges and easy to get subtly wrong); pass a full-year range
        (e.g. "This Year", same as core.budget_manager's own Summary
        reporting) for a true annual cap rate. None — never a
        fabricated number — when the property doesn't exist or its
        current_value is 0 (nothing to divide by)."""
        prop = self.get_property(property_id)
        if prop is None or prop.current_value <= 0:
            return None
        noi = self.net_operating_income(property_id, start_date, end_date)
        return noi / prop.current_value
