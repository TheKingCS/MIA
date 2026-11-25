"""
core.calendar_move
====================

"Actually, make it Sunday" (Jarvis brainstorm, round 12; smooth conversation): move a calendar event to another day
or time. Before, the calendar could add and delete but not move, so "make it Sunday" after "remind me to change the
truck oil next Saturday" added a second task (live check through the whole turn, 2026-11-24).

**Which event** (`which`): the one whose title his words name ("move the dentist to Friday"), else the one added most
recently (core/calendar_manager.py all_events keeps the order added): "it" and "that" are what was just said.
**The day** (`day_of`): a date as YYYY-MM-DD, else a day in his words ("Sunday", "tomorrow", "the day after",
core/weather.days_meant), the next one from today. **The time**: HH:MM when he gives one; else it keeps its own.
Undoable like any calendar change (core/calendar_manager.update_event writes through atomic_write).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional


def which(events: list, title: str):
    """Pure logic. The event a title names (every word of it in the event's), else the newest; None without any."""
    words = [w for w in re.findall(r"[a-z0-9']+", str(title or "").lower()) if w not in ("the", "my", "a", "it", "that")]
    if words:
        named = [e for e in events if all(w in e.title.lower() for w in words)]
        if named:
            return named[-1]
    return events[-1] if events else None


def day_of(text: str, today: Optional[date] = None) -> Optional[str]:
    """Pure logic. A day his words give, as YYYY-MM-DD: a weekday, "tomorrow", "the day after" first (the model passed
    "Monday" as 2024-01-01: live check, 2026-11-24), else an ISO date."""
    from core.weather import days_meant

    days = days_meant(str(text or ""), today or date.today())
    if days:
        return days[0].isoformat()
    found = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", str(text or ""))
    return found.group(1) if found else None


def event_day(date_str: str) -> Optional[str]:
    """Pure logic. A calendar event's day as YYYY-MM-DD: an ISO date as it is, else the day words give ("Friday at
    2pm", passed as the date: live check, 2026-11-24), else None. For both add_calendar_event handlers."""
    said = str(date_str or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", said):
        return said
    return day_of(said)


def move(context, title: str = "", when: str = "", time: str = "", today: Optional[date] = None) -> str:
    """Moves the event (see the module's opening) and says where it is now."""
    calendar = getattr(context, "calendar", None)
    events = calendar.all_events() if calendar is not None else []
    event = which(events, title)
    if event is None:
        return "There's nothing on your calendar to move yet."
    new_day = day_of(when, today)
    new_time = time.strip() if re.fullmatch(r"\d{1,2}:\d{2}", str(time or "").strip()) else None
    if new_day is None and new_time is None:
        return f"To when? Say a day for '{event.title}', like \"move it to Sunday\"."
    fields = {"date": new_day} if new_day else {}
    if new_time:
        fields["time"] = new_time
    calendar.update_event(event.event_id, **fields)
    moved = date.fromisoformat(fields.get("date", event.date))
    return (f"Moved '{event.title}' to {moved:%A, %B} {moved.day}" + (f" at {new_time}" if new_time else "") + ".")


def _tool(context, arguments: dict) -> str:
    """Tool move_calendar_event: `move` with what the model passed and his words."""
    # his words first, so a day he named wins over a date the model made up
    return move(context, str(arguments.get("title", "") or ""),
                " ".join(str(arguments.get(k) or "") for k in ("question", "date")),
                str(arguments.get("time", "") or ""))


def register_calendar_move_actions(registry) -> None:
    """Registers move_calendar_event."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="move_calendar_event", domain="calendar",
        description="Move an event already on his calendar to another day or time (\"move it to Sunday\", "
                    "\"actually make it Sunday\", \"reschedule the dentist to Friday\"); with no title, the one just "
                    "added. A new event is add_calendar_event.",
        parameters={"type": "object", "properties": {
            "title": {"type": "string", "description": "the event's title, only if he named it"},
            "date": {"type": "string", "description": "the new day, YYYY-MM-DD or as he said it"},
            "time": {"type": "string", "description": "a new time, HH:MM, only if he said one"},
            "question": {"type": "string", "description": "his words"}},
            "required": []},
        handler=_tool,
        trigger_phrases=("move it to", "move that to", "move the", "reschedule", "push it to", "push that to",
                         "actually make it", "make it sunday", "make it saturday", "make it monday",
                         "make it tuesday", "make it wednesday", "make it thursday", "make it friday",
                         "make it tomorrow", "change it to", "change that to"),
    ))
