"""
core.reminders_view
=====================

His reminders and the small everyday turns around them, in code (the live sweep, 2026-11-26):

- `listing`: "what reminders do I have?" (it had named only the wake-up alarm): the calendar's reminders still to
  come, the repeating ones with how often, and his alarms;
- `cancel`: "cancel the oil reminder" (it had said "it's not a reminder for the truck's oil change"): the one whose
  title holds every word he said, by its id, through the action contract (event.delete / alarm.delete: recorded and
  undoable); two that fit are asked about with their days; none, and the model has it;
  "turn off all reminders" lists them and asks which, never deleting them all on one sentence;
- `greeting`: "good morning" (it had said "I didn't get an answer together for that one"): back in kind, with the
  morning briefing's day when it's morning (core/morning_briefing.briefing);
- `yesterday`: "what did I do yesterday?" (it had said nothing's kept): yesterday's wins in a few words
  (core/life_events.WINS, as the evening wrap counts them), never something taken back since.
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
    """Pure logic. "every week", "every two weeks", "tomorrow at 09:00", "on Dec 3"."""
    if event.recurrence:
        return {"daily": "every day", "weekly": "every week", "biweekly": "every two weeks", "monthly": "every month",
                "yearly": "every year"}.get(event.recurrence, f"every {event.recurrence}")
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
    """For "cancel the oil reminder": the one reminder or alarm whose title holds every word he said, cancelled by
    its id through the action contract (undoable); the choice when several fit; for "all", the list and a question.
    None when no words are left to match or none fits (the model's then)."""
    today = today or date.today()
    if re.search(r"\b(?:all|every|everything)\b", words or "", re.I):
        found = listing(context, today)
        return found + " Which should I cancel? Say \"cancel the ... reminder\" for each, so none goes by accident."
    want = _words(words)
    if not want:
        return None
    # every word he said is in its title (never one shared word: "the oil change reminder" isn't "Change the filter")
    events = [e for e in _events(context, today) if want <= _words(e.title)]
    alarms = [a for a in _alarms(context) if want <= _words(a.label)]
    hits = [("event.delete", {"event_id": e.event_id}, e.title, _when(e, today)) for e in events] + \
        [("alarm.delete", {"alarm_id": a.alarm_id}, f"the {a.label} alarm", a.time) for a in alarms]
    if not hits:
        return None  # nothing it can name for sure: the model's (a maintenance task, a watch, a far-off reminder)
    if len(hits) > 1:
        return "Which one? " + "; ".join(f"{name} ({when})" for _k, _p, name, when in hits) + "."
    kind, params, name, when = hits[0]
    actions = getattr(context, "actions", None)
    if actions is None:
        return None
    from core.actions import ActionError

    try:  # his own request, through the action contract: recorded, and "undo that" brings it back
        done = actions.approve(context, actions.propose(context, kind, params).proposal_id)
    except ActionError as problem:
        return str(problem)
    repeats = " It was a repeating one; the whole series is gone." if "every" in when else ""
    return f"Cancelled {name}.{repeats} Say \"undo that\" to bring it back." if done.status == "executed" else \
        (done.result or "I couldn't cancel it.")


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
    """For "what did I do yesterday?": yesterday's wins counted by kind (core/life_events.WINS), never one taken
    back since."""
    from core import life_events

    day = (today or date.today()) - timedelta(days=1)
    try:
        events = [e for e in life_events.events_for(context, since=day.isoformat(), until=day.isoformat())
                  if e.type not in life_events.AUDIT_ONLY]
    except Exception:  # noqa: BLE001
        log.exception("Yesterday couldn't be read")
        events = []
    try:  # what's been taken back since, today included, doesn't count
        later = life_events.events_for(context, since=day.isoformat())
    except Exception:  # noqa: BLE001
        later = events
    taken_back = life_events.reversed_ids(later)
    kept = [e for e in events if e.event_id not in taken_back and e.type in life_events.WINS]
    if not kept:
        return f"Nothing's logged for yesterday ({day:%A}). Tell me what you do as you go, and I'll keep the day."
    from core.evening_wrap import _count

    totals = life_events.counts(kept)
    said = ", ".join(_count(n, life_events.TYPES.get(t, t)) for t, n in sorted(totals.items(), key=lambda kv: -kv[1])[:6])
    return f"Yesterday ({day:%A}): {said}."
