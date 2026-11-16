"""
core.shelf_actions
====================

The shelf's changes (UI-4, core/shelf.py) on the action contract in core/actions.py:

- `shelf.keep`: put a capture on the person's shelf for a number of days (a week when not said). Its parameters are
  the capture's own fields, checked again by `core.ual.Capture.from_dict`, so a keep from the selection menu, a drop
  or voice is the same.
- `shelf.remove`: take one thing off.
- `shelf.clear`: take everything off.

All three only change the person's own shelf, and "undo that" takes each back. Nothing here reads what's kept.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _capture(params):
    """The capture in the parameters, checked; ActionError when there's nothing in it."""
    from core.ual import Capture, UalError

    try:
        return Capture.from_dict(params)
    except UalError as problem:
        raise ActionError(str(problem)) from None


def _days_said(params) -> str:
    """'for a week', or 'for N days', for the sentence."""
    from core.shelf import KEEP_DAYS, _days

    days = _days(params.get("days"))
    return "for a week" if days == KEEP_DAYS == 7 else f"for {days} day{'s' if days != 1 else ''}"


def _describe_keep(context, params) -> str:
    """The sentence the approval card shows for `shelf.keep`."""
    from core.shelf import ShelfEntry

    capture = _capture(params)
    label = ShelfEntry(entry_id="", text=capture.text, files=capture.files, source_app=capture.source_app,
                       url=capture.url, title=capture.title).label()
    return f"Keep \"{label}\" on your shelf {_days_said(params)}"


def _keep(context, params) -> str:
    """Does `shelf.keep` and says what happened."""
    from core.shelf import ShelfError, shelf_of

    try:
        shelf_of(context).keep(_capture(params), params.get("days"))
    except ShelfError as problem:
        raise ActionError(str(problem)) from None
    return f"It's on your shelf {_days_said(params)}."


def _entry(context, params):
    """The entry the parameters name; ActionError when it isn't on the shelf."""
    from core.shelf import shelf_of

    wanted = str(params.get("entry_id") or "")
    hit = next((e for e in shelf_of(context).entries() if e.entry_id == wanted), None)
    if hit is None:
        raise ActionError("That isn't on your shelf any more.")
    return hit


def _describe_remove(context, params) -> str:
    """The sentence the approval card shows for `shelf.remove`."""
    return f"Take \"{_entry(context, params).label()}\" off your shelf"


def _remove(context, params) -> str:
    """Does `shelf.remove` and says what happened."""
    from core.shelf import shelf_of

    shelf_of(context).remove(_entry(context, params).entry_id)
    return "Taken off your shelf."


def _describe_clear(context, params) -> str:
    """The sentence the approval card shows for `shelf.clear`; ActionError when the shelf is already empty."""
    from core.shelf import shelf_of

    count = len(shelf_of(context).entries())
    if not count:
        raise ActionError("Your shelf is already empty.")
    return f"Take everything off your shelf ({count} thing{'s' if count != 1 else ''})"


def _clear(context, params) -> str:
    """Does `shelf.clear` and says what happened."""
    from core.shelf import shelf_of

    count = shelf_of(context).clear()
    return f"Your shelf is clear ({count} taken off)."


_CAPTURE = {"text": "what was selected", "files": "optional: the files' names", "source_app": "optional: the app",
            "url": "optional", "title": "optional", "device": "optional", "missing": "optional: what wasn't captured",
            "kind": "optional: text, url, code, file or image", "days": "optional: how many days to keep it"}

for _a in (
    ActionType("shelf.keep", "Keep On My Shelf", _CAPTURE, _describe_keep, _keep),
    ActionType("shelf.remove", "Take Off", {"entry_id": "the shelf entry"}, _describe_remove, _remove),
    ActionType("shelf.clear", "Clear My Shelf", {}, _describe_clear, _clear),
):
    ACTION_TYPES[_a.kind] = _a
