"""
core.play_actions
===================

Recreation (core/recreation.py, DEC-0098) through the action contract
(core/actions.py): `play.log` (a game or sport played) and `play.delete`.
The log writes through atomic_write_text, so "undo that" takes it back.
Children play too: both are child-safe.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _describe_log(context, params) -> str:
    what = " ".join(str(params.get("what") or "").split())
    if not what:
        raise ActionError("What did you play?")
    minutes = float(params.get("minutes") or 0)
    people = [p for p in params.get("with") or [] if str(p).strip()]
    return f"Log {what}" + (f", {minutes:g} min" if minutes else "") + (f", with {', '.join(people)}" if people else "")


def _log(context, params) -> str:
    entry = _need(context, "recreation").log(params.get("what", ""), params.get("minutes") or 0, params.get("effort"),
                                             params.get("with") or [], params.get("date") or None)
    asked = "" if entry["effort_said"] else " How hard was it, 1 to 10? Say \"it was a 7\" next time and I'll count it."
    return (f"Logged {entry['what']}" + (f", {entry['minutes']:g} min" if entry["minutes"] else "")
            + (f": training load {entry['load']:g}." if entry["minutes"] else ". How long did you play?") + asked)


def _entry(context, params) -> dict:
    found = next((e for e in _need(context, "recreation").entries if e["id"] == str(params.get("entry_id", ""))), None)
    if found is None:
        raise ActionError("That game isn't in your log.")
    return found


def _describe_delete(context, params) -> str:
    return f"Take {_entry(context, params)['what']} on {_entry(context, params)['date']} out of your log"


def _delete(context, params) -> str:
    _need(context, "recreation").delete(_entry(context, params)["id"])
    return "Taken out."


PLAY_ACTIONS = {a.kind: a for a in (
    ActionType("play.log", "Log it", {"what": "the game or sport", "minutes": "how long", "effort": "1 to 10, or easy "
               "to brutal", "with": "who played", "date": "when (default today)"}, _describe_log, _log, child_ok=True),
    ActionType("play.delete", "Take it out", {"entry_id": "the entry"}, _describe_delete, _delete, child_ok=True),
)}
ACTION_TYPES.update(PLAY_ACTIONS)
