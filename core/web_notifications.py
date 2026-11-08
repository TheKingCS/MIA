"""
core.web_notifications
========================

Notifications on the web (the screens review's missing notifications,
docs/design/CORE_SCREENS_REVIEW.md section 3; DEC-0125). Each notification
(core/notification_manager.py), newest first: its title and message, a tone
for its level (amber for a warning, red only for a real error: DEC-0014),
where it came from, when, and whether it's read. A message MIA sent on her
own (through the communication gate) also says why, in the gate's own words
(core/message_reasons.explain), so "why did you tell me that?" has an answer
on the screen too.

Changes are actions: `notification.read_all` and `notification.dismiss`
(dismissing one on purpose teaches the gate, as on the desktop). The same by
voice in core/assistant_notification_actions.py. The web only draws.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.web_changes import when_words

TONES = {"warning": "attention", "error": "bad", "critical": "bad", "success": "ok"}


def tone_of(level: str) -> str:
    """Pure logic. A level's tone on the screen: attention, bad, ok, or "" for plain information."""
    return TONES.get((level or "").lower(), "")


def notifications_page(context, now: Optional[datetime] = None) -> dict:
    """The Notifications screen: each notification newest first with its tone, source, when, read or not, and why
    MIA sent it when she sent it on her own; how many are unread."""
    from core.message_reasons import explain

    now = now or datetime.now()
    book = getattr(context, "notifications", None)
    if book is None:
        return {"available": False, "items": [], "unread": 0}
    gate = getattr(context, "communication", None)
    sent = {}
    if gate is not None:
        try:
            sent = {e["notification_id"]: e for e in gate.entries_since("") if e.get("notification_id")}
        except Exception:
            sent = {}
    items = [{"id": n.notification_id, "title": n.title, "message": n.message, "tone": tone_of(n.level),
              "source": n.source.replace("_", " "), "when": when_words(n.created_at or "", now), "read": n.read,
              "why": explain(sent[n.notification_id]) if n.notification_id in sent else ""}
             for n in sorted(book.list_all(), key=lambda n: n.created_at or "", reverse=True)]
    return {"available": True, "items": items, "unread": sum(1 for i in items if not i["read"])}


def _describe_read_all(context, params) -> str:
    """The sentence for `notification.read_all`; ActionError when nothing is unread."""
    count = _need(context, "notifications").unread_count()
    if not count:
        raise ActionError("Everything's already read.")
    return f"Mark {count} notification{'s' if count != 1 else ''} read"


def _read_all(context, params) -> str:
    """Does `notification.read_all`."""
    _need(context, "notifications").mark_all_read()
    return "All read."


def _one(context, params):
    """The notification named by notification_id, or ActionError."""
    found = next((n for n in _need(context, "notifications").list_all()
                  if n.notification_id == str(params.get("notification_id") or "")), None)
    if found is None:
        raise ActionError("That notification isn't here any more.")
    return found


def _dismiss(context, params) -> str:
    """Does `notification.dismiss`: takes it off the list on purpose (the communication gate learns from it)."""
    found = _one(context, params)
    _need(context, "notifications").dismiss(found.notification_id)
    return f"Dismissed “{found.title}”."


NOTIFICATION_ACTIONS = {k.kind: k for k in (
    ActionType("notification.read_all", "Mark All Read", {}, _describe_read_all, _read_all),
    ActionType("notification.dismiss", "Dismiss", {"notification_id": "the notification"},
               lambda c, p: f"Dismiss “{_one(c, p).title}”", _dismiss),
)}
ACTION_TYPES.update(NOTIFICATION_ACTIONS)
