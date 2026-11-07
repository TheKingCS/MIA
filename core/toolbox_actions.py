"""
core.toolbox_actions
======================

The Toolbox's changes on the web (DEC-0113 canvas Toolbox, DEC-0125: alarms
were set only on the PC or by voice). An alarm is set with `alarm.add` (a
label, a clock time said any common way, and once / every day / weekdays /
weekends), switched on or off with `alarm.switch`, and taken out with
`alarm.delete`, all through core/alarm_manager.py. The PC still rings it
(core/application.py checks alarms each minute).

clock_time() reads "7", "7:30", "7:30 pm", "730am" or "19:05" as 24-hour
HH:MM, so the screen, the form and a typed time agree.
"""

from __future__ import annotations

import re

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

REPEATS = {"Once": [], "Every day": [0, 1, 2, 3, 4, 5, 6], "Weekdays": [0, 1, 2, 3, 4], "Weekends": [5, 6]}
_CLOCK = re.compile(r"^\s*(\d{1,2})(?::?(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\s*$", re.IGNORECASE)


def clock_time(text: str) -> str:
    """Pure logic. A clock time as 24-hour "HH:MM": "7" -> "07:00", "7:30 pm" -> "19:30", "730am" -> "07:30",
    "12 am" -> "00:00". ValueError for anything that isn't a time of day."""
    m = _CLOCK.match(str(text or ""))
    if not m:
        raise ValueError("What time? Like 7:30 or 6:15 pm.")
    hour, minute, half = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower().replace(".", "")
    if half:
        if not 1 <= hour <= 12:
            raise ValueError("With am or pm the hour is 1 to 12.")
        hour = hour % 12 + (12 if half == "pm" else 0)
    if hour > 23 or minute > 59:
        raise ValueError("That isn't a time of day.")
    return f"{hour:02d}:{minute:02d}"


def repeat_word(days: list) -> str:
    """Pure logic. An alarm's weekdays in a word: "Once", "Every day", "Weekdays", "Weekends", or "Mon, Wed"."""
    days = sorted(set(days or []))
    for word, these in REPEATS.items():
        if days == these:
            return word
    return ", ".join(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[d] for d in days if 0 <= d <= 6)


def _alarm(context, params):
    """The alarm named by alarm_id, or ActionError."""
    found = _need(context, "alarms").get_alarm(str(params.get("alarm_id") or ""))
    if found is None:
        raise ActionError("That alarm isn't here any more.")
    return found


def _add_parts(params) -> tuple[str, str, list]:
    """The new alarm's label, time and days from the form, or ActionError."""
    try:
        at = clock_time(params.get("time"))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    repeat = str(params.get("repeat") or "Once")
    if repeat not in REPEATS:
        raise ActionError("Repeat is once, every day, weekdays or weekends.")
    return (str(params.get("label") or "").strip() or "Alarm"), at, REPEATS[repeat]


def _describe_add(context, params) -> str:
    """The sentence the approval card shows for `alarm.add`; ActionError when it can't be done."""
    _need(context, "alarms")
    label, at, days = _add_parts(params)
    return f"Set an alarm “{label}” for {at}" + ("" if not days else f", {repeat_word(days).lower()}")


def _add(context, params) -> str:
    """Does `alarm.add` once approved."""
    label, at, days = _add_parts(params)
    _need(context, "alarms").add_alarm(label=label, time=at, days=days)
    return f"Alarm “{label}” set for {at}."


def _on(params) -> bool:
    """Whether `alarm.switch` turns it on (on: yes/true/1/on)."""
    return str(params.get("on", "yes")).lower() in ("yes", "true", "1", "on")


def _describe_switch(context, params) -> str:
    """The sentence for `alarm.switch`."""
    return f"Turn {'on' if _on(params) else 'off'} the alarm “{_alarm(context, params).label}”"


def _switch(context, params) -> str:
    """Does `alarm.switch`: the alarm on or off (off keeps it, it just won't ring)."""
    alarm = _alarm(context, params)
    _need(context, "alarms").update_alarm(alarm.alarm_id, enabled=_on(params))
    return f"“{alarm.label}” is {'on' if _on(params) else 'off'}."


def _describe_delete(context, params) -> str:
    """The sentence for `alarm.delete`."""
    a = _alarm(context, params)
    return f"Delete the alarm “{a.label}” ({a.time})"


def _delete(context, params) -> str:
    """Does `alarm.delete`."""
    a = _alarm(context, params)
    _need(context, "alarms").delete_alarm(a.alarm_id)
    return f"Deleted the alarm “{a.label}”."


ALARM_FIELDS = [
    {"name": "label", "label": "What it's for", "type": "text", "required": False, "options": [], "default": "Alarm"},
    {"name": "time", "label": "Time (7:30, 6:15 pm...)", "type": "text", "required": True, "options": [], "default": None},
    {"name": "repeat", "label": "Repeat", "type": "choice", "required": False, "options": list(REPEATS), "default": "Once"},
]

_KINDS = [
    ActionType("alarm.add", "Set Alarm", {"label": "what it's for", "time": "a clock time", "repeat": "optional"},
               _describe_add, _add),
    ActionType("alarm.switch", "Turn Alarm On or Off", {"alarm_id": "the alarm", "on": "yes or no"},
               _describe_switch, _switch),
    ActionType("alarm.delete", "Delete Alarm", {"alarm_id": "the alarm"}, _describe_delete, _delete),
]
TOOLBOX_ACTIONS = {k.kind: k for k in _KINDS}
ACTION_TYPES.update(TOOLBOX_ACTIONS)
