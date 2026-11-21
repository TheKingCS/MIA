"""
core.lockdown
=============

The lockdown (WP-01, DEC-0254, Q-93 yes, REQ-IMP-007): one phrase, or the Lockdown button on Sign-ins and Security,
and MIA closes up until he signs in again with his password.

**What it does** (`engage`):
- every session of his ends (the web front end on any device, the desktop's own included) and every phone linked to
  this computer is unlinked (core/linked_devices.py): each signs in or links again with his password;
- the vaults lock: his saved passwords, the private journal, the mail check (each asks for its own key again);
- "stop everything" is put on with no end (core/stop.py): nothing she starts herself, no message she'd offer, no work
  in her lab, until it's lifted;
- it's written to the security log.

**What lifts it** (`lift`): only his password. Signing in with it (`/api/login`) lifts it; "carry on" doesn't
(core/stop.py refuses while a lockdown is on). Alarms, reminders he set and the safety floor go on as they do under
"stop everything".

**The phrase** (`recognise`): the whole message is "lockdown", "lock down", "lock everything (down)" or "lock it all
down", with "MIA" or "now" around it. Taken at the start of a turn, before the model, like "stop everything"; there's
deliberately no tool for it, so a misheard model call can never sign his phone out.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

KEY = "security.lockdown"  # the person's setting: {"since": ISO time} while a lockdown is on
VAULTS = ("passwords", "private_journal", "inbox_mail")  # AppContext fields whose store has lock()
_PHRASE = re.compile(r"^\s*(?:(?:hey\s+)?mia[,.!]?\s+)?(?:lock\s*down|lock\s+(?:it\s+)?(?:all|everything)(?:\s+down)?)"
                     r"(?:\s+(?:now|mia))?[\s.!]*$", re.IGNORECASE)


def recognise(prompt: str) -> bool:
    """Pure logic. Whether the whole message asks for a lockdown."""
    return bool(_PHRASE.match(str(prompt or "")))


def active(context) -> Optional[dict]:
    """The lockdown in force for this person ({"since"}), or None."""
    from core import person_settings

    try:
        value = person_settings.get(context, KEY, None)
    except Exception:  # noqa: BLE001 - a setting that can't be read is no lockdown
        return None
    return value if isinstance(value, dict) and value.get("since") else None


def _end_sessions(context, profile_id: str) -> int:
    """Ends every web session of this person on this computer's server (the desktop's own too); how many."""
    server = getattr(context, "phone_server", None)
    app = getattr(server, "_app", None)
    state = getattr(app, "state", None)
    sessions = getattr(state, "sessions", None)
    if not isinstance(sessions, dict):
        return 0
    ended = [token for token, who in list(sessions.items()) if who == profile_id]
    for token in ended:
        sessions.pop(token, None)
        for table in ("last_seen", "session_started"):
            getattr(state, table, {}).pop(token, None)
    return len(ended)


def engage(context, profile_id: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    """Locks MIA down for this person (see the module's opening). Returns what it did: {"sessions", "phones",
    "vaults"}. Each step is done even when another fails, and a failure is logged."""
    from core import linked_devices, person_settings, stop
    from core.undo_log import outside_undo

    now = now or datetime.now()
    who = profile_id or person_settings.person_id(context)
    done = {"sessions": 0, "phones": 0, "vaults": []}
    with outside_undo():  # a lockdown is never taken back by "undo that"
        person_settings.put(context, KEY, {"since": now.isoformat(timespec="seconds")})
    try:
        stop.stop_everything(context, None, now)
    except Exception:  # noqa: BLE001 - the rest still happens
        log.exception("Lockdown: couldn't stop everything.")
    try:
        done["sessions"] = _end_sessions(context, who) if who else 0
    except Exception:  # noqa: BLE001
        log.exception("Lockdown: couldn't end the sessions.")
    try:
        config = getattr(context, "config", None)
        done["phones"] = linked_devices.unlink_all(config, who) if config is not None and who else 0
    except Exception:  # noqa: BLE001
        log.exception("Lockdown: couldn't unlink the phones.")
    for name in VAULTS:
        vault = getattr(context, name, None)
        if vault is not None and hasattr(vault, "lock"):
            try:
                vault.lock()
                done["vaults"].append(name)
            except Exception:  # noqa: BLE001
                log.exception("Lockdown: couldn't lock %s.", name)
    book = getattr(context, "security_log", None)
    if book is not None:
        book.record("lockdown", who, "", f"{done['sessions']} sessions ended, {done['phones']} phones unlinked")
    log.warning("Lockdown is on for %s.", who)
    return done


def lift(context, profile_id: str, password: str) -> bool:
    """Lifts the lockdown when the password is his; whether it was lifted. A wrong password lifts nothing."""
    from core import person_settings, stop
    from core.undo_log import outside_undo

    profiles = getattr(context, "profiles", None)
    if profiles is None or not profiles.verify_password(profile_id, password):
        return False
    if active(context) is None:
        return True
    with outside_undo():
        person_settings.put(context, KEY, None)
    stop.carry_on(context)
    book = getattr(context, "security_log", None)
    if book is not None:
        book.record("lockdown_lifted", profile_id, "", "")
    log.warning("Lockdown is lifted for %s.", profile_id)
    return True


def report(done: dict) -> str:
    """Pure logic. What she says when the lockdown is on."""
    parts = []
    if done.get("sessions"):
        parts.append(f"{done['sessions']} sign-in{'s' if done['sessions'] != 1 else ''} ended")
    if done.get("phones"):
        parts.append(f"{done['phones']} phone{'s' if done['phones'] != 1 else ''} unlinked")
    if done.get("vaults"):
        parts.append("the vaults locked")
    what = (": " + ", ".join(parts)) if parts else ""
    return (f"Lockdown is on{what}. Everything of mine is stopped. Sign in with your password to lift it; until then "
            "alarms and the reminders you set still come.")


def handle(context, prompt: str) -> Optional[str]:
    """The turn pipeline's first question, before "stop everything": when the whole message asks for a lockdown, does
    it and returns what she says; else None."""
    if not recognise(prompt):
        return None
    return report(engage(context))
