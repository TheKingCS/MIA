"""
core.obligations
==================

Tax and compliance obligations (DEC-0040; the Business OS spec's first
increment, docs/BUSINESS_OS_AUDIT.md): every filing, payment, permit,
licence, registration, inspection and renewal the household has to keep,
in one list with one calendar.

- **An obligation** says who it's owed to (authority, jurisdiction), what
  for (the entity or activity), the period, when it's due (to file, and
  to pay when that's different), what it costs, what documents it needs,
  the next action, and where its rule came from: the official source, the
  day it was last checked, and whether it's **verified**. An unverified
  one is a task to check, and is always shown as one: MIA never presents
  a guessed permit, fee or date as confirmed law.
- **Deadlines** move to the next business day when they fall on a weekend
  or a federal holiday (the IRS rule, and the usual state one), when the
  obligation says so; that's worked out here, never typed in. An
  extension to file is kept apart from the payment date: it never moves
  the day the money is due.
- **Reminders** at 90, 60, 30, 14 and 7 days, on the day, and every week
  while overdue (each obligation can have its own list), through the
  communication gate, each once.
- **Repeating ones** (quarterly estimates, a yearly licence) make the next
  one when this one is done.
- **Starters**: a list of obligations commonly worth checking, offered as
  *to verify*, each with the official place to check. Never applied
  without the person, never marked verified.

A household store, written through atomic_write_text so every change can
be undone. Pure functions below have no I/O.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "obligations.json"

KINDS = ("tax filing", "tax payment", "permit", "licence", "registration", "inspection", "annual report", "renewal",
         "insurance", "other")
JURISDICTIONS = ("federal", "state", "county", "city", "other")
# Where it stands. "overdue" and "upcoming" are worked out from the dates, never stored.
STATUSES = ("to verify", "applies", "ready to file", "submitted", "payment due", "paid", "extended", "done",
            "needs a professional", "not applicable")
CLOSED = ("done", "paid", "not applicable")
RECURRENCES = ("", "monthly", "quarterly", "yearly")
DEFAULT_REMINDERS = (90, 60, 30, 14, 7, 0)
OVERDUE_EVERY_DAYS = 7


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Obligation:
    obligation_id: str
    title: str
    kind: str = "other"
    authority: str = ""  # who it's owed to: "IRS", "Kentucky Department of Revenue", the county clerk
    jurisdiction: str = "other"
    applies_to: str = ""  # the entity or activity, in the person's words, or an entity id
    period: str = ""  # "2026 Q3", "tax year 2026"
    due_date: str = ""  # to file / to renew, YYYY-MM-DD, as the rule states it
    pay_date: str = ""  # when the money is due, if different
    extended_to: str = ""  # a verified extension to file (never moves pay_date)
    business_days: bool = True  # move a weekend/holiday due date to the next business day
    status: str = "to verify"
    recurrence: str = ""
    fee: float = 0.0
    estimate: float = 0.0  # the amount expected to be owed, when known
    documents: str = ""
    next_action: str = ""
    source_url: str = ""  # the official source
    source_title: str = ""
    rule: str = ""  # the statute, form or guidance, in words
    verified_on: str = ""  # YYYY-MM-DD, when someone last checked the source
    reverify_days: int = 365
    reminders: list = field(default_factory=lambda: list(DEFAULT_REMINDERS))
    proof: str = ""  # a confirmation number, a file in the inbox
    notes: str = ""
    starter_id: str = ""  # which starter it came from, if one
    created_at: str = ""
    closed_at: str = ""


# ---------------------------------------------------------------- dates (pure)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(day: date) -> date:
    return day - timedelta(days=1) if day.weekday() == 5 else day + timedelta(days=1) if day.weekday() == 6 else day


def federal_holidays(year: int, dc: bool = True) -> set[date]:
    """Pure logic. US federal holidays (as observed) in `year`; with `dc`,
    Washington DC's Emancipation Day too, which moves IRS deadlines."""
    days = {
        _observed(date(year, 1, 1)), _nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3),
        _last_weekday(year, 5, 0), _observed(date(year, 6, 19)), _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1), _nth_weekday(year, 10, 0, 2), _observed(date(year, 11, 11)),
        _nth_weekday(year, 11, 3, 4), _observed(date(year, 12, 25)),
    }
    if _observed(date(year + 1, 1, 1)).year == year:  # Jan 1 on a Saturday is observed Dec 31
        days.add(_observed(date(year + 1, 1, 1)))
    if dc:
        days.add(_observed(date(year, 4, 16)))
    return days


def business_day(day: date, dc: bool = True) -> date:
    """Pure logic. `day`, or the next day that's neither a weekend nor a federal holiday."""
    while day.weekday() >= 5 or day in federal_holidays(day.year, dc):
        day += timedelta(days=1)
    return day


