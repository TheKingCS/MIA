"""
core.calendar_manager
========================

Backs the Calendar tool (modules/toolbox/tools/calendar_tool.py) — a
plain CRUD event store, persisted to data/calendar_events.json so
events survive a restart, same durability guarantee
core.notification_manager.NotificationManager gives notifications.

Lives in core/ (not modules/toolbox/) even though only the Calendar
tool uses it today, matching the existing convention that data/ is
only ever written to by core/ services (profile_manager,
notification_manager, backup_manager) — this also means calendar
events are automatically swept up by backup_manager's data/ rglob,
with no backup/restore code changes needed.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_EVENTS_FILE = _DATA_DIR / "calendar_events.json"


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    date: str  # ISO "YYYY-MM-DD"
    time: Optional[str] = None  # "HH:MM", or None for an all-day event
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict) -> "CalendarEvent":
        return CalendarEvent(
            event_id=data.get("event_id", uuid.uuid4().hex[:10]),
            title=data.get("title", ""),
            date=data.get("date", ""),
            time=data.get("time"),
            notes=data.get("notes", ""),
        )


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

    def add_event(self, title: str, date: str, time: Optional[str] = None, notes: str = "") -> CalendarEvent:
        event = CalendarEvent(
            event_id=uuid.uuid4().hex[:10],
            title=title,
            date=date,
            time=time,
            notes=notes,
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

    def events_for_date(self, date: str) -> list[CalendarEvent]:
        """Events on `date` (ISO "YYYY-MM-DD"), all-day events first, then sorted by time."""
        matches = [e for e in self._events if e.date == date]
        return sorted(matches, key=lambda e: (e.time is not None, e.time or ""))

    def events_for_month(self, year: int, month: int) -> dict[str, list["CalendarEvent"]]:
        """All events in `year`-`month`, grouped by ISO date, each list in events_for_date order."""
        prefix = f"{year:04d}-{month:02d}-"
        grouped: dict[str, list[CalendarEvent]] = {}
        for event in self._events:
            if event.date.startswith(prefix):
                grouped.setdefault(event.date, []).append(event)
        for date in grouped:
            grouped[date] = self.events_for_date(date)
        return grouped
