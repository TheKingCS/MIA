"""
core.web_changes
==================

Recent Changes on the web (the screens review's missing "Recent changes /
Undo history", docs/design/CORE_SCREENS_REVIEW.md section 3; DEC-0125:
"undo that" and "what did you just change?" were voice-only). Two parts:

- **Undo**: the changes MIA can still put back for this person
  (core/undo_log.py keeps the last 20 since MIA started), newest first,
  each in words (the history's own summary when the change recorded one),
  when, and whether the person or MIA made it. Only the newest can be undone,
  as by voice: `undo.last` (an action, so the page and "undo that" agree).
- **History**: what happened in the last fortnight, from the history
  (core/life_events.py), newest first, by day; undone ones are marked.

The web only draws.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger

log = get_logger(__name__)

HISTORY_DAYS = 14


def label_words(label: str) -> str:
    """Pure logic. A change's label in words: an action kind by its own label ("action_routine.add" -> "Add
    Routine"), a tool's name with spaces ("add_expense" -> "add expense")."""
    if label.startswith("action_"):
        kind = label[len("action_"):]
        action = ACTION_TYPES.get(kind)
        return action.label if action is not None else kind.replace(".", " ").replace("_", " ")
    return label.replace("_", " ")


def clock(at: str) -> str:
    """Pure logic. The time of day of an ISO moment: "2:05 PM"; "" when it can't be read."""
    try:
        moment = datetime.fromisoformat(at[:19])
    except ValueError:
        return ""
    return f"{moment.hour % 12 or 12}:{moment:%M} {'PM' if moment.hour >= 12 else 'AM'}"


def when_words(at: str, now: datetime) -> str:
    """Pure logic. When something happened, in a few words: "2:05 PM" today, "yesterday 2:05 PM", "Nov 3"."""
    try:
        moment = datetime.fromisoformat(at[:19])
    except ValueError:
        return ""
    clock_ = clock(at)
    if moment.date() == now.date():
        return clock_
    if moment.date() == now.date() - timedelta(days=1):
        return "yesterday " + clock_
    return f"{moment:%b} {moment.day}"


def _summaries(context, ids: set) -> dict:
    """The history's summary for each event id asked about (both logs), {} when there's no history."""
    from core.life_events import events_for

    if not ids:
        return {}
    try:
        return {e.event_id: e.summary for e in events_for(context) if e.event_id in ids}
    except Exception:
        log.exception("Recent changes: history read failed")
        return {}


def changes_page(context, now: Optional[datetime] = None) -> dict:
    """The Recent Changes screen: the undoable changes (newest first, the first one undoable) and the last fortnight's
    history by day."""
    from core.life_events import events_for, reversed_ids
    from core.person_settings import person_id

    now = now or datetime.now()
    undo = getattr(context, "undo", None)
    changes = undo.recent(person_id(context)) if undo is not None else []
    said = _summaries(context, {e for c in changes for e in c.events})
    undoable = [{"what": next((said[e] for e in c.events if e in said), None) or label_words(c.label),
                 "when": when_words(c.at, now), "by": "MIA" if c.by == "mia" else "You", "newest": i == 0}
                for i, c in enumerate(changes)]
    since = (now.date() - timedelta(days=HISTORY_DAYS - 1)).isoformat()
    try:
        events = events_for(context, since=since)
    except Exception:
        log.exception("Recent changes: history read failed")
        events = []
    undone = reversed_ids(events)
    days: dict[str, list] = {}
    for e in events:
        days.setdefault(e.at[:10], []).append({"what": e.summary, "when": clock(e.at),
                                               "undone": e.event_id in undone, "by_mia": e.source == "assistant"})
    today = now.date()
    return {"undoable": undoable, "history": [
        {"day": "Today" if d == today.isoformat() else "Yesterday" if d == (today - timedelta(days=1)).isoformat()
         else f"{date.fromisoformat(d):%a %b} {date.fromisoformat(d).day}", "events": rows}
        for d, rows in sorted(days.items(), reverse=True)], "history_days": HISTORY_DAYS}


def _describe_undo(context, params) -> str:
    """The sentence for `undo.last`: what will be put back; ActionError when there's nothing."""
    from core.person_settings import person_id

    undo = getattr(context, "undo", None)
    changes = undo.recent(person_id(context)) if undo is not None else []
    if not changes:
        raise ActionError("There's nothing of mine to undo right now.")
    said = _summaries(context, set(changes[0].events))
    return "Undo: " + (next((said[e] for e in changes[0].events if e in said), None) or label_words(changes[0].label))


def _undo(context, params) -> str:
    """Does `undo.last`: puts the newest change back, as "undo that" does. Its own writes are kept out of the undo
    log (a nested recording), so undoing never adds a change of its own."""
    from core.person_settings import person_id
    from core.undo_log import recording, undo_last

    with recording("undo", None):
        change = undo_last(context, person_id(context))
    if change is None:
        raise ActionError("There's nothing of mine to undo right now.")
    return f"Undone: {label_words(change.label)}."


UNDO_ACTIONS = {"undo.last": ActionType("undo.last", "Undo", {}, _describe_undo, _undo)}
ACTION_TYPES.update(UNDO_ACTIONS)