def _day(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def effective_dates(o: Obligation) -> dict:
    """Pure logic. When it's really due: to file (an extension if there is
    one), and to pay (never moved by an extension to file), each moved to
    a business day when the obligation says so; and whether it moved."""
    def adjust(text: str) -> tuple[Optional[date], bool]:
        stated = _day(text)
        if stated is None:
            return None, False
        moved = business_day(stated) if o.business_days else stated
        return moved, moved != stated

    payment_only = o.kind == "tax payment"
    file_on, file_moved = (None, False) if payment_only else adjust(o.extended_to or o.due_date)
    if o.pay_date:
        pay_on, pay_moved = adjust(o.pay_date)
    elif payment_only or o.extended_to:  # an extension to file: the money's still due on the original day
        pay_on, pay_moved = adjust(o.due_date)
    else:
        pay_on, pay_moved = None, False
    return {"file": file_on, "file_moved": file_moved, "pay": pay_on, "pay_moved": pay_moved}


def next_due(o: Obligation) -> Optional[date]:
    """Pure logic. The earliest day something is owed."""
    days = [d for d in (effective_dates(o)["file"], effective_dates(o)["pay"]) if d is not None]
    return min(days) if days else None


def state(o: Obligation, today: date) -> dict:
    """Pure logic. Where it stands today: closed, overdue, upcoming (within
    30 days), later, or undated; days left; whether its source is due for
    another check."""
    due = next_due(o)
    days = (due - today).days if due else None
    if o.status in CLOSED:
        where = "closed"
    elif due is None:
        where = "undated"
    elif days < 0:
        where = "overdue"
    elif days <= 30:
        where = "upcoming"
    else:
        where = "later"
    checked = _day(o.verified_on)
    stale = bool(checked and (today - checked).days > max(1, int(o.reverify_days or 365)))
    return {"where": where, "due": due.isoformat() if due else "", "days": days,
            "verified": bool(checked) and o.status != "to verify", "stale": stale}


def reminder_due(o: Obligation, today: date) -> Optional[tuple[str, str]]:
    """Pure logic. The reminder for today, if one is due: (fingerprint,
    which). On a reminder day (days left in its list), and weekly while
    overdue. Closed obligations never remind."""
    if o.status in CLOSED:
        return None
    due = next_due(o)
    if due is None:
        return None
    days = (due - today).days
    if days < 0:
        if -days % OVERDUE_EVERY_DAYS == 1:  # the day after, then weekly
            return f"obligation|{o.obligation_id}|{due.isoformat()}|overdue|{-days // OVERDUE_EVERY_DAYS}", "overdue"
        return None
    if days in [int(x) for x in (o.reminders or DEFAULT_REMINDERS)]:
        return f"obligation|{o.obligation_id}|{due.isoformat()}|{days}", "today" if days == 0 else f"{days} days"
    return None


def next_period(o: Obligation) -> Optional[dict]:
    """Pure logic. The dates of the next one, for a repeating obligation."""
    step = {"monthly": 1, "quarterly": 3, "yearly": 12}.get(o.recurrence)
    if not step:
        return None

    def shift(text: str) -> str:
        d = _day(text)
        if d is None:
            return ""
        month = d.month - 1 + step
        year, month = d.year + month // 12, month % 12 + 1
        last = ((date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)).day
        return date(year, month, min(d.day, last)).isoformat()

    return {"due_date": shift(o.due_date), "pay_date": shift(o.pay_date)}


# ---------------------------------------------------------------- starters (to verify, never confirmed)

IRS_ES = "https://www.irs.gov/forms-pubs/about-form-1040-es"
STARTERS: tuple[dict, ...] = (
    {"id": "fed_1040", "title": "Federal income tax return (Form 1040)", "kind": "tax filing", "jurisdiction": "federal",
     "authority": "IRS", "month_day": (4, 15), "recurrence": "yearly", "source_url": "https://www.irs.gov/filing",
     "source_title": "IRS: Filing", "next_action": "Check the due date for this tax year and whether you file jointly.",
     "documents": "W-2s, 1099s, the Business Report, rental income and expenses, mileage"},
    *({"id": f"fed_es_q{q}", "title": f"Federal estimated tax, payment {q} (Form 1040-ES)", "kind": "tax payment",
       "jurisdiction": "federal", "authority": "IRS", "month_day": md, "recurrence": "yearly", "source_url": IRS_ES,
       "source_title": "IRS: About Form 1040-ES",
       "next_action": "Check whether you need estimated payments (self-employment, rental or farm income "
                      "not covered by withholding), and the amount."}
      for q, md in ((1, (4, 15)), (2, (6, 15)), (3, (9, 15)), (4, (1, 15)))),
    {"id": "fed_1099_nec", "title": "1099-NEC to contractors you paid", "kind": "tax filing", "jurisdiction": "federal",
     "authority": "IRS", "month_day": (1, 31), "recurrence": "yearly",
     "source_url": "https://www.irs.gov/forms-pubs/about-form-1099-nec", "source_title": "IRS: About Form 1099-NEC",
     "next_action": "Only if a business paid a contractor over the threshold: the Business Report lists them."},
    {"id": "state_income", "title": "State income tax return", "kind": "tax filing", "jurisdiction": "state",
     "authority": "Your state's revenue department", "month_day": (4, 15), "recurrence": "yearly", "state": "",
     "next_action": "Check your state's form and due date."},
    {"id": "ky_740", "title": "Kentucky individual income tax return (Form 740)", "kind": "tax filing",
     "jurisdiction": "state", "authority": "Kentucky Department of Revenue", "month_day": (4, 15), "recurrence": "yearly",
     "state": "KY", "source_url": "https://revenue.ky.gov", "source_title": "Kentucky Department of Revenue",
     "next_action": "Check the due date for this tax year."},
    {"id": "ky_sales_tax", "title": "Kentucky sales and use tax: registration and returns", "kind": "registration",
     "jurisdiction": "state", "authority": "Kentucky Department of Revenue", "state": "KY",
     "source_url": "https://revenue.ky.gov", "source_title": "Kentucky Department of Revenue",
     "next_action": "Check whether what you sell (baked goods, honey, eggs, produce, wood goods) is taxable, whether "
                    "you must register, and how often you'd file (the state assigns it)."},
    {"id": "ky_home_processor", "title": "Kentucky home-based processor registration", "kind": "registration",
     "jurisdiction": "state", "authority": "Kentucky Department for Public Health, Food Safety Branch", "state": "KY",
     "source_url": "https://www.chfs.ky.gov", "source_title": "Kentucky Cabinet for Health and Family Services",
     "next_action": "Search their site for \"home-based processor\": registration, fee, renewal, label rules."},
    {"id": "ky_eggs", "title": "Selling eggs: Kentucky's rules", "kind": "registration", "jurisdiction": "state",
     "authority": "Kentucky Department of Agriculture", "state": "KY", "source_url": "https://www.kyagr.com",
     "source_title": "Kentucky Department of Agriculture",
     "next_action": "Check egg sales rules for a small flock: registration or licence, cartons, labels, storage temperature."},
    {"id": "ky_annual_report", "title": "Kentucky LLC annual report", "kind": "annual report", "jurisdiction": "state",
     "authority": "Kentucky Secretary of State", "month_day": (6, 30), "recurrence": "yearly", "state": "KY",
     "source_url": "https://www.sos.ky.gov", "source_title": "Kentucky Secretary of State",
     "next_action": "Only for an LLC or corporation registered in Kentucky: check the filing window and fee."},
    {"id": "local_occupational", "title": "Local occupational licence tax", "kind": "licence", "jurisdiction": "county",
     "authority": "Your county's or city's occupational tax office",
     "next_action": "Ask your county and city (from the property's real address) whether a business or rental there "
                    "owes an occupational licence tax, and when."},
    {"id": "property_tax", "title": "Property tax", "kind": "tax payment", "jurisdiction": "county",
     "authority": "Your county", "recurrence": "yearly",
     "next_action": "Check each property's bill date, discount date and due date with the county."},
    {"id": "rental_registration", "title": "Rental registration or landlord licence", "kind": "registration",
     "jurisdiction": "city", "authority": "Your city or county",
     "next_action": "Ask the city and county where each rental is whether rentals must be registered or inspected."},
)
STARTERS_BY_ID = {s["id"]: s for s in STARTERS}


def starter_fields(starter_id: str, year: int) -> dict:
    """The obligation for a starter, to verify: its next due date in or
    after `year` when it has one."""
    s = STARTERS_BY_ID[starter_id]
    out = {k: s[k] for k in ("title", "kind", "jurisdiction", "authority", "next_action") if k in s}
    for k in ("source_url", "source_title", "documents", "recurrence"):
        if s.get(k):
            out[k] = s[k]
    if s.get("month_day"):
        month, day_ = s["month_day"]
        out["due_date"] = date(year, month, day_).isoformat()
    out.update(status="to verify", starter_id=starter_id)
    return out


def starter_list(state_code: str = "") -> list[dict]:
    """Starters for a picker: federal ones, the person's state's (or the
    general state one when there's no list for it), and local ones; with no
    state set (`region.state`), all of them."""
    code = state_code.upper()
    have_state = any(s.get("state") == code for s in STARTERS) if code else False
    out = []
    for s in STARTERS:
        st = s.get("state")
        if not code or st is None or (have_state and st == code) or (not have_state and st == ""):
            out.append({"id": s["id"], "name": s["title"], "jurisdiction": s["jurisdiction"]})
    return out


# ---------------------------------------------------------------- the store


class ObligationBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        self.obligations: list[Obligation] = []
        self.noted: list[str] = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            known = Obligation.__dataclass_fields__
            self.obligations = [Obligation(**{k: v for k, v in d.items() if k in known}) for d in raw.get("obligations", [])]
            self.noted = [str(x) for x in raw.get("noted", [])][-500:]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("obligations.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"obligations": [asdict(o) for o in self.obligations],
                                                  "noted": self.noted[-500:]}, indent=2))

    def get(self, obligation_id: str) -> Optional[Obligation]:
        return next((o for o in self.obligations if o.obligation_id == obligation_id), None)

    def add(self, title: str, **fields) -> Obligation:
        if not str(title or "").strip():
            raise ValueError("What's the obligation called?")
        o = Obligation(obligation_id=uuid.uuid4().hex[:10], title=title.strip(), created_at=_now())
        self._apply(o, fields)
        self.obligations.append(o)
        self._save()
        return o

    def update(self, obligation_id: str, **fields) -> Obligation:
        o = self.get(obligation_id)
        if o is None:
            raise ValueError("That obligation isn't there anymore.")
        self._apply(o, fields)
        if o.status in CLOSED and not o.closed_at:
            o.closed_at = _now()
        elif o.status not in CLOSED:
            o.closed_at = ""
        self._save()
        return o

    def delete(self, obligation_id: str) -> None:
        self.obligations = [o for o in self.obligations if o.obligation_id != obligation_id]
        self._save()

    @staticmethod
    def _apply(o: Obligation, fields: dict) -> None:
        for name, value in fields.items():
            if name in ("obligation_id", "created_at") or not hasattr(o, name):
                raise ValueError(f"An obligation has no '{name}'.")
            if name == "kind" and value not in KINDS:
                raise ValueError(f"Kind: one of {', '.join(KINDS)}.")
            if name == "jurisdiction" and value not in JURISDICTIONS:
                raise ValueError(f"Jurisdiction: one of {', '.join(JURISDICTIONS)}.")
            if name == "status" and value not in STATUSES:
                raise ValueError(f"Status: one of {', '.join(STATUSES)}.")
            if name == "recurrence" and value not in RECURRENCES:
                raise ValueError("Repeats: monthly, quarterly, yearly or not.")
            if name in ("due_date", "pay_date", "extended_to", "verified_on") and value and _day(value) is None:
                raise ValueError("Dates look like 2026-10-21.")
            if name in ("fee", "estimate"):
                value = max(0.0, float(value or 0))
            if name == "reverify_days":
                value = max(1, int(float(value or 365)))
            if name == "business_days":
                value = str(value).lower() not in ("0", "false", "no", "off")
            if name == "reminders":
                value = sorted({max(0, int(x)) for x in (value if isinstance(value, (list, tuple)) else
                                                          str(value).replace(",", " ").split())}, reverse=True)
            setattr(o, name, value if value is not None else "")

    def note_given(self, fingerprint: str) -> bool:
        """Remember a reminder; False if it was already given."""
        if fingerprint in self.noted:
            return False
        self.noted.append(fingerprint)
        self._save()
        return True


