"""
core.calendar_actions
=======================

Your own calendar events (Zac, 2026-10-16), through the action contract
(core/actions.py): `event.add` and `event.delete`. Everything else on the
calendar (upkeep, bills, meals, training, birthdays) is read from its own
store by core/calendar_view.py and changed where it lives. The calendar
store writes through atomic_write_text, so "undo" takes a change back.
"""

from __future__ import annotations

import re
from datetime import date

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

_REPEATS = ("weekly", "biweekly", "monthly", "yearly")


def _event_fields(params) -> dict:
    title = str(params.get("title") or "").strip()
    if not title:
        raise ActionError("What's the event? Give it a name.")
    raw = str(params.get("date") or "").strip()
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        raise ActionError("Pick a date for it.") from None
    time = str(params.get("time") or "").strip() or None
    if time:
        match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)?", time.lower())
        if not match:
            raise ActionError("Write the time like 14:30 or 2:30 pm.")
        hour, minute, half = int(match.group(1)), int(match.group(2) or 0), match.group(3)
        if half:
            hour = hour % 12 + (12 if half.startswith("p") else 0)
        if hour > 23 or minute > 59:
            raise ActionError("That time doesn't exist.")
        time = f"{hour:02d}:{minute:02d}"
    repeats = str(params.get("recurrence") or "").strip().lower() or None
    if repeats and repeats not in _REPEATS:
        raise ActionError("It can repeat weekly, every two weeks, monthly or yearly.")
    return {"title": title, "date": day.isoformat(), "time": time, "recurrence": repeats,
            "notes": str(params.get("notes") or "").strip()}


def _describe_add(context, params) -> str:
    f = _event_fields(params)
    day = date.fromisoformat(f["date"])
    when = f"{day:%a}, {day:%b} {day.day}" + (f" at {f['time']}" if f["time"] else "")
    return f"Add \"{f['title']}\" to the calendar on {when}" + (f", repeating {f['recurrence']}" if f["recurrence"] else "")


def _add(context, params) -> str:
    f = _event_fields(params)
    _need(context, "calendar").add_event(**f)
    return f"Added {f['title']} to the calendar."


def _event(context, params):
    event = _need(context, "calendar").get_event(str(params.get("event_id") or ""))
    if event is None:
        raise ActionError("That event isn't on the calendar any more.")
    return event


def _describe_delete(context, params) -> str:
    event = _event(context, params)
    return f"Remove \"{event.title}\" from the calendar" + (" (every repeat)" if event.recurrence else "")


def _delete(context, params) -> str:
    event = _event(context, params)
    context.calendar.delete_event(event.event_id)
    return f"Removed {event.title}."


for _a in (
    ActionType("event.add", "Add Event", {"title": "what it is", "date": "YYYY-MM-DD", "time": "optional: 14:30",
                                         "recurrence": "optional: weekly, biweekly, monthly, yearly",
                                         "notes": "optional"}, _describe_add, _add),
    ActionType("event.delete", "Remove", {"event_id": "the event"}, _describe_delete, _delete),
):
    ACTION_TYPES[_a.kind] = _a
