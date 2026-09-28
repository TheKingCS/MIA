"""
core.business_use
====================

Finance #3 (2026-09-28): the business-use share of personal equipment,
starting with the owner's mower ("help me with write offs for my real
estate businesses with things like the mower if I do a certain amount
of contracted lawn care with it").

**Records and arithmetic, not tax advice.** A tool used partly for
business has a business-use percentage, and that share of its costs is
a business cost. What this module does is keep the record that backs
the percentage up (dated business jobs, and who they were for) and do
the arithmetic from MIA's own data. How to depreciate the purchase
(Section 179, bonus, regular depreciation) and which schedule each
share goes on are decisions for the owner or a tax preparer. The
worksheet says so and shows its work.

**How the percentage is measured.** The owner logs business use as it
happens ("mowed the Maple duplex, 2 hours"). Total use for the year
comes from the tool's hour meter (core/homestead_costs.hour_readings):
the last reading in the year minus the last reading before it (or the
first reading in the year, if there's nothing earlier). Personal use is
everything that isn't logged as business. Without meter readings, total
use is what was logged, business and personal, and the worksheet flags
that as a weaker record.

Costs come from Finance #2's expense tags (`ExpenseEntry.asset_id`):
this year's running costs (fuel, repairs, maintenance) and the purchase
price as the cost basis.
"""

from __future__ import annotations

import html
import json
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.homestead_costs import hour_readings
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_USE_FILE = _DATA_DIR / "business_use.json"

BUSINESS = "business"
PERSONAL = "personal"

DISCLAIMER = (
    "These are records and arithmetic from MIA's own data, not tax advice. How to depreciate the purchase "
    "(for example Section 179, bonus or regular depreciation) and where each amount goes on your return are "
    "decisions for you or your tax preparer."
)


@dataclass
class UseEntry:
    entry_id: str
    asset_id: str
    date: str  # ISO date
    hours: float
    purpose: str = BUSINESS  # "business" | "personal"
    entity_id: str = ""  # which business (core.budget_manager.BusinessEntity), if any
    property_id: str = ""  # a rental it was for (core.real_estate_manager.Property), if any
    client: str = ""  # who the work was for, free text ("Johnson lawn", "Maple duplex")
    note: str = ""
    created_at: str = ""

    @staticmethod
    def from_dict(data: dict) -> "UseEntry":
        fields = UseEntry.__dataclass_fields__
        return UseEntry(**{k: v for k, v in data.items() if k in fields})


class BusinessUseManager:
    def __init__(self, context) -> None:
        self.context = context
        self._entries: list[UseEntry] = []
        self._load()

    def _load(self) -> None:
        if not _USE_FILE.exists():
            return
        try:
            self._entries = [UseEntry.from_dict(d) for d in json.loads(_USE_FILE.read_text(encoding="utf-8"))]
        except (json.JSONDecodeError, OSError, TypeError):
            log.exception("business_use.json unreadable — starting empty.")
            notify_data_corruption(self.context, "business_use.json")
            self._entries = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_USE_FILE, json.dumps([asdict(e) for e in self._entries], indent=2))

    def log_use(
        self, asset_id: str, hours: float, purpose: str = BUSINESS, use_date: Optional[str] = None,
        entity_id: str = "", property_id: str = "", client: str = "", note: str = "",
    ) -> UseEntry:
        if hours <= 0:
            raise ValueError("hours must be positive")
        if purpose not in (BUSINESS, PERSONAL):
            raise ValueError(f"purpose must be '{BUSINESS}' or '{PERSONAL}'")
        entry = UseEntry(
            entry_id=uuid.uuid4().hex[:10], asset_id=asset_id, date=use_date or date.today().isoformat(),
            hours=float(hours), purpose=purpose, entity_id=entity_id, property_id=property_id,
            client=client, note=note, created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._entries.append(entry)
        self._save()
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.entry_id != entry_id]
        if len(self._entries) != before:
            self._save()
            return True
        return False

    def entries_for(self, asset_id: str, year: Optional[int] = None) -> list[UseEntry]:
        return sorted(
            (e for e in self._entries if e.asset_id == asset_id and (year is None or e.date.startswith(f"{year}-"))),
            key=lambda e: e.date,
        )

    def assets_with_business_use(self) -> list[str]:
        return sorted({e.asset_id for e in self._entries if e.purpose == BUSINESS})


# ---------------------------------------------------------------------------
# The worksheet
# ---------------------------------------------------------------------------