def reminder_notes(context, today: date) -> list[tuple[str, str, str, str]]:
    """(title, message, fingerprint, urgency) for every reminder due today."""
    from core.communication_gate import AMBIENT, TIMELY, URGENT
    from core.region import money

    book = getattr(context, "obligations", None)
    if book is None:
        return []
    out = []
    for o in book.obligations:
        hit = reminder_due(o, today)
        if hit is None:
            continue
        fingerprint, which = hit
        st = state(o, today)
        unverified = "" if st["verified"] else " (not verified yet: check the source first)"
        fee = f" Fee about {money(o.fee)}." if o.fee else ""
        step = f" Next: {o.next_action}" if o.next_action else ""
        if which == "overdue":
            title, urgency = f"⚠ Overdue: {o.title}", URGENT
            message = f"It was due {st['due']}{unverified}.{fee}{step}"
        elif which == "today":
            title, urgency = f"📌 Due today: {o.title}", URGENT
            message = f"{o.authority + ': ' if o.authority else ''}due today{unverified}.{fee}{step}"
        else:
            days = int(which.split()[0])
            title = f"📅 {o.title}: {which}"
            urgency = TIMELY if days <= 14 else AMBIENT
            message = f"Due {st['due']}{unverified}.{fee}{step}"
        out.append((title, message, fingerprint, urgency))
    return out
