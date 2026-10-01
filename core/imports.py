"""
core.imports
==============

Bring your life with you (2026-10-01): a new person shouldn't start from
an empty MIA. Three common exports from other apps:

- **Calendar** (.ics, from Google Calendar, Outlook, Apple Calendar):
  events with their date, time, notes and repeat (weekly, every two
  weeks, monthly, yearly; any other repeat comes in as one event).
- **Contacts** (.vcf, from phones and Google/Outlook contacts): People &
  Pets, with email and birthday.
- **Bank statement** (.csv, "download transactions" on most bank
  websites): expenses and income, with a category guessed from the
  description (a guess: change it any time).

Re-importing the same file adds nothing twice. Each import can be undone
with "undo that" (core/undo_log.py): it's recorded as one change.

The parsers are pure logic (tested against real-world shapes); `run()`
applies one to the person's stores.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

CALENDAR, CONTACTS, BANK = "calendar", "contacts", "bank"


@dataclass
class Summary:
    kind: str
    added: int = 0
    skipped: int = 0  # already in MIA
    problems: list[str] = field(default_factory=list)

    def describe(self) -> str:
        noun = {CALENDAR: "event", CONTACTS: "person", BANK: "transaction"}[self.kind]
        plural = {CALENDAR: "events", CONTACTS: "people", BANK: "transactions"}[self.kind]
        text = f"Imported {self.added} {noun if self.added == 1 else plural}"
        if self.skipped:
            text += f"; {self.skipped} were already in MIA"
        if self.problems:
            text += f"; {len(self.problems)} couldn't be read"
        return text + "."


# ------------------------------------------------------------------ shared


def _unfold(text: str) -> list[str]:
    """RFC 5545/6350: a line starting with a space or tab continues the last."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        elif raw.strip():
            lines.append(raw)
    return lines


def _split(line: str) -> tuple[str, dict, str]:
    """'DTSTART;TZID=X;VALUE=DATE:2026...' -> ('DTSTART', {'TZID': 'X', ...}, '2026...')."""
    head, _, value = line.partition(":")
    name, *params = head.split(";")
    parsed = {}
    for param in params:
        key, _, val = param.partition("=")
        parsed[key.upper()] = val.strip('"')
    return name.upper(), parsed, value


def _unescape(value: str) -> str:
    return (value.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";")
            .replace("\\\\", "\\")).strip()


# ------------------------------------------------------------------ calendar


@dataclass
class ImportedEvent:
    title: str
    date: str  # ISO
    time: Optional[str] = None  # HH:MM, local
    notes: str = ""
    recurrence: Optional[str] = None


_FREQ = {"WEEKLY": "weekly", "MONTHLY": "monthly", "YEARLY": "yearly"}