def meter_hours_in_year(readings: list[tuple[str, float]], year: int) -> Optional[float]:
    """Pure logic. Hours the meter moved during `year`, or None without
    at least one reading in the year plus a starting point."""
    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"
    before = [v for ts, v in readings if ts < start]
    during = [v for ts, v in readings if start <= ts < end]
    if not during:
        return None
    baseline = before[-1] if before else during[0]
    moved = max(during) - baseline
    return round(moved, 2) if moved > 0 else None


@dataclass
class Worksheet:
    asset_id: str
    asset_name: str
    year: int
    business_hours: float
    personal_logged_hours: float
    total_hours: Optional[float]
    total_method: str  # "hour meter" | "logged use" | ""
    running_costs: float
    running_by_category: dict[str, float] = field(default_factory=dict)
    cost_basis: float = 0.0
    placed_in_service: str = ""
    by_business: list[tuple[str, float]] = field(default_factory=list)  # (label, business hours)
    jobs: list[UseEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def business_pct(self) -> Optional[float]:
        if not self.total_hours:
            return None
        return round(min(100.0, 100 * self.business_hours / self.total_hours), 1)

    @property
    def business_running_costs(self) -> Optional[float]:
        pct = self.business_pct
        return round(self.running_costs * pct / 100, 2) if pct is not None else None

    @property
    def business_basis(self) -> Optional[float]:
        pct = self.business_pct
        return round(self.cost_basis * pct / 100, 2) if pct is not None and self.cost_basis else None

    def business_costs_by_business(self) -> list[tuple[str, float, float]]:
        """(label, business hours, share of business running costs)."""
        total_business = self.business_running_costs
        if total_business is None or not self.business_hours:
            return []
        return [(label, hours, round(total_business * hours / self.business_hours, 2)) for label, hours in self.by_business]


def build_worksheet(context, asset, year: int) -> Worksheet:
    entries = context.business_use.entries_for(asset.asset_id, year)
    business = [e for e in entries if e.purpose == BUSINESS]
    business_hours = round(sum(e.hours for e in business), 2)
    personal_hours = round(sum(e.hours for e in entries if e.purpose == PERSONAL), 2)

    meter = None
    try:
        meter = meter_hours_in_year(hour_readings(context, asset), year)
    except AttributeError:
        pass  # no data logger wired
    notes: list[str] = []
    if meter is not None:
        total, method = max(meter, business_hours + personal_hours), "hour meter"
        if business_hours + personal_hours > meter:
            notes.append(
                f"You logged {business_hours + personal_hours:g} hours but the hour meter moved only {meter:g} this year; "
                "the logged total is used. Check the meter readings."
            )
    elif business_hours + personal_hours > 0:
        total, method = business_hours + personal_hours, "logged use"
        notes.append(
            "There are no hour-meter readings for this year, so total use is only what you logged. Logging a "
            "reading at the start and end of the year makes the percentage much easier to back up."
        )
    else:
        total, method = None, ""

    expenses = [
        e for e in context.budget.all_expenses()
        if e.asset_id == asset.asset_id and not e.asset_purchase and e.date.startswith(f"{year}-")
    ]
    by_category: dict[str, float] = defaultdict(float)
    for e in expenses:
        by_category[e.category] += e.amount
    purchases = sum(e.amount for e in context.budget.all_expenses() if e.asset_id == asset.asset_id and e.asset_purchase)
    basis = max(asset.purchase_price, purchases)

    labels: dict[str, float] = defaultdict(float)
    for e in business:
        labels[_business_label(context, e)] += e.hours

    sheet = Worksheet(
        asset_id=asset.asset_id, asset_name=asset.name, year=year,
        business_hours=business_hours, personal_logged_hours=personal_hours,
        total_hours=total, total_method=method,
        running_costs=round(sum(e.amount for e in expenses), 2),
        running_by_category={k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])},
        cost_basis=round(basis, 2), placed_in_service=asset.purchase_date,
        by_business=sorted(labels.items(), key=lambda kv: -kv[1]),
        jobs=business, notes=notes,
    )
    if not business:
        sheet.notes.append("No business use is logged for this year yet.")
    if not basis:
        sheet.notes.append("No purchase price is recorded, so there's no cost basis to split. Add it in Maintenance.")
    pct = sheet.business_pct
    if pct is not None:
        side = "more" if pct > 50 else "not more"
        sheet.notes.append(
            f"Business use is {side} than 50%. That threshold matters for some depreciation choices, so mention it "
            "to your tax preparer."
        )
    return sheet


