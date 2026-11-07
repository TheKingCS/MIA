"""
core.life_note_actions
========================

What someone said they'd do, decided, want to try and set aside
(core/life_notes.py, DEC-0054) through the action contract
(core/actions.py): `life_note.done` (a promise kept, an idea tried) and
`life_note.forget`. The notes write through atomic_write_text, so "undo
that" takes either back. Said out loud: "I kept my promise to Sam",
"forget the idea about honey" (`life_notes.reply`).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _note(context, params) -> dict:
    """The note the params name, from this person's notes; ActionError when it isn't one of theirs."""
    found = _need(context, "life_notes").get(str(params.get("note_id") or ""))
    if found is None:
        raise ActionError("That isn't one of the things you asked me to keep.")
    return found


def _describe_done(context, params) -> str:
    """life_note.done's sentence to approve: the note in a line."""
    from core.life_notes import describe

    return f"Mark done: {describe(_note(context, params))}"


def _done(context, params) -> str:
    """life_note.done: mark the note done; a promise gets a "Nicely kept"."""
    from core.life_notes import describe

    note = _need(context, "life_notes").mark_done(_note(context, params)["id"])
    return f"Done: {describe(note)}." + (" Nicely kept." if note["kind"] == "commitment" else "")


def _describe_forget(context, params) -> str:
    """life_note.forget's sentence to approve."""
    from core.life_notes import describe

    return f"Forget {describe(_note(context, params))}"


def _forget(context, params) -> str:
    """life_note.forget: remove the note for good (undo brings it back)."""
    from core.life_notes import describe

    note = _note(context, params)
    _need(context, "life_notes").forget(note["id"])
    return f"Forgotten: {describe(note)}."


LIFE_NOTE_ACTIONS = {a.kind: a for a in (
    ActionType("life_note.done", "Mark done", {"note_id": "the promise, decision, idea or goal"}, _describe_done, _done,
               child_ok=True),
    ActionType("life_note.forget", "Forget it", {"note_id": "the promise, decision, idea or goal"}, _describe_forget,
               _forget, child_ok=True),
)}
ACTION_TYPES.update(LIFE_NOTE_ACTIONS)