def _ics_when(value: str, params: dict) -> tuple[Optional[str], Optional[str]]:
    value = value.strip()
    try:
        if params.get("VALUE") == "DATE" or len(value) == 8:
            return datetime.strptime(value[:8], "%Y%m%d").date().isoformat(), None
        moment = datetime.strptime(value.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
        if value.endswith("Z"):  # UTC: shown in this computer's own time
            moment = moment.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
        return moment.date().isoformat(), moment.strftime("%H:%M")
    except ValueError:
        return None, None


def parse_ics(text: str) -> tuple[list[ImportedEvent], list[str]]:
    """Pure logic. Events, and what couldn't be read."""
    events, problems = [], []
    current: Optional[dict] = None
    for line in _unfold(text):
        name, params, value = _split(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            current = {}
        elif name == "END" and value.upper() == "VEVENT" and current is not None:
            title = current.get("title") or "(no title)"
            if current.get("date"):
                events.append(ImportedEvent(title, current["date"], current.get("time"), current.get("notes", ""),
                                            current.get("recurrence")))
            else:
                problems.append(title)
            current = None
        elif current is not None:
            if name == "SUMMARY":
                current["title"] = _unescape(value)
            elif name == "DTSTART":
                current["date"], current["time"] = _ics_when(value, params)
            elif name == "DESCRIPTION":
                current["notes"] = _unescape(value)
            elif name == "LOCATION" and value.strip():
                current["notes"] = (current.get("notes", "") + f"\nWhere: {_unescape(value)}").strip()
            elif name == "RRULE":
                rule = dict(part.split("=", 1) for part in value.split(";") if "=" in part)
                freq, interval = rule.get("FREQ", ""), rule.get("INTERVAL", "1")
                if freq == "WEEKLY" and interval == "2":
                    current["recurrence"] = "biweekly"
                elif interval == "1":
                    current["recurrence"] = _FREQ.get(freq)
    return events, problems


# ------------------------------------------------------------------ contacts


@dataclass
class ImportedPerson:
    name: str
    email: str = ""
    birthday: str = ""  # ISO, or "" (a birthday without a year is kept as a note)
    notes: str = ""


def parse_vcards(text: str) -> tuple[list[ImportedPerson], list[str]]:
    """Pure logic. People, and what couldn't be read."""
    people, problems = [], []
    card: Optional[dict] = None
    for line in _unfold(text):
        name, params, value = _split(line)
        name = name.split(".")[-1]  # "item1.EMAIL" (Apple) -> "EMAIL"
        if name == "BEGIN" and value.upper() == "VCARD":
            card = {"notes": []}
        elif name == "END" and value.upper() == "VCARD" and card is not None:
            full = card.get("fn") or card.get("n") or card.get("org")
            if full:
                people.append(ImportedPerson(full, card.get("email", ""), card.get("bday", ""), "\n".join(card["notes"])))
            else:
                problems.append("a contact without a name")
            card = None
        elif card is not None:
            if name == "FN":
                card["fn"] = _unescape(value)
            elif name == "N" and value.strip(";"):
                last, first, *_ = (value.split(";") + ["", ""])[:3]
                card["n"] = f"{_unescape(first)} {_unescape(last)}".strip()
            elif name == "ORG" and value.strip(";"):
                card["org"] = _unescape(value.split(";")[0])
            elif name == "EMAIL" and "email" not in card:
                card["email"] = value.strip().lower()
            elif name == "TEL":
                card["notes"].append(f"Phone: {value.strip()}")
            elif name == "BDAY":
                digits = value.strip().replace("-", "")
                if re.fullmatch(r"\d{8}", digits):
                    card["bday"] = f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
                elif re.fullmatch(r"--\d{4}|--\d{2}-\d{2}", value.strip()):
                    card["notes"].append(f"Birthday: {value.strip().lstrip('-')} (no year)")
            elif name == "NOTE":
                card["notes"].append(_unescape(value))
    return people, problems


# ------------------------------------------------------------------ bank statements


@dataclass
class ImportedTransaction:
    date: str  # ISO
    description: str
    amount: float  # money out is positive here; see `is_income`
    is_income: bool
    category: str


_DATE_HEADERS = ("date", "transaction date", "posted date", "posting date", "trans. date", "booking date")
_DESC_HEADERS = ("description", "payee", "merchant", "name", "memo", "details", "transaction", "narrative")
_AMOUNT_HEADERS = ("amount", "transaction amount", "value")
_DEBIT_HEADERS = ("debit", "withdrawal", "withdrawals", "money out", "paid out", "debit amount")
_CREDIT_HEADERS = ("credit", "deposit", "deposits", "money in", "paid in", "credit amount")

# A guess from the description; the person can change any of them.
_CATEGORY_WORDS = (
    ("Groceries", ("grocery", "kroger", "walmart", "aldi", "safeway", "publix", "costco", "tesco", "sainsbury",
                   "whole foods", "trader joe", "food lion", "h-e-b", "heb ", "market")),
    ("Transportation", ("shell", "exxon", "chevron", "bp ", "fuel", "gas station", "uber", "lyft", "parking", "toll")),
    ("Utilities", ("electric", "energy", "water", "power", "internet", "comcast", "xfinity", "verizon", "at&t",
                   "t-mobile", "spectrum", "utility")),
    ("Mortgage/Rent", ("rent", "mortgage")),
    ("Insurance", ("insurance", "geico", "progressive", "state farm", "allstate")),
    ("Medical", ("pharmacy", "cvs", "walgreens", "doctor", "dental", "clinic", "hospital", "medical")),
    ("Entertainment", ("netflix", "spotify", "hulu", "disney", "cinema", "theater", "steam", "xbox", "playstation")),
    ("Building Materials", ("home depot", "lowe's", "lowes", "menards", "lumber", "hardware")),
    ("Shopping", ("amazon", "target", "ebay", "etsy", "best buy")),
    ("Bank Fees", ("fee", "overdraft", "interest charge")),
    ("Travel", ("airline", "hotel", "airbnb", "delta", "united", "southwest", "expedia")),
)


def guess_category(description: str) -> str:
    """Pure logic."""
    lowered = f" {description.lower()} "
    for category, words in _CATEGORY_WORDS:
        if any(word in lowered for word in words):
            return category
    return "Other"


def _amount(text: str) -> Optional[float]:
    cleaned = (text or "").strip().replace(",", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -abs(value) if negative else value


def _bank_date(text: str, day_first: bool) -> Optional[str]:
    text = (text or "").strip()[:10]
    formats = ["%Y-%m-%d", "%Y/%m/%d"] + (["%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"] if day_first
                                          else ["%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y"])
    formats += ["%d.%m.%Y", "%d-%m-%Y", "%m-%d-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _column(headers: list[str], names: tuple[str, ...]) -> Optional[int]:
    lowered = [h.strip().lower() for h in headers]
    for name in names:
        if name in lowered:
            return lowered.index(name)
    for i, header in enumerate(lowered):
        if any(header.startswith(name) for name in names):
            return i
    return None


def parse_bank_csv(text: str, day_first: bool = False) -> tuple[list[ImportedTransaction], list[str]]:
    """Pure logic. Transactions, and rows that couldn't be read. `day_first`:
    31/12/2026-style dates (anywhere but the US)."""
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    header_at = next((i for i, row in enumerate(rows[:15])
                      if _column(row, _DATE_HEADERS) is not None and
                      (_column(row, _AMOUNT_HEADERS) is not None or _column(row, _DEBIT_HEADERS) is not None)), None)
    if header_at is None:
        return [], ["no Date and Amount columns found"]
    headers = rows[header_at]
    date_col, desc_col = _column(headers, _DATE_HEADERS), _column(headers, _DESC_HEADERS)
    amount_col = _column(headers, _AMOUNT_HEADERS)
    debit_col, credit_col = _column(headers, _DEBIT_HEADERS), _column(headers, _CREDIT_HEADERS)
    found, problems = [], []
    for row in rows[header_at + 1:]:
        if not any(cell.strip() for cell in row):
            continue
        cell = lambda col: row[col] if col is not None and col < len(row) else ""  # noqa: E731
        when = _bank_date(cell(date_col), day_first)
        description = cell(desc_col).strip() or "(no description)"
        if amount_col is not None and cell(amount_col).strip():
            value = _amount(cell(amount_col))
        else:
            out, into = _amount(cell(debit_col)), _amount(cell(credit_col))
            value = (abs(into) if into else None) if not out else -abs(out)
        if when is None or value is None or value == 0:
            problems.append(", ".join(row)[:60])
            continue
        is_income = value > 0
        found.append(ImportedTransaction(when, description, abs(value), is_income,
                                         "Other" if is_income else guess_category(description)))
    return found, problems


# ------------------------------------------------------------------ applying


def kind_of(path: Path, text: str) -> Optional[str]:
    """Pure logic. Which importer a file needs."""
    suffix = Path(path).suffix.lower()
    head = text.lstrip("﻿")[:200].upper()
    if suffix == ".ics" or "BEGIN:VCALENDAR" in head:
        return CALENDAR
    if suffix in (".vcf", ".vcard") or "BEGIN:VCARD" in head:
        return CONTACTS
    if suffix == ".csv":
        return BANK
    return None


def import_calendar(context, text: str) -> Summary:
    events, problems = parse_ics(text)
    summary = Summary(CALENDAR, problems=problems)
    existing = {(e.title.strip().lower(), e.date) for e in context.calendar.all_events()}
    for event in events:
        key = (event.title.strip().lower(), event.date)
        if key in existing:
            summary.skipped += 1
            continue
        context.calendar.add_event(title=event.title, date=event.date, time=event.time, notes=event.notes,
                                   recurrence=event.recurrence)
        existing.add(key)
        summary.added += 1
    return summary


def import_contacts(context, text: str) -> Summary:
    people, problems = parse_vcards(text)
    summary = Summary(CONTACTS, problems=problems)
    relationships = context.relationships
    by_name = {p.name.strip().lower(): p for p in relationships.all_people()}
    for person in people:
        known = by_name.get(person.name.strip().lower())
        if known is not None:
            missing = {k: v for k, v in (("email", person.email), ("birthday", person.birthday)) if v and not getattr(known, k)}
            if missing:
                relationships.update_person(known.person_id, **missing)
            summary.skipped += 1
            continue
        added = relationships.add_person(name=person.name, birthday=person.birthday, notes=person.notes,
                                         email=person.email)
        by_name[person.name.strip().lower()] = added
        summary.added += 1
    return summary


def import_bank(context, text: str, day_first: bool = False) -> Summary:
    transactions, problems = parse_bank_csv(text, day_first)
    summary = Summary(BANK, problems=problems)
    budget = context.budget
    seen = {(e.date, round(e.amount, 2), e.description.strip().lower()) for e in budget.all_expenses()}
    seen |= {(i.date, round(i.amount, 2), i.description.strip().lower()) for i in budget.all_income()}
    for t in transactions:
        key = (t.date, round(t.amount, 2), t.description.strip().lower())
        if key in seen:
            summary.skipped += 1
            continue
        if t.is_income:
            budget.add_income(amount=t.amount, category=t.category, description=t.description, date=t.date,
                              tax_relevant=False)
        else:
            budget.add_expense(amount=t.amount, category=t.category, description=t.description, date=t.date,
                               notes="Imported from a bank statement")
        seen.add(key)
        summary.added += 1
    return summary


def run(context, path: Path) -> Summary:
    """Import one file into the signed-in person's MIA, as one undoable
    change. Raises ValueError for a file MIA can't import."""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    kind = kind_of(path, text)
    if kind is None:
        raise ValueError("MIA can import calendar files (.ics), contacts (.vcf) and bank statements (.csv).")
    from core.person_settings import person_id
    from core.region import country_of
    from core.undo_log import recording

    with recording(f"import_{kind}", person_id(context)) as change:
        if kind == CALENDAR:
            summary = import_calendar(context, text)
        elif kind == CONTACTS:
            summary = import_contacts(context, text)
        else:
            summary = import_bank(context, text, day_first=country_of(context) != "US")
    undo = getattr(context, "undo", None)
    if undo is not None:
        undo.add(change)
    from core.main_thread import publish

    publish(context, "records.changed", action=f"import_{kind}")
    log.info("Imported %s from %s: %s", kind, path.name, summary.describe())
    return summary
