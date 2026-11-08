"""
core.web_directions
=====================

My Directions (web/directions.html, DEC-0141/0143): the standing directions the person is steering their life by, the
values MIA holds in mind on every turn and gently encourages (core/direction.py). The screen shows each direction in
the person's own words with how MIA encourages it and the short nudges she may raise now and then; today's seed (a
concrete little thing to make or do toward them, core/whimsy.py, the same each day); and one thing they could already
go and do right now (core/capability_reminders.py), both from real state and never invented.

Every change is the person's own act through the action system, so each is approved and undoable:

- `direction.add`: a new direction (its name, the value in their words, optionally how to encourage it and nudges).
- `direction.edit`: its words changed.
- `direction.pause` / `direction.resume`: held out of MIA's view for a while, or back in.
- `direction.remove`: let go for good (the file comes back with Undo).

`screen(context)` is what `/api/directions` serves. Nothing here is hard-coded about anyone: an empty book shows how to
set the first one.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

FIELDS = [
    {"name": "title", "label": "Its name", "type": "text", "required": True},
    {"name": "statement", "label": "In your own words", "type": "textarea", "required": True},
    {"name": "encourage", "label": "How MIA should encourage it", "type": "textarea"},
    {"name": "nudges", "label": "Little nudges she can raise now and then, one per line", "type": "textarea"},
]
MAX_DIRECTIONS = 12


def _book(context):
    """The person's DirectionBook, or None on a MIA without one."""
    return getattr(context, "direction", None)


def _nudges(value) -> list:
    """Pure logic. Nudges from a list or from text with one per line (blank lines dropped)."""
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value or "").splitlines()
    return [str(n).strip() for n in items if str(n).strip()][:12]


