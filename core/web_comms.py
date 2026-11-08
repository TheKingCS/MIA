"""
core.web_comms
================

Communications (DEC-0129, Zac 2026-11-08): one screen for what was spread
over four: the email drafts MIA wrote (she only drafts; an email goes when
the person presses Send, core/mail_send.py), the mailbox MIA reads for
receipts (core/inbox_mail.py), what MIA said on her own today and what she
held back (core/communication_gate.py), the daily limit and the kinds of
message on a break, the latest notifications, and the people to catch up
with (core/relationships_manager.py).

- `comms_page(context, now)`: the screen's data, read-only.
- `catch_up(people, today)` (pure): people with a way to reach them,
  longest since you last caught up first.
- Actions `comms.limit` (the daily limit; set_message_limit by voice) and
  `comms.resume` (bring back a kind of message on a break;
  resume_message_topic by voice), so undo covers both.

Sending, discarding and the mailbox's setup keep their own endpoints
(/api/email/drafts, /api/inbox/email): a password or passphrase never goes
through an action.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need

LATEST = 5
CATCH_UP = 6


def _days_since(iso: str, today: date) -> Optional[int]:
    """Days since an ISO date, None when there isn't one."""
    try:
        return (today - date.fromisoformat((iso or "")[:10])).days
    except ValueError:
        return None


def catch_up(people: list, today: date, limit: int = CATCH_UP) -> list[dict]:
    """Pure logic. The people you can write to (they have an email), longest since you last caught up first (never
    first of all): [{id, name, email, since: days or None}]."""
    rows = [{"id": p.person_id, "name": p.name, "email": p.email, "since": _days_since(p.last_contact, today)}
            for p in people if getattr(p, "email", "")]
    rows.sort(key=lambda r: (r["since"] is not None, -(r["since"] or 0), r["name"].lower()))
    return rows[:limit]


def _drafts(context) -> dict:
    """The open drafts (newest first) and whether Send can work here."""
    drafts = getattr(context, "email_drafts", None)
    if drafts is None:
        return {"available": False, "items": []}
    from core.email_drafts import as_dict

    items = sorted(drafts.open_drafts(), key=lambda d: d.created_at or "", reverse=True)
    return {"available": True, "items": [as_dict(d) for d in items]}


def _messages(context) -> dict:
    """What MIA said on her own today and what she held back, her daily limit, and the kinds of message on a break."""
    gate = getattr(context, "communication", None)
    if gate is None:
        return {"available": False}
    from core.communication_gate import ACT, DEFER, DROP

    entries = gate.entries_for_day()
    held = [{"title": e.get("title", ""), "message": e.get("message", ""), "reason": e.get("reason", ""),
             "waiting": e["action"] == DEFER} for e in entries if e["action"] in (DEFER, DROP)]
    paused = [{"topic": p["topic"], "label": p["label"], "until": f"{p['until']:%b %d}"} for p in gate.paused()]
    return {"available": True, "said_today": sum(1 for e in entries if e["action"] == ACT),
            "limit": int(gate.settings()["daily_budget"]), "held": held, "paused": paused}


def comms_page(context, now: Optional[datetime] = None) -> dict:
    """The Communications screen: drafts, the mailbox, MIA's messages, the latest notifications, people to catch up
    with."""
    from core.web_inbox import _email_status
    from core.web_notifications import notifications_page

    now = now or datetime.now()
    notes = notifications_page(context, now)
    people = getattr(context, "relationships", None)
    return {
        "drafts": _drafts(context),
        "mailbox": _email_status(context),
        "messages": _messages(context),
        "notifications": {"available": notes["available"], "unread": notes["unread"], "items": notes["items"][:LATEST]},
        "people": catch_up(people.all_people(), now.date()) if people is not None else [],
    }


def _gate(context):
    """The communication gate; ActionError without one."""
    gate = getattr(context, "communication", None)
    if gate is None:
        raise ActionError("Messages aren't managed on this device.")
    return gate


def _limit(context, params) -> str:
    """Does comms.limit: how many times a day MIA may speak up on her own."""
    try:
        wanted = int(float(params.get("count")))
    except (TypeError, ValueError):
        raise ActionError("How many times a day?") from None
    new = _gate(context).set_daily_budget(wanted)
    return f"At most {new} time{'s' if new != 1 else ''} a day on her own. Urgent things and answers don't count."


def _resume(context, params) -> str:
    """Does comms.resume: a kind of message on a break comes back."""
    gate = _gate(context)
    topic = str(params.get("topic") or "")
    match = next((p for p in gate.paused() if p["topic"] == topic), None)
    if match is None:
        raise ActionError("That isn't on a break.")
    gate.resume(topic)
    return f"MIA will tell you about {match['label']} again."


COMMS_ACTIONS = {a.kind: a for a in (
    ActionType("comms.limit", "Set", {"count": "times a day"},
               lambda c, p: f"Let MIA speak up on her own at most {p.get('count')} times a day", _limit),
    ActionType("comms.resume", "Bring Back", {"topic": "the kind of message"},
               lambda c, p: f"Let MIA tell you about {str(p.get('topic') or '').replace('_', ' ')} again", _resume),
)}
ACTION_TYPES.update(COMMS_ACTIONS)
