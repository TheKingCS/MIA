"""
core.web_conversations
========================

Past conversations on the web (the chat page, web/assistant.html; parity with the Qt Assistant's History): the
person's conversations with MIA, newest first, each with its title, when it was last added to and how many messages;
one opened to read; picking one back up so Talk continues it; and taking one out (the action `conversation.delete`,
undoable because the store writes through atomic_write_text).

Only what was kept is shown: off-the-record and private messages are never written (core/conversation_manager.py),
so they never appear here. Everything comes from the person's own conversations store (their view).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType

SHOWN = 60  # past conversations listed; older ones are still kept


def _manager(context):
    """The person's conversation store, or None."""
    return getattr(context, "conversations", None)


def history(context, current_id: str = "") -> dict:
    """The person's past conversations with something in them, newest first: id, title, when, how many messages, and
    which one Talk is in now."""
    manager = _manager(context)
    if manager is None:
        return {"available": False, "conversations": []}
    rows = [c for c in manager.all_conversations() if c.messages]
    return {"available": True, "total": len(rows), "conversations": [{
        "id": c.conversation_id, "title": c.title, "when": (c.updated_at or c.created_at or "")[:16],
        "count": len(c.messages), "current": c.conversation_id == current_id,
        "first": next((m.content[:90] for m in c.messages if m.role == "user"), "")} for c in rows[:SHOWN]]}


def one(context, conversation_id: str) -> Optional[dict]:
    """One conversation to read: its title and its kept messages (the person's and MIA's), or None."""
    manager = _manager(context)
    c = manager.get_conversation(conversation_id) if manager is not None else None
    if c is None:
        return None
    return {"id": c.conversation_id, "title": c.title, "when": (c.updated_at or "")[:16],
            "messages": [{"role": m.role, "content": m.content} for m in c.messages if m.role in ("user", "assistant")]}


def pick_up(context, conversation_id: str):
    """Marks a past conversation as just used (so a new turn continues it instead of starting fresh) and returns it;
    ValueError when it isn't the person's."""
    manager = _manager(context)
    c = manager.get_conversation(conversation_id) if manager is not None else None
    if c is None:
        raise ValueError("That conversation isn't here.")
    c.updated_at = datetime.now().isoformat(timespec="seconds")
    manager.save()
    return c


def _need(context, params):
    """The conversation the params name; ActionError when it isn't there."""
    manager = _manager(context)
    found = manager.get_conversation(str(params.get("conversation_id") or "")) if manager is not None else None
    if found is None:
        raise ActionError("That conversation isn't here.")
    return found


def _describe_delete(context, params) -> str:
    """The approval sentence for `conversation.delete`."""
    c = _need(context, params)
    return f"Delete the conversation “{c.title}” ({len(c.messages)} messages)"


def _delete(context, params) -> str:
    """Does `conversation.delete`; Undo brings it back."""
    c = _need(context, params)
    _manager(context).delete_conversation(c.conversation_id)
    return f"Deleted “{c.title}”. Undo brings it back."


CONVERSATION_ACTIONS = {a.kind: a for a in (
    ActionType("conversation.delete", "Delete", {"conversation_id": "the conversation"}, _describe_delete, _delete,
               child_ok=True),
)}
ACTION_TYPES.update(CONVERSATION_ACTIONS)
