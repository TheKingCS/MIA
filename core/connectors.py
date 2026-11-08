"""
core.connectors
=================

Bringing data in from other apps (Zac, 2026-11-08: "make MIA able to connect to any app with relevant data and be able
to import data upon user request and approval"; the audit and plan: https://claude.ai/artifact/H8gYSX2rvneRMp5mgA4qFa).
Every source works the same way: the person asks, MIA reads it (read-only, never writing back), shows a preview (what's
new, what's already in MIA, what she couldn't read), and only an approved import lands, as one change "undo that" takes
back. This file is the one place that knows the sources; `CONNECTORS` lists them for the Connect Apps page.

Two kinds so far, neither needing a sign-in:

- **A file** (`file`): a calendar (.ics), contacts (.vcf) or a bank statement (.csv), the same parsers and duplicate
  rules as core/imports.py (until now only in the PC app's Settings);
- **A rental calendar link** (`rental_calendar`): the private calendar link Airbnb, VRBO, Hostaway and others give
  each listing. Each booked stay becomes a check-in and a check-out in the Calendar, for the property named. Only
  the dates come in: the link's notes (Airbnb's carry the reservation link and the last digits of the guest's
  phone) never do, and blocked days aren't stays. The link is a key (anyone holding it sees the bookings), so it's
  used for this import and not kept.

A link is fetched only over https from a public address (never this computer or the home network: `fetch_link`), at
most MAX_BYTES, with a timeout. Changes are the action kinds `connect.file` and `connect.rental_calendar`.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from core.logger import get_logger

log = get_logger(__name__)

MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 15
_BLOCKED = ("not available", "blocked", "unavailable", "closed", "owner block", "owner stay")


@dataclass(frozen=True)
class Connector:
    """One source MIA can import from: its id, its name, how its data is reached, and where it lands."""
    connector_id: str
    name: str
    how: str
    lands: str
    examples: tuple = ()


CONNECTORS = (
    Connector("file", "A file from another app", "Choose the file you downloaded",
              "Calendar, People & Pets, or Money", ("Google Calendar or Outlook (.ics)", "phone or Google contacts (.vcf)",
                                                    "your bank's \"download transactions\" (.csv)")),
    Connector("rental_calendar", "A rental's calendar link", "Paste the listing's private calendar link (.ics)",
              "Calendar: a check-in and a check-out for each booked stay", ("Airbnb", "VRBO", "Hostaway", "OwnerRez")),
)


# ------------------------------------------------------------------ fetching a link


class LinkError(ValueError):
    """A link MIA won't or can't read, said plainly."""


def _public(host: str) -> bool:
    """Whether every address a host name points to is on the public internet (not this computer, the home network,
    a link-local or reserved range)."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise LinkError("MIA couldn't find that address. Check the link.") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            return False
    return True


def clean_link(url: str) -> str:
    """Pure logic. The link as MIA will fetch it: trimmed, webcal:// read as https://; raises LinkError for anything but
    an https link to a named host."""
    url = (url or "").strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    parts = urlparse(url)
    if parts.scheme.lower() != "https" or not parts.hostname:
        raise LinkError("Use the calendar's https link (it starts with https:// or webcal://).")
    return url


def fetch_link(url: str) -> str:
    """The text at a calendar link: https only, a public address only (never this computer or the home network), at
    most MAX_BYTES, within TIMEOUT seconds; raises LinkError, said plainly, when it can't."""
    url = clean_link(url)
    host = urlparse(url).hostname or ""
    if not _public(host):
        raise LinkError("MIA only reads calendar links on the internet, not addresses on this computer or network.")

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        """Refuses redirects, so a link can't be bounced to a private address."""

        def redirect_request(self, *args, **kwargs):
            """Never follow one."""
            raise LinkError("That link redirects somewhere else. Copy the calendar link itself.")

    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "MIA calendar import"})
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            data = response.read(MAX_BYTES + 1)
    except LinkError:
        raise
    except Exception as problem:  # network, HTTP error, timeout
        raise LinkError(f"MIA couldn't read that link ({type(problem).__name__}).") from None
    if len(data) > MAX_BYTES:
        raise LinkError("That calendar is too large to import.")
    return data.decode("utf-8-sig", errors="replace")


# ------------------------------------------------------------------ rental calendars


@dataclass
class Stay:
    """One booked stay from a rental calendar: check-in and check-out dates (ISO)."""
    check_in: str
    check_out: str

    @property
    def nights(self) -> int:
        """Nights booked (0 when the dates don't read)."""
        try:
            return max(0, (date.fromisoformat(self.check_out) - date.fromisoformat(self.check_in)).days)
        except ValueError:
            return 0


