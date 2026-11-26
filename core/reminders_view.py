"""
core.reminders_view
=====================

His reminders and the small everyday turns around them, in code (the live sweep, 2026-11-26):

- `listing`: "what reminders do I have?" (it had named only the wake-up alarm): the calendar's reminders still to
  come, the repeating ones with how often, and his alarms;
- `cancel`: "cancel the oil reminder" (it had said "it's not a reminder for the truck's oil change"): the one his
  words name, through the delete_calendar_event or delete_alarm tool (undoable); two that fit are asked about;
  "turn off all reminders" lists them and asks which, never deleting them all on one sentence;
- `greeting`: "good morning" (it had said "I didn't get an answer together for that one"): back in kind, with the
  morning briefing's day when it's morning (core/morning_briefing.briefing);
- `yesterday`: "what did I do yesterday?" (it had said nothing's kept): yesterday's history in a few words
  (core/life_events).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

AHEAD_DAYS = 60
SHOWN = 8


def _events(context, today: date) -> list:
    """The calendar's reminders still to come: repeating ones, and one-offs from today on (within AHEAD_DAYS)."""
    calendar = getattr(context, "calendar", None)
    if calendar is None:
        return []
    end = (today + timedelta(days=AHEAD_DAYS)).isoformat()
    return [e for e in calendar.all_events() if e.recurrence or today.isoformat() <= (e.date or "") <= end]


def _alarms(context) -> list:
    """His alarms that are on."""
    alarms = getattr(context, "alarms", None)
    try:
        return [a for a in alarms.all_alarms() if a.enabled] if alarms is not None else []
    except Exception:  # noqa: BLE001
        return []


def _when(event, today: date) -> str:
    """Pure logic. "every week", "tomorrow at 09:00", "on Dec 3"."""
    if event.recurrence:
        return {"daily": "every day", "weekly": "every week", "monthly": "every month",
                "yearly": "every year"}.get(event.recurrence, event.recurrence)
    day = date.fromisoformat(event.date[:10])
    said = "today" if day == today else "tomorrow" if day == today + timedelta(days=1) else f"on {day:%b} {day.day}"
    return said + (f" at {event.time}" if event.time else "")


def listing(context, today: Optional[date] = None) -> str:
    """For "what reminders do I have?"."""
    today = today or date.today()
    events = sorted(_events(context, today), key=lambda e: (not e.recurrence, e.date or ""))
    alarms = _alarms(context)
    if not events and not alarms:
        return "You don't have any reminders. Say one, like \"remind me every Friday to check the oil\"."
    parts = [f"{e.title} ({_when(e, today)})" for e in events[:SHOWN]]
    parts += [f"the {a.label} alarm at {a.time}" for a in alarms[:SHOWN]]
    more = len(events) + len(alarms) - len(parts)
    return "Your reminders: " + "; ".join(parts) + (f"; and {more} more" if more > 0 else "") + "."


def _words(text: str) -> set:
    """Pure logic. A title's or a request's words, small ones left out."""
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 2} - {
        "the", "my", "reminder", "reminders", "alarm", "cancel", "delete", "remove", "stop", "turn", "off", "that",
        "about", "for", "to", "please", "mia"}


def cancel(context, words: str, today: Optional[date] = None) -> Optional[str]:
    """For "cancel the oil reminder": the one reminder or alarm his words name, deleted through its tool; the
    choice when several fit; for "all", the list and a question. None when no words are left to match."""
    today = today or date.today()
    if re.search(r"\b(?:all|every|everything)\b", words or "", re.I):
        found = listing(context, today)
        return found + " Which should I cancel? Say \"cancel the ... reminder\" for each, so none goes by accident."
    want = _words(words)
    if not want:
        return None
    events = [e for e in _events(context, today) if want & _words(e.title)]
    alarms = [a for a in _alarms(context) if want & _words(a.label)]
    hits = [("event", e.title) for e in events] + [("alarm", a.label) for a in alarms]
    if not hits:
        return f"I don't see a reminder about {' '.join(sorted(want))}. " + listing(context, today)
    if len(hits) > 1:
        return "Which one? " + "; ".join(name for _, name in hits) + "."
    kind, name = hits[0]
    actions = getattr(context, "assistant_actions", None)
    if actions is None:
        return None
    tool, arguments = ("delete_calendar_event", {"title": name}) if kind == "event" else ("delete_alarm", {"label": name})
    return actions.execute(context, tool, arguments)


def greeting(context, words: str, now: Optional[datetime] = None) -> str:
    """Back in kind; in the morning with the briefing's day (weather and what's first) when there is one."""
    now = now or datetime.now()
    said = (words or "").lower()
    if "morning" in said and now.hour < 12:
        try:
            from core.morning_briefing import briefing

            day = briefing(context, now)
            if day:
                return day
        except Exception:  # noqa: BLE001
            log.exception("Greeting: the briefing couldn't be read")
        return "Good morning. Nothing on today's list yet. What's first?"
    part = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    if re.search(r"\bgood (?:morning|afternoon|evening)\b", said):
        return f"Good {part}. What can I do for you?"
    return "Hey. What can I do for you?"


def yesterday(context, today: Optional[date] = None) -> str:
    """For "what did I do yesterday?": yesterday's history counted by kind, from core/life_events."""
    from core import life_events

    day = (today or date.today()) - timedelta(days=1)
    try:
        events = [e for e in life_events.events_for(context, since=day.isoformat(), until=day.isoformat())
                  if e.type not in life_events.AUDIT_ONLY]
    except Exception:  # noqa: BLE001
        log.exception("Yesterday couldn't be read")
        events = []
    taken_back = life_events.reversed_ids(events)
    kept = [e for e in events if e.event_id not in taken_back and e.type != "undone"]
    if not kept:
        return f"Nothing's logged for yesterday ({day:%A}). Tell me what you do as you go, and I'll keep the day."
    from core.evening_wrap import _count

    totals = life_events.counts(kept)
    said = ", ".join(_count(n, life_events.TYPES.get(t, t)) for t, n in sorted(totals.items(), key=lambda kv: -kv[1])[:6])
    return f"Yesterday ({day:%A}): {said}."
