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
- **Undo by time** (UI-3): a time ("this afternoon") and, if he likes, a
  subject ("the greenhouse") propose `history.undo`, whose approval card
  lists exactly which changes go back (core/change_history.py keeps every
  change for 30 days, across restarts); each goes back whole or not at all,
  and only where nothing changed it since.

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
    """The Recent Changes screen: the undoable changes (newest first, the first one undoable), the times Undo By Time
    offers (`when_choices`, UI-3), and the last fortnight's history by day, each line saying whether MIA did it
    (her proposal he approved, or a standing yes she ran on her own)."""
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
                                               "undone": e.event_id in undone, "by_mia": e.source in ("assistant", "mia")})
    today = now.date()
    return {"undoable": undoable, "when_choices": [{"id": i, "name": n} for i, n in WHEN_CHOICES], "history": [
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


# Undo by time and subject (UI-3, core/change_history.py): "this afternoon", optionally "the greenhouse".
WHEN_CHOICES = (("last hour", "The last hour"), ("this morning", "This morning"), ("this afternoon", "This afternoon"),
                ("today", "Today"), ("yesterday", "Yesterday"), ("this week", "This week"))


def _history_found(context, params):
    """The changes `history.undo` would put back: (the person, the changes, the time in words)."""
    from core import change_history
    from core.person_settings import person_id

    when = " ".join(str(params.get("when") or "today").split())[:40]
    start, end = change_history.window(when)
    who = person_id(context)
    return who, change_history.find(who, start, end, str(params.get("what") or "")[:80]), when


def _describe_history_undo(context, params) -> str:
    """The sentence for `history.undo`: exactly which changes, when, will be put back; ActionError when none."""
    from core import change_history

    _who, found, when = _history_found(context, params)
    if not found:
        about = str(params.get("what") or "").strip()
        raise ActionError(f"I didn't change anything{' to ' + about if about else ''} {when}.")
    return (f"Undo {len(found)} change{'s' if len(found) != 1 else ''} from {when}, newest first: "
            + change_history.say(found) + ". Anything changed again since is left as it is")


def _history_undo(context, params) -> str:
    """Does `history.undo`: each change put back whole, newest first, where nothing changed it since; says what was
    put back and what was left and why. Its own writes aren't a new change."""
    from core import change_history
    from core.undo_log import recording

    who, found, when = _history_found(context, params)
    if not found:
        raise ActionError(f"I didn't change anything {when}.")
    with recording("undo", None):
        done = change_history.undo(context, who, found)
    said = []
    if done["undone"]:
        said.append(f"Put back {len(done['undone'])}: " + change_history.say(done["undone"]) + ".")
    for entry, why in done["left"]:
        said.append(f"Left \"{entry.what}\": {why}.")
    return " ".join(said) or "Nothing could be put back."


UNDO_ACTIONS = {"undo.last": ActionType("undo.last", "Undo", {}, _describe_undo, _undo),
                "history.undo": ActionType("history.undo", "Undo These",
                                           {"when": "a time: this afternoon, today, the last hour, yesterday...",
                                            "what": "optional: what the changes were about"},
                                           _describe_history_undo, _history_undo)}
ACTION_TYPES.update(UNDO_ACTIONS)
