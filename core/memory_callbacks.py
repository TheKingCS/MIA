"""
core.memory_callbacks
=======================

Remembering at the right moment (DEC-0029, ALICE pick 3): MIA brings
up something you told her when it's about to matter, instead of waiting
to be asked.

- **A birthday coming up** (a person in a week or tomorrow, a pet
  tomorrow): with the gift ideas and favorites you noted, and anything
  MIA remembers about them.
- **Something on the calendar tomorrow** that names someone or something
  MIA remembers ("Dinner with Sam" → "Sam is vegetarian").
- **Upkeep due within two days** on gear with a note or a memory about it
  ("Sharpen blades: Mower" → "Last spring the blade was badly dull").

Only when there's something remembered to add: a plain due date is the
calendar's job, never repeated here. Facts come from code; nothing is
made up. On the desktop each one goes through the communication gate
(the daily limit, no repeats: `fingerprint`); on Home they're the small
"MIA Remembers" card, which is how a phone sees them.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

BIRTHDAY_DAYS = (7, 1, 0)
UPKEEP_DAYS = 2
MAX_MEMORIES = 2


def second_person(text: str) -> str:
    """Pure logic. Memories are kept as "The user's friend Sam is
    vegetarian"; said back, that's "your friend Sam is vegetarian"."""
    import re

    out = re.sub(r"\bthe user's\b", "your", text, flags=re.IGNORECASE)
    out = re.sub(r"\bthe user\b", "you", out, flags=re.IGNORECASE)
    out = re.sub(r"\byou (is|was|has)\b", lambda m: {"is": "you are", "was": "you were", "has": "you have"}[m.group(1)], out)
    return out


def _memories_about(context, text: str) -> list[str]:
    from core.user_memory_manager import relevant_memories

    store = getattr(context, "user_memories", None)
    if store is None or not text:
        return []
    return [second_person(m.text) for m in relevant_memories(text, store.all_memories(), MAX_MEMORIES)]


def _when(days: int) -> str:
    return "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"


def _birthdays(context, today: date) -> list[dict]:
    from core.web_more import next_birthday

    people = getattr(context, "relationships", None)
    out = []
    if people is None:
        return out
    for p in people.all_people():
        nb = next_birthday(p.birthday, today)
        if nb is None or nb[1] not in BIRTHDAY_DAYS:
            continue
        bits = []
        if p.gift_ideas:
            bits.append(f"Gift ideas you noted: {p.gift_ideas}.")
        if p.favorite_things:
            bits.append(f"Favorites: {p.favorite_things}.")
        bits += [f"You told me: {m}" for m in _memories_about(context, p.name)]
        if not bits and nb[1] != 0:
            continue  # nothing remembered to add; the calendar already shows the date
        turning = f" (turning {nb[2]})" if nb[2] else ""
        out.append({"key": f"birthday:{p.person_id}:{nb[0].isoformat()}:{nb[1]}", "icon": "🎂",
                    "title": f"{p.name}'s birthday is {_when(nb[1])}{turning}", "lines": bits,
                    "page": "people.html#birthdays", "days": nb[1]})
    for a in people.all_pets():
        nb = next_birthday(a.birthday, today)
        if nb is None or nb[1] not in (1, 0):
            continue
        out.append({"key": f"pet:{a.pet_id}:{nb[0].isoformat()}", "icon": "🐾",
                    "title": f"{a.name}'s birthday is {_when(nb[1])}" + (f" (turning {nb[2]})" if nb[2] else ""),
                    "lines": [f"Notes: {a.notes}."] if a.notes else [], "page": "people.html#pets", "days": nb[1]})
    return out


def _calendar(context, today: date) -> list[dict]:
    from core.calendar_manager import occurs_on

    calendar = getattr(context, "calendar", None)
    out = []
    if calendar is None:
        return out
    tomorrow = today + timedelta(days=1)
    for event in calendar.all_events():
        if not occurs_on(event, tomorrow):
            continue
        remembered = _memories_about(context, event.title)
        if remembered:
            out.append({"key": f"event:{event.event_id}:{tomorrow.isoformat()}", "icon": "📅",
                        "title": f"Tomorrow: {event.title}", "lines": [f"You told me: {m}" for m in remembered],
                        "page": "calendar.html", "days": 1})
    return out


def _upkeep(context, today: date) -> list[dict]:
    from core.maintenance_manager import next_occurrence_date
    from core.web_equipment import _readings

    maintenance = getattr(context, "maintenance", None)
    out = []
    if maintenance is None:
        return out
    for task in maintenance.all_tasks():
        asset = maintenance.get_asset(task.asset_id)
        if asset is None:
            continue
        when = next_occurrence_date(task, _readings(context, task), today)
        if when is None or (when - today).days > UPKEEP_DAYS:
            continue
        bits = [f"Your note: {task.notes}"] if task.notes else []
        bits += [f"You told me: {m}" for m in _memories_about(context, f"{asset.name} {task.title}")]
        if bits:
            days = (when - today).days
            out.append({"key": f"upkeep:{task.task_id}:{when.isoformat()}", "icon": "🔧",
                        "title": f"{task.title}: {asset.name} is due " + ("now" if days <= 0 else _when(days)),
                        "lines": bits[:3], "page": f"asset.html?id={asset.asset_id}", "days": max(0, days)})
    return out


def callbacks(context, today: Optional[date] = None) -> list[dict]:
    """Everything worth remembering right now, soonest first."""
    today = today or date.today()
    out = []
    for source in (_birthdays, _calendar, _upkeep):
        try:
            out += source(context, today)
        except Exception:
            log.debug("Memory callbacks: %s failed", source.__name__, exc_info=True)
    return sorted(out, key=lambda c: c["days"])


def as_message(item: dict) -> str:
    """Pure logic. One callback as a note's text."""
    return " ".join([item["title"] + "."] + item["lines"])