def _business_label(context, entry: UseEntry) -> str:
    """Which business the work belongs to, for splitting costs."""
    budget = getattr(context, "budget", None)
    if entry.entity_id and budget is not None:
        entity = budget.get_business_entity(entry.entity_id)
        if entity is not None:
            return entity.name
    real_estate = getattr(context, "real_estate", None)
    if entry.property_id and real_estate is not None:
        prop = real_estate.get_property(entry.property_id)
        if prop is not None:
            if prop.entity_id and budget is not None:
                entity = budget.get_business_entity(prop.entity_id)
                if entity is not None:
                    return entity.name
            return f"Rentals ({prop.name})"
    return "Business (no entity set)"


def describe_worksheet(sheet: Worksheet) -> str:
    """Pure logic: a short spoken summary."""
    if sheet.total_hours is None:
        return f"I don't have any use logged for the {sheet.asset_name} in {sheet.year} yet."
    text = (
        f"In {sheet.year} the {sheet.asset_name} ran {sheet.total_hours:g} hours ({sheet.total_method}), "
        f"{sheet.business_hours:g} of them for business: {sheet.business_pct:g}% business use."
    )
    if sheet.business_running_costs is not None and sheet.running_costs:
        text += f" Business share of this year's running costs: ${sheet.business_running_costs:,.2f} of ${sheet.running_costs:,.2f}."
    if sheet.business_basis is not None:
        text += f" Business share of its ${sheet.cost_basis:,.2f} cost: ${sheet.business_basis:,.2f}."
    text += f" That's backed by {len(sheet.jobs)} logged business job{'s' if len(sheet.jobs) != 1 else ''}."
    return text


def build_worksheet_html(sheet: Worksheet, generated_at: str) -> str:
    """Pure logic: the printable worksheet."""
    esc = html.escape
    money = lambda v: f"${v:,.2f}"  # noqa: E731
    pct = sheet.business_pct
    rows = [
        ("Total use this year", f"{sheet.total_hours:g} hours ({sheet.total_method})" if sheet.total_hours else "Unknown"),
        ("Business use (logged)", f"{sheet.business_hours:g} hours"),
        ("Personal use", f"{(sheet.total_hours or 0) - sheet.business_hours:g} hours" if sheet.total_hours else "Unknown"),
        ("Business-use percentage", f"{pct:g}%" if pct is not None else "Unknown"),
        ("Running costs this year", money(sheet.running_costs)),
        ("Business share of running costs", money(sheet.business_running_costs) if sheet.business_running_costs is not None else "Unknown"),
        ("Cost basis (purchase price)", money(sheet.cost_basis) if sheet.cost_basis else "Not recorded"),
        ("Placed in service", sheet.placed_in_service or "Not recorded"),
        ("Business share of cost basis", money(sheet.business_basis) if sheet.business_basis is not None else "Unknown"),
    ]
    table = '<table border="1" cellspacing="0" cellpadding="4" width="100%" style="border-collapse:collapse">'
    parts = [
        f"<h2>Business use worksheet: {esc(sheet.asset_name)}, {sheet.year}</h2>",
        f"<p><i>Generated {esc(generated_at)} by MIA.</i></p>",
        table + "".join(f"<tr><td><b>{esc(k)}</b></td><td>{esc(v)}</td></tr>" for k, v in rows) + "</table>",
    ]
    if sheet.running_by_category:
        parts.append("<h3>Running costs by category</h3>" + table + "".join(
            f"<tr><td>{esc(cat)}</td><td>{money(amount)}</td></tr>" for cat, amount in sheet.running_by_category.items()
        ) + "</table>")
    split = sheet.business_costs_by_business()
    if split:
        parts.append("<h3>Business share by business</h3>" + table
                     + "<tr><th>Business</th><th>Hours</th><th>Share of running costs</th></tr>" + "".join(
            f"<tr><td>{esc(label)}</td><td>{hours:g}</td><td>{money(share)}</td></tr>" for label, hours, share in split
        ) + "</table>")
    if sheet.jobs:
        parts.append("<h3>Business use log</h3>" + table
                     + "<tr><th>Date</th><th>Hours</th><th>For</th><th>Note</th></tr>" + "".join(
            f"<tr><td>{esc(e.date)}</td><td>{e.hours:g}</td><td>{esc(e.client)}</td><td>{esc(e.note)}</td></tr>" for e in sheet.jobs
        ) + "</table>")
    if sheet.notes:
        parts.append("<h3>Notes</h3><ul>" + "".join(f"<li>{esc(n)}</li>" for n in sheet.notes) + "</ul>")
    parts.append(f"<p><i>{esc(DISCLAIMER)}</i></p>")
    return "\n".join(parts)
