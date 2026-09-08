"""
core.calendar_manager
========================

Backs the Calendar tool (modules/toolbox/tools/calendar_tool.py) — a
CRUD event store, persisted to data/calendar_events.json so events
survive a restart, same durability guarantee
core.notification_manager.NotificationManager gives notifications.

Lives in core/ (not modules/toolbox/) even though only the Calendar
tool uses it today, matching the existing convention that data/ is
only ever written to by core/ services (profile_manager,
notification_manager, backup_manager) — this also means calendar
events are automatically swept up by backup_manager's data/ rglob,
with no backup/restore code changes needed.

Recurring events (2026-09-08, closing a real documented gap —
docs/KNOWN_ISSUES.md's "Calendar has no recurring-event support"):
a CalendarEvent's `date` is always its one stored anchor date;
`recurrence` (None/"yearly"/"monthly"/"weekly") plus the pure
occurs_on() function below determine whether it ALSO occurs on any
other date being asked about. This is the one place that logic lives —
events_for_date()/events_for_month() and
core.daily_occasions.calendar_events_today() all resolve through it,
so an anniversary now surfaces every year, not just on the day it was
originally entered.
"""

from __future__ import annotations

import json
import uuid
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_EVENTS_FILE = _DATA_DIR / "calendar_events.json"

RECURRENCE_TYPES = ["yearly", "monthly", "weekly", "biweekly"]


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    date: str  # ISO "YYYY-MM-DD" — the anchor date; see occurs_on() for recurrence
    time: Optional[str] = None  # "HH:MM", or None for an all-day event
    notes: str = ""
    recurrence: Optional[str] = None  # None, or one of RECURRENCE_TYPES

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "notes": self.notes,
            "recurrence": self.recurrence,
        }

    @staticmethod
    def from_dict(data: dict) -> "CalendarEvent":
        return CalendarEvent(
            event_id=data.get("event_id", uuid.uuid4().hex[:10]),
            title=data.get("title", ""),
            date=data.get("date", ""),
            time=data.get("time"),
            notes=data.get("notes", ""),
            recurrence=data.get("recurrence"),
        )


def date_recurs_on(anchor: date, recurrence: Optional[str], check_date: date) -> bool:
    """
    True if a thing anchored on `anchor` with `recurrence` (None/
    "yearly"/"monthly"/"weekly"/"biweekly") occurs on `check_date`. The shared
    recurrence primitive underneath both `occurs_on()` below (Calendar
    events) and `core.budget_manager`'s Bill due-date logic — extracted
    here rather than reimplemented a second time, since it's plain date
    arithmetic with no Calendar-specific concept in it at all. A `core/`
    module importing another `core/` module is unrestricted (only
    `modules/` has the no-cross-import layering rule).

    No recurrence: only the anchor date itself. Recurring: the anchor
    date and every matching anniversary AFTER it — never retroactively
    before the anchor. Monthly recurrence on a day that doesn't exist
    in a given month (the 31st in February) simply doesn't occur that
    month — never fabricated onto a nearby date.
    """
    if check_date < anchor:
        return False
    if recurrence is None:
        return check_date == anchor
    if recurrence == "yearly":
        return (check_date.month, check_date.day) == (anchor.month, anchor.day)
    if recurrence == "monthly":
        return check_date.day == anchor.day
    if recurrence == "weekly":
        return check_date.weekday() == anchor.weekday() and (check_date - anchor).days % 7 == 0
    if recurrence == "biweekly":
        return check_date.weekday() == anchor.weekday() and (check_date - anchor).days % 14 == 0
    return check_date == anchor  # unknown recurrence value — fail safe to exact-date-only


def occurs_on(event: CalendarEvent, check_date: date) -> bool:
    """
    True if `event` occurs on `check_date`, accounting for recurrence —
    same "take the date as an explicit parameter" testability
    convention as core.alarm_manager.Alarm.check_due/
    core.maintenance_manager's recurrence functions. See
    date_recurs_on() above for the actual comparison logic.
    """
    try:
        anchor = date.fromisoformat(event.date)
    except ValueError:
        return False
    return date_recurs_on(anchor, event.recurrence, check_date)


class CalendarManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._events: list[CalendarEvent] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _EVENTS_FILE.exists():
            self._events = []
            return
        try:
            raw = json.loads(_EVENTS_FILE.read_text(encoding="utf-8"))
            self._events = [CalendarEvent.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load calendar_events.json — starting with an empty list.")
            self._events = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _EVENTS_FILE.write_text(
            json.dumps([e.to_dict() for e in self._events], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_event(
        self,
        title: str,
        date: str,
        time: Optional[str] = None,
        notes: str = "",
        recurrence: Optional[str] = None,
    ) -> CalendarEvent:
        event = CalendarEvent(
            event_id=uuid.uuid4().hex[:10],
            title=title,
            date=date,
            time=time,
            notes=notes,
            recurrence=recurrence,
        )
        self._events.append(event)
        self._save()
        log.info("Calendar event added: '%s' on %s", title, date)
        return event

    def update_event(self, event_id: str, **fields) -> CalendarEvent:
        event = self.get_event(event_id)
        if event is None:
            raise ValueError(f"No calendar event with id '{event_id}'.")
        for key, value in fields.items():
            if not hasattr(event, key):
                raise ValueError(f"CalendarEvent has no field '{key}'.")
            setattr(event, key, value)
        self._save()
        return event

    def delete_event(self, event_id: str) -> None:
        self._events = [e for e in self._events if e.event_id != event_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def all_events(self) -> list[CalendarEvent]:
        return list(self._events)

    def events_for_date(self, date_str: str) -> list[CalendarEvent]:
        """Events occurring on `date_str` (ISO "YYYY-MM-DD"), all-day
        events first, then sorted by time. Accounts for recurrence via
        occurs_on() — a recurring event surfaces here on every matching
        anniversary, not just the exact date it was originally entered."""
        check_date = date.fromisoformat(date_str)
        matches = [e for e in self._events if occurs_on(e, check_date)]
        return sorted(matches, key=lambda e: (e.time is not None, e.time or ""))

    def events_for_month(self, year: int, month: int) -> dict[str, list["CalendarEvent"]]:
        """Every real day in `year`-`month`, grouped by ISO date (only
        dates with at least one occurrence included), each list in
        events_for_date order. Walks real calendar days rather than
        string-matching stored dates, since a recurring event's
        anchor date can be in a completely different month/year from
        an occurrence being displayed here."""
        days_in_month = monthrange(year, month)[1]
        grouped: dict[str, list[CalendarEvent]] = {}
        for day in range(1, days_in_month + 1):
            date_str = date(year, month, day).isoformat()
            matches = self.events_for_date(date_str)
            if matches:
                grouped[date_str] = matches
        return grouped