def parse_stays(text: str) -> tuple[list[Stay], int]:
    """Pure logic. The booked stays in a rental calendar (.ics) and how many blocked spans were left out. Only the
    dates are read: a stay's summary decides only whether it's a booking, and its notes are never kept."""
    from core.imports import _ics_when, _split, _unfold

    stays, blocked = [], 0
    current: Optional[dict] = None
    for line in _unfold(text):
        name, params, value = _split(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            current = {}
        elif name == "END" and value.upper() == "VEVENT" and current is not None:
            summary = current.get("summary", "").lower()
            if any(word in summary for word in _BLOCKED):
                blocked += 1
            elif current.get("start") and current.get("end"):
                stays.append(Stay(current["start"], current["end"]))
            current = None
        elif current is not None:
            if name == "SUMMARY":
                current["summary"] = value
            elif name == "DTSTART":
                current["start"] = _ics_when(value, params)[0]
            elif name == "DTEND":
                current["end"] = _ics_when(value, params)[0]
    stays.sort(key=lambda s: s.check_in)
    return stays, blocked


def _stay_events(stays: list[Stay], place: str) -> list[tuple[str, str, str]]:
    """Pure logic. The calendar events for the stays: (title, date, notes), a check-in and a check-out each."""
    events = []
    for s in stays:
        nights = f"{s.nights} night{'s' if s.nights != 1 else ''}"
        events.append((f"Check-in · {place}", s.check_in, f"Booked stay, {nights}, from the listing's calendar link."))
        events.append((f"Check-out · {place}", s.check_out, f"Booked stay, {nights}, from the listing's calendar link."))
    return events


@dataclass
class Preview:
    """What an import would do: the rows it would add (in words), how many are already in MIA, what it couldn't read,
    and anything left out on purpose."""
    adds: list[str] = field(default_factory=list)
    already: int = 0
    unreadable: list[str] = field(default_factory=list)
    left_out: str = ""

    def sentence(self, what: str) -> str:
        """The preview in one sentence, for the approval card."""
        text = f"Add {len(self.adds)} {what}" if self.adds else f"Nothing new to add from {what}"
        if self.already:
            text += f"; {self.already} already in MIA"
        if self.unreadable:
            text += f"; {len(self.unreadable)} couldn't be read"
        if self.left_out:
            text += f"; {self.left_out}"
        return text + "."

    def as_dict(self) -> dict:
        """For the Connect Apps page: the first rows to add, the counts and what was left out."""
        return {"adds": self.adds[:50], "count": len(self.adds), "already": self.already,
                "unreadable": self.unreadable[:20], "left_out": self.left_out}


def _calendar_keys(context) -> set:
    """The calendar's events as (title, date) keys, the duplicate rule core/imports.py uses."""
    calendar = getattr(context, "calendar", None)
    return {(e.title.strip().lower(), e.date) for e in calendar.all_events()} if calendar is not None else set()


def rental_preview(context, text: str, place: str) -> tuple[Preview, list[tuple[str, str, str]]]:
    """A rental calendar's preview for the property named, and the events it would add."""
    stays, blocked = parse_stays(text)
    events = _stay_events(stays, place)
    have = _calendar_keys(context)
    new = [e for e in events if (e[0].strip().lower(), e[1]) not in have]
    preview = Preview(adds=[f"{t} on {d}" for t, d, _n in new], already=len(events) - len(new),
                      left_out=f"{blocked} blocked span{'s' if blocked != 1 else ''} left out" if blocked else "")
    return preview, new


def file_preview(context, name: str, text: str) -> tuple[str, Preview]:
    """A downloaded file's kind and preview, by core/imports.py's own parsers and duplicate rules; raises ValueError
    for a file MIA can't import."""
    from core import imports

    kind = imports.kind_of(Path(name or "import"), text)
    if kind is None:
        raise ValueError("MIA can import calendar files (.ics), contacts (.vcf) and bank statements (.csv).")
    if kind == imports.CALENDAR:
        events, problems = imports.parse_ics(text)
        have = _calendar_keys(context)
        new = [e for e in events if (e.title.strip().lower(), e.date) not in have]
        return kind, Preview([f"{e.title} on {e.date}" for e in new], len(events) - len(new), problems)
    if kind == imports.CONTACTS:
        people, problems = imports.parse_vcards(text)
        known = {p.name.strip().lower() for p in context.relationships.all_people()}
        new = [p for p in people if p.name.strip().lower() not in known]
        return kind, Preview([p.name for p in new], len(people) - len(new), problems)
    transactions, problems = imports.parse_bank_csv(text)
    budget = context.budget
    seen = {(e.date, round(e.amount, 2), e.description.strip().lower()) for e in budget.all_expenses()}
    seen |= {(i.date, round(i.amount, 2), i.description.strip().lower()) for i in budget.all_income()}
    new = [t for t in transactions if (t.date, round(t.amount, 2), t.description.strip().lower()) not in seen]
    from core.region import money

    return kind, Preview([f"{t.date} {t.description}: {money(t.amount)}{' in' if t.is_income else ''}" for t in new],
                         len(transactions) - len(new), problems)


# ------------------------------------------------------------------ the action kinds


def _place(params) -> str:
    """The property a rental calendar is for, as said; ActionError without one."""
    from core.actions import ActionError

    place = " ".join(str(params.get("property") or "").split())[:60]
    if not place:
        raise ActionError("Which property is this calendar for?")
    return place


def _rental_text(params) -> str:
    """The rental calendar's text: fetched from its link, or given (a file); ActionError, said plainly, when it can't
    be read."""
    from core.actions import ActionError

    if params.get("text"):
        return str(params["text"])
    try:
        return fetch_link(str(params.get("url") or ""))
    except LinkError as problem:
        raise ActionError(str(problem)) from None


def _describe_rental(context, params) -> str:
    """The sentence the approval card shows for `connect.rental_calendar`: what the import would add."""
    preview, _new = rental_preview(context, _rental_text(params), _place(params))
    return f"{_place(params)}'s calendar: " + preview.sentence("check-ins and check-outs")


def _import_rental(context, params) -> str:
    """Does `connect.rental_calendar`: adds each new check-in and check-out to the Calendar (one undoable change)."""
    place = _place(params)
    _preview, new = rental_preview(context, _rental_text(params), place)
    for title, day, notes in new:
        context.calendar.add_event(title=title, date=day, notes=notes)
    log.info("Rental calendar imported for '%s': %d events.", place, len(new))
    return f"Added {len(new)} check-ins and check-outs for {place}." if new else f"{place}'s calendar had nothing new."


def _describe_file(context, params) -> str:
    """The sentence the approval card shows for `connect.file`: what importing the file would add."""
    from core.actions import ActionError

    try:
        kind, preview = file_preview(context, str(params.get("name") or ""), str(params.get("text") or ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return preview.sentence({"calendar": "calendar events", "contacts": "people", "bank": "transactions"}[kind])


def _import_file(context, params) -> str:
    """Does `connect.file`: the file through core/imports.py's own import for its kind (one undoable change)."""
    from core import imports
    from core.actions import ActionError

    text, name = str(params.get("text") or ""), str(params.get("name") or "")
    kind = imports.kind_of(Path(name or "import"), text)
    if kind is None:
        raise ActionError("MIA can import calendar files (.ics), contacts (.vcf) and bank statements (.csv).")
    run = {imports.CALENDAR: imports.import_calendar, imports.CONTACTS: imports.import_contacts,
           imports.BANK: imports.import_bank}[kind]
    return run(context, text).describe()


def _register() -> None:
    """Puts connect.file and connect.rental_calendar in ACTION_TYPES."""
    from core.actions import ACTION_TYPES, ActionType

    for kind in (
        ActionType("connect.file", "Import", {"name": "the file's name", "text": "its contents"}, _describe_file,
                   _import_file),
        ActionType("connect.rental_calendar", "Import", {"url": "the listing's calendar link", "property": "which property",
                                                          "text": "or the calendar file's contents"},
                   _describe_rental, _import_rental),
    ):
        ACTION_TYPES[kind.kind] = kind


def connect_page(context) -> dict:
    """The Connect Apps page: each source (name, how, where it lands, examples), the properties to pick for a rental
    calendar, and what's coming next (the audit's plan)."""
    real_estate = getattr(context, "real_estate", None)
    properties = [p.name for p in real_estate.all_properties()] if real_estate is not None else []
    return {"connectors": [{"id": c.connector_id, "name": c.name, "how": c.how, "lands": c.lands,
                            "examples": list(c.examples)} for c in CONNECTORS],
            "properties": properties,
            "coming": ["Hostaway and OwnerRez (a key from their settings)", "Google Sheets", "QuickBooks",
                       "TurboTax (your return's PDF)", "Airbnb earnings (CSV)"]}


_register()
