"""
core.assistant_notification_actions
=====================================

Notifications by voice (DEC-0125), for what the Notifications page shows:
"what are my notifications?" (the unread ones, newest first) and "mark my
notifications read" (the same `notification.read_all` action as the page's
button). Why one was sent, and muting a kind, were already voice tools
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


def register_notification_actions(registry) -> None:
    """Registers list_notifications and mark_notifications_read."""
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