def roll_for(day: date, salt: str = "") -> float:
    """Pure logic. A steady 0-1 number for the day, so the screen's seed stays the same all day."""
    digest = hashlib.sha256(f"{day.isoformat()}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def todays_seed(context, today: Optional[date] = None) -> str:
    """Today's seed toward the person's active directions (core/whimsy.a_seed, with what's on the workshop shelf), or
    "" when no direction is active or none fits."""
    from core import whimsy

    book = _book(context)
    if book is None:
        return ""
    today = today or date.today()
    blobs = [f"{d.title} {d.statement}" for d in book.active()]
    materials = []
    if getattr(context, "materials", None) is not None:
        try:
            materials = [m.name for m in context.materials.all_materials()]
        except Exception:  # noqa: BLE001 - the shelf is a nice-to-have here
            materials = []
    return whimsy.a_seed(blobs, materials, today.month, roll_for(today, "seed"))


def right_now(context, today: Optional[date] = None) -> str:
    """One thing the person could already go and do (core/capability_reminders), or "" when there's nothing true to
    point to."""
    from core import capability_reminders

    today = today or date.today()
    return capability_reminders.a_reminder(capability_reminders.on_hand(context), roll_for(today, "now"))


def screen(context, today: Optional[date] = None) -> dict:
    """My Directions: the directions (in force first, then paused), today's seed, one thing within reach, the form."""
    book = _book(context)
    if book is None:
        return {"available": False}
    today = today or date.today()
    rows = sorted(book.directions, key=lambda d: (not d.active, d.created_at))
    return {
        "available": True,
        "directions": [{"id": d.direction_id, "title": d.title, "statement": d.statement, "encourage": d.encourage,
                        "nudges": list(d.nudges), "active": d.active, "since": (d.created_at or "")[:10],
                        "values": {"title": d.title, "statement": d.statement, "encourage": d.encourage,
                                   "nudges": "\n".join(d.nudges)}} for d in rows],
        "in_force": len(book.active()),
        "seed": todays_seed(context, today),
        "right_now": right_now(context, today),
        "forms": {"direction": {"fields": FIELDS}},
        "max": MAX_DIRECTIONS,
    }


def _need_book(context):
    """The book, or ActionError on a MIA without one."""
    book = _book(context)
    if book is None:
        raise ActionError("Directions aren't set up on this MIA.")
    return book


def _need(context, params):
    """The direction the params name; ActionError when it isn't there."""
    found = _need_book(context).get(str(params.get("direction_id") or ""))
    if found is None:
        raise ActionError("That direction isn't one of yours.")
    return found


def _words(params, field: str, what: str) -> str:
    """A required text param, tidied; ActionError when it's empty."""
    value = " ".join(str(params.get(field) or "").split()) if field == "title" else str(params.get(field) or "").strip()
    if not value:
        raise ActionError(what)
    return value


def _describe_add(context, params) -> str:
    """The approval sentence for `direction.add`; ActionError when it can't be done."""
    book = _need_book(context)
    title = _words(params, "title", "What should this direction be called?")[:60]
    _words(params, "statement", "Say the direction in your own words.")
    if len(book.directions) >= MAX_DIRECTIONS:
        raise ActionError(f"You have {MAX_DIRECTIONS} directions. Let one go first.")
    if any(d.title.lower() == title.lower() for d in book.directions):
        raise ActionError(f"You already have a direction called {title}.")
    return f"Set the direction {title}: MIA keeps it in mind and encourages it"


def _add(context, params) -> str:
    """Does `direction.add`: the new direction, in force."""
    _describe_add(context, params)
    d = _need_book(context).add(_words(params, "title", "")[:60], _words(params, "statement", "")[:600],
                                str(params.get("encourage") or "").strip()[:400], _nudges(params.get("nudges")))
    return f"{d.title} is one of your directions now. MIA will lean that way when it fits."


def _describe_edit(context, params) -> str:
    """The approval sentence for `direction.edit`."""
    found = _need(context, params)
    if "title" in params:
        _words(params, "title", "A direction needs a name.")
    if "statement" in params:
        _words(params, "statement", "Say the direction in your own words.")
    return f"Change the words of {found.title}"


def _edit(context, params) -> str:
    """Does `direction.edit`: only the words given change."""
    found = _need(context, params)
    _describe_edit(context, params)
    try:
        d = _need_book(context).edit(
            found.direction_id,
            title=_words(params, "title", "")[:60] if "title" in params else None,
            statement=str(params["statement"]).strip()[:600] if "statement" in params else None,
            encourage=str(params["encourage"]).strip()[:400] if "encourage" in params else None,
            nudges=_nudges(params["nudges"]) if "nudges" in params else None)
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"{d.title} is changed."


def _describe_pause(context, params) -> str:
    """The approval sentence for `direction.pause`."""
    found = _need(context, params)
    if not found.active:
        raise ActionError(f"{found.title} is already paused.")
    return f"Pause {found.title}: MIA stops leaning that way until you resume it"


def _pause(context, params) -> str:
    """Does `direction.pause`."""
    found = _need(context, params)
    _need_book(context).set_active(found.direction_id, False)
    return f"{found.title} is paused."


def _describe_resume(context, params) -> str:
    """The approval sentence for `direction.resume`."""
    found = _need(context, params)
    if found.active:
        raise ActionError(f"{found.title} is already in force.")
    return f"Resume {found.title}"


def _resume(context, params) -> str:
    """Does `direction.resume`."""
    found = _need(context, params)
    _need_book(context).set_active(found.direction_id, True)
    return f"{found.title} is back in force."


def _describe_remove(context, params) -> str:
    """The approval sentence for `direction.remove`."""
    return f"Let go of the direction {_need(context, params).title}"


def _remove(context, params) -> str:
    """Does `direction.remove`."""
    found = _need(context, params)
    _need_book(context).remove(found.direction_id)
    return f"Let go of {found.title}. Undo brings it back."


def find(context, words: str):
    """The direction whose name or words best match what was said (a voice tool's lookup), or None."""
    book = _book(context)
    words = " ".join(str(words or "").lower().split())
    if book is None or not words:
        return None
    for d in book.directions:
        if d.title.lower() == words:
            return d
    hits = [d for d in book.directions if words in d.title.lower() or d.title.lower() in words
            or words in d.statement.lower()]
    return hits[0] if hits else None


DIRECTION_ACTIONS = {a.kind: a for a in (
    ActionType("direction.add", "Set It", {"title": "its name", "statement": "the value in your own words",
                                          "encourage": "optional: how MIA should encourage it",
                                          "nudges": "optional: little nudges, a list or one per line"},
               _describe_add, _add, child_ok=True),
    ActionType("direction.edit", "Change", {"direction_id": "the direction", "title": "optional", "statement": "optional",
                                           "encourage": "optional", "nudges": "optional"},
               _describe_edit, _edit, child_ok=True),
    ActionType("direction.pause", "Pause", {"direction_id": "the direction"}, _describe_pause, _pause, child_ok=True),
    ActionType("direction.resume", "Resume", {"direction_id": "the direction"}, _describe_resume, _resume, child_ok=True),
    ActionType("direction.remove", "Let Go", {"direction_id": "the direction"}, _describe_remove, _remove, child_ok=True),
)}
ACTION_TYPES.update(DIRECTION_ACTIONS)
