"""
core.assistant_notification_actions
=====================================

Notifications by voice (DEC-0125), for what the Notifications page shows:
"what are my notifications?" (the unread ones, newest first), "mark my
notifications read" (the same `notification.read_all` action as the page's
button) and "that was useful" (`notification.useful` on the latest message
MIA sent on her own, so her pace for that kind goes up, DEC-0171). Why one was sent, and muting a kind, were already voice tools
(core/assistant_undo_actions.py).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _list(context, arguments: dict) -> str:
    """Tool list_notifications: the unread notifications, newest first (five at most), or that there are none."""
    from core.web_notifications import notifications_page

    page = notifications_page(context)
    unread = [i for i in page["items"] if not i["read"]]
    if not unread:
        return "No new notifications."
    said = "; ".join(f"{i['title']} ({i['when']})" if i["when"] else i["title"] for i in unread[:5])
    more = f" And {len(unread) - 5} more." if len(unread) > 5 else ""
    return f"{len(unread)} new: {said}.{more}"


def _read(context, arguments: dict) -> str:
    """Tool mark_notifications_read: marks every notification read (notification.read_all)."""
    from core.actions import ACTION_TYPES, ActionError

    try:
        ACTION_TYPES["notification.read_all"].describe(context, {})
        return ACTION_TYPES["notification.read_all"].execute(context, {})
    except ActionError as problem:
        return str(problem)


def _useful(context, arguments: dict) -> str:
    """Tool mark_message_useful: the latest message MIA sent on her own was worth hearing (notification.useful)."""
    from core.actions import ACTION_TYPES, ActionError

    gate = getattr(context, "communication", None)
    last = gate.last_sent() if gate is not None else None
    notification_id = (last or {}).get("notification_id", "")
    if not notification_id:
        if last and gate.note_engagement(topic=last.get("topic", ""), how="opened"):
            return "Noted. I'll keep those coming."
        return "I haven't sent you anything on my own lately."
    try:
        return ACTION_TYPES["notification.useful"].execute(context, {"notification_id": notification_id})
    except ActionError:
        gate.note_engagement(notification_id=notification_id, how="opened")
        return "Noted. I'll keep those coming."


def register_notification_actions(registry) -> None:
    """Registers list_notifications, mark_notifications_read and mark_message_useful."""
    none = {"type": "object", "properties": {}, "required": []}
    registry.register(AssistantAction(
        name="list_notifications", domain="system",
        description="Read out the unread notifications, newest first.",
        parameters=none, handler=_list,
        trigger_phrases=("my notifications", "any notifications", "new notifications", "what notifications"),
        subjects=("notification",),
    ))
    registry.register(AssistantAction(
        name="mark_notifications_read", domain="system",
        description="Mark every notification read.",
        parameters=none, handler=_read,
        trigger_phrases=("mark my notifications read", "mark notifications read", "clear my notifications",
                         "mark them all read"),
        subjects=("notification",),
    ))
    registry.register(AssistantAction(
        name="mark_message_useful", domain="system",
        description="The last message MIA sent on her own was useful: she'll send that kind more.",
        parameters=none, handler=_useful,
        trigger_phrases=("that was useful", "that was helpful", "good tip", "thanks for telling me",
                         "keep telling me about that"),
        subjects=("notification", "message"),
    ))
