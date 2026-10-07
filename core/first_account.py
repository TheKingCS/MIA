"""
core.first_account
====================

Making the first account on a device (2026-10-07, DEC-0019 Phase 2): the
phone app opens to "create your account" (name, email, password,
country, what you want MIA to help with) instead of making a person
called "You". Only when no account here has a password yet: after that,
people sign in, and more people join through households as before.

The phone test build made a placeholder ("You", no email, no password);
the first account takes it over, so whatever was tried keeps working.
The server only offers this where it's switched on (the phone app,
`app.state.allow_setup`), never on a computer's network-reachable server.
"""

from __future__ import annotations

from typing import Optional

from core.logger import get_logger
from core.profile_manager import AccountError, looks_like_email

log = get_logger(__name__)

MIN_PASSWORD = 6


def _placeholders(profiles) -> list:
    return [p for p in profiles.list_profiles() if not p.has_password and not p.email]


def setup_needed(context) -> bool:
    """Pure-ish. True while no account on this device has a password."""
    profiles = getattr(context, "profiles", None)
    return profiles is not None and not any(p.has_password for p in profiles.list_profiles())


def setup_page(context) -> dict:
    """What the "create your account" screen needs."""
    from core.region import REGIONS

    skills = getattr(context, "skills", None)
    return {
        "needed": setup_needed(context),
        "countries": [{"code": r.code, "name": r.name} for r in REGIONS.values()] + [{"code": "OTHER", "name": "Somewhere else"}],
        "interests": skills.categories() if skills is not None else [],
        "min_password": MIN_PASSWORD,
    }


def create_first_account(context, name: str, email: str, password: str, country: str = "US",
                         interests: Optional[list] = None):
    """Makes (or takes over the placeholder as) the device's first account.
    Returns (profile, recovery_code). Raises AccountError with a plain
    sentence for anything wrong; nothing is saved then."""
    from core import person_settings
    from core.region import REGIONS

    profiles = context.profiles
    if not setup_needed(context):
        raise AccountError("This MIA already has an account. Sign in instead.")
    name = (name or "").strip()
    email = (email or "").strip()
    if not name:
        raise AccountError("What should MIA call you?")
    if not looks_like_email(email):
        raise AccountError("That doesn't look like an email address.")
    if len(password or "") < MIN_PASSWORD:
        raise AccountError(f"Pick a password of at least {MIN_PASSWORD} characters.")
    country = (country or "US").upper()
    if country not in REGIONS and country != "OTHER":
        raise AccountError("Pick your country from the list.")
    taken = profiles.find_by_email(email)
    if taken is not None:
        raise AccountError("Someone on this MIA already signs in with that email.")

    placeholders = _placeholders(profiles)
    if len(placeholders) == 1:
        profile = placeholders[0]
        profiles.rename_profile(profile.profile_id, name)
        profiles.set_email(profile.profile_id, email)
        profiles.set_password(profile.profile_id, password)
        log.info("The first account took over the placeholder profile '%s'.", profile.profile_id)
    else:
        profile = profiles.create_profile(name, password=password, make_active=True, email=email)
    profiles.set_active_profile(profile.profile_id)
    personal = getattr(context, "personal_data", None)
    if personal is not None:
        personal.activate_current()
    person_settings.put(context, "region.country", country)
    known = set(getattr(getattr(context, "skills", None), "categories", lambda: [])())
    chosen = [i for i in (interests or []) if i in known]
    if chosen:
        profiles.set_interview_answers(profile.profile_id, chosen, "")
    code = profiles.issue_recovery_code(profile.profile_id)
    return profiles.get_profile(profile.profile_id), code
