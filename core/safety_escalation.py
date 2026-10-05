"""
core.safety_escalation
========================

When a child's message triggers the safety floor (Q-0002, approved by the
owner 2026-10-05, H-0011): the child gets the immediate safety reply
(core/safety_floor.py) and is told plainly that a parent who looks after
their account will be told; each guardian (core/child_accounts.py) gets
a notification straight away with the minimum: who, and when. No words
from the conversation, ever, and ordinary conversations and journals
stay private.

The rules, all in code (never decided by the model):
- **Direct**, never through the communication gate (it's a safety
  escalation, not a message MIA chose to send), and even when someone
  has switched notifications off.
- **Auditable:** recorded as a `safety_escalation` life event in the
  child's own history and in each guardian's own history. Never in the
  household's shared history, where other members would see it.
- **Not a flood:** at most one alert per guardian every
  `ALERT_SPACING_MINUTES`; every trigger is still recorded.

Known limit (H-0011's guardrail, to design separately): the guardian is
treated as the right person to tell. Cases where a guardian is
unavailable, implicated, or otherwise the wrong path need their own
design (Q-0012); this must not wait for it.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

ALERT_SPACING_MINUTES = 30
CHILD_NOTICE = ("A parent who looks after your account will be told that you needed this, so they can help. "
                "They won't see what you wrote.")

_lock = threading.Lock()
_last_alert: dict[tuple[str, str], float] = {}  # (child, guardian) -> when


def alert_text(child_name: str, when: datetime) -> tuple[str, str]:
    """Pure logic. The guardian's notification: who and when, nothing more."""
    clock = f"{when.hour % 12 or 12}:{when:%M %p}"
    return ("Safety alert", f"{child_name} was shown MIA's safety support message at {clock} on {when:%b} "
                            f"{when.day}. Please check in with them now. (MIA doesn't share what they wrote.)")


def _personal_log(context, profile_id: str):
    from core.life_events import PersonalLifeEventLog

    personal = getattr(context, "personal_data", None) or getattr(getattr(context, "_base", None),
                                                                 "personal_data", None)
    if personal is None:
        return None
    return PersonalLifeEventLog(context, personal.folder(profile_id))


def _guardian_notifications(context, guardian_id: str):
    personal = getattr(context, "personal_data", None) or getattr(getattr(context, "_base", None),
                                                                 "personal_data", None)
    if personal is None:
        return None
    return getattr(personal.view(guardian_id), "notifications", None)


def escalate(context, child_id: Optional[str], now: Optional[datetime] = None) -> int:
    """Tell the child's guardians. Returns how many were alerted now.
    Never raises: the child's safety reply must go out regardless."""
    from core import life_events
    from core.child_accounts import guardians_of

    if not child_id:
        return 0
    now = now or datetime.now()
    alerted = 0
    try:
        profiles = getattr(context, "profiles", None)
        child = profiles.get_profile(child_id) if profiles is not None else None
        child_name = getattr(child, "name", None) or "Your child"
        guardians = guardians_of(context, child_id)
        child_log = _personal_log(context, child_id)
        life_events.record(child_log, "safety_escalation", "The safety support message was shown; "
                           "a guardian was told", [f"profile:{child_id}"], {"guardians": len(guardians)},
                           profile_id=child_id, source="manual")
        title, message = alert_text(child_name, now)
        for guardian_id in guardians:
            life_events.record(_personal_log(context, guardian_id), "safety_escalation",
                               f"Safety alert about {child_name}", [f"profile:{child_id}"], {},
                               profile_id=guardian_id, source="manual")
            key = (child_id, guardian_id)
            with _lock:
                last = _last_alert.get(key, 0.0)
                if time.time() - last < ALERT_SPACING_MINUTES * 60:
                    continue
                _last_alert[key] = time.time()
            notifications = _guardian_notifications(context, guardian_id)
            if notifications is None:
                log.warning("Safety escalation: no way to notify guardian %s on this MIA.", guardian_id)
                continue
            if notifications.notify(title, message, level="critical", source="safety", always=True) is not None:
                alerted += 1
        log.info("Safety escalation for a child account: %d guardian(s) alerted.", alerted)
    except Exception:
        log.exception("Safety escalation failed; the child's safety reply still went out.")
    return alerted
