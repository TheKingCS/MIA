"""
core.web_changes
==================

Recent changes (2026-11-07; the design review's missing "Recent changes /
Undo history" screen): what MIA changed for the signed-in person lately,
newest first, from the undo log (core/undo_log.py: the last 20, kept in
memory since MIA started), each said in words with when and whether MIA
or the person did it. Only the newest can be undone, the same as "undo
that" (an older one would undo on top of what came after), so the page
offers Undo on that one: `undo_latest()`, the same call the quick command
makes. Served as /api/changes and /api/changes/undo; web/changes.html draws it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def _words(label: str) -> str:
    """Pure logic. A change's label in words: "add_expense" is "Add expense", "bill.pay" is "Bill pay"."""
    said = label.replace("_", " ").replace(".", " ").strip()
    return said[:1].upper() + said[1:]


def _when(at: str, now: datetime) -> str:
    """Pure logic. When it happened: "2:05 PM" today, else "Nov 6, 2:05 PM"."""
    try:
        when = datetime.fromisoformat(at)
    except (TypeError, ValueError):
        return ""
    clock = f"{when.hour % 12 or 12}:{when:%M %p}"
    return clock if when.date() == now.date() else f"{when:%b} {when.day}, {clock}"


def changes_page(context, now: Optional[datetime] = None) -> dict:
    """The page: the person's recent changes, newest first, each with what, when, who made it, and whether it's the
    one Undo takes back; {"available": False} without the undo log."""
    from core.person_settings import person_id

    undo = getattr(context, "undo", None)
    if undo is None:
        return {"available": False}
    now = now or datetime.now()
    changes = undo.recent(person_id(context))
    return {"available": True, "changes": [
        {"what": _words(c.label), "when": _when(c.at, now), "by": "MIA" if c.by == "mia" else "You",
         "latest": i == 0} for i, c in enumerate(changes)]}


def undo_latest(context) -> str:
    """Undoes the person's newest change (the same as "undo that") and says what was put back."""
    from core.person_settings import person_id
    from core.undo_log import undo_last

    change = undo_last(context, person_id(context))
    if change is None:
        return "There's nothing to undo."
    return f"Undone: {_words(change.label).lower()}."
