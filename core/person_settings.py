"""
core.person_settings
======================

Settings that belong to a person, not the device (2026-10-01, accounts):
how many messages MIA may send you a day, the weekly journal reflection,
whether she asks what kind of support you want (and what you usually
pick), your trusted contact for the safety floor, and which apps you
see first (core/focus_presets.py).

Kept on the profile record, `profiles.<id>.settings`, under the same key
names the device config used. The person is the context's own
(`context.profile_id` on a phone turn's view, core/personal_data.py) or
whoever is signed in. The device's first account keeps any value that
was set before settings were per person; everyone else starts from the
defaults, so nobody inherits someone else's trusted contact.
"""

from __future__ import annotations

from typing import Any, Optional

PERSONAL_SETTINGS = (
    "communication.daily_budget",
    "communication.min_spacing_minutes",
    "communication.repeat_days",
    "journal.weekly_reflection",
    "journal.reflection_weekday",
    "system.last_journal_reflection_date",
    "assistant.ask_support_kind",
    "assistant.support_choices",
    "assistant.safety.trusted_contact",
    "apps.focus",
    "apps.featured",
    "apps.hidden",
    "setup.questions_done",
    "email.send.address",
    "email.send.host",
    "email.send.port",
    "email.send.security",
    "region.country",
    "region.currency",
    "budget.private",
    "display.text_size",
    "display.high_contrast",
)


def person_id(context) -> Optional[str]:
    own = getattr(context, "profile_id", None)
    if isinstance(own, str) and own:
        return own
    get_active = getattr(getattr(context, "profiles", None), "get_active_profile", None)
    active = get_active() if callable(get_active) else None
    return getattr(active, "profile_id", None) if active is not None else None


def _is_first_account(context, profile_id: str) -> bool:
    profiles = getattr(context, "profiles", None)
    listed = profiles.list_profiles() if profiles is not None else []
    return bool(listed) and sorted(listed, key=lambda p: p.created_at or "")[0].profile_id == profile_id


def get(context, key: str, default: Any = None) -> Any:
    config = getattr(context, "config", None)
    if config is None:
        return default
    profile_id = person_id(context)
    if key not in PERSONAL_SETTINGS or profile_id is None:
        return config.get(key, default)
    record = config.get(f"profiles.{profile_id}") or {}
    own = record.get("settings", {}) or {}
    if key in own:
        return own[key]
    return config.get(key, default) if _is_first_account(context, profile_id) else default


def put(context, key: str, value: Any) -> None:
    config = context.config
    profile_id = person_id(context)
    if key not in PERSONAL_SETTINGS or profile_id is None or config.get(f"profiles.{profile_id}") is None:
        config.set(key, value)
    else:
        record = dict(config.get(f"profiles.{profile_id}"))
        record["settings"] = {**(record.get("settings") or {}), key: value}
        config.set(f"profiles.{profile_id}", record)
    config.save()
