"""
core.account_actions
======================

What the web's Profile and Settings screens change (2026-10-07,
core/web_account.py): your name, email, country and interests
(`profile.edit`), one of your own settings (`setting.set`), and ending a
break MIA took from a kind of message (`communication.resume`). All are
the person's own and undoable. Passwords and recovery codes are not
actions (server/app.py has their endpoints).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType


def _me(context):
    from core.web_account import _me as me

    profile = me(context)
    if profile is None:
        raise ActionError("Sign in first.")
    return profile


def _profile_changes(context, params) -> dict:
    """What would change, checked: {field: new value}. Raises ActionError."""
    from core.child_accounts import ASK_A_PARENT, is_child
    from core.profile_manager import looks_like_email
    from core.region import REGIONS, country_of
    from core.web_account import find_interest

    me = _me(context)
    changes: dict = {}
    if "name" in params:
        name = str(params["name"] or "").strip()
        if not name:
            raise ActionError("What should MIA call you?")
        if len(name) > 60:
            raise ActionError("That name is too long.")
        if name != me.name:
            changes["name"] = name
    if "email" in params:
        email = str(params["email"] or "").strip()
        if email.lower() != (me.email or "").lower():
            if is_child(context):
                raise ActionError(ASK_A_PARENT)
            if not looks_like_email(email):
                raise ActionError("That doesn't look like an email address.")
            taken = context.profiles.find_by_email(email)
            if taken is not None and taken.profile_id != me.profile_id:
                raise ActionError("Someone on this MIA already signs in with that email.")
            changes["email"] = email
    if "country" in params:
        country = str(params["country"] or "").strip().upper()
        if country not in REGIONS and country != "OTHER":
            raise ActionError("Pick your country from the list.")
        if country != country_of(context):
            changes["country"] = country
    if "interests" in params:
        raw = params["interests"]
        names = raw if isinstance(raw, list) else [n for n in str(raw or "").split(",") if n.strip()]
        chosen = []
        for name in names:
            found = find_interest(context, name)
            if found is None:
                raise ActionError(f"MIA doesn't know the area '{name}'.")
            if found not in chosen:
                chosen.append(found)
        if chosen != list(me.interests):
            changes["interests"] = chosen
    return changes


def _describe_profile(context, params) -> str:
    from core.region import region

    changes = _profile_changes(context, params)
    if not changes:
        raise ActionError("Nothing to change.")
    parts = []
    if "name" in changes:
        parts.append(f"your name to {changes['name']}")
    if "email" in changes:
        parts.append(f"your email to {changes['email']}")
    if "country" in changes:
        parts.append(f"your country to {region(changes['country']).name}")
    if "interests" in changes:
        parts.append("what MIA helps with to " + (", ".join(changes["interests"]) or "nothing in particular"))
    return "Change " + "; ".join(parts)


def _edit_profile(context, params) -> str:
    from core import person_settings

    me = _me(context)
    changes = _profile_changes(context, params)
    profiles = context.profiles
    if "name" in changes:
        profiles.rename_profile(me.profile_id, changes["name"])
    if "email" in changes:
        profiles.set_email(me.profile_id, changes["email"])
    if "country" in changes:
        person_settings.put(context, "region.country", changes["country"])
    if "interests" in changes:
        profiles.set_interview_answers(me.profile_id, changes["interests"], me.interview_notes)
    return "Your profile is updated."


def _setting(context, params):
    from core.child_accounts import ASK_A_PARENT, is_child
    from core.web_account import SETTINGS_BY_KEY, clean_setting

    _me(context)
    setting = SETTINGS_BY_KEY.get(str(params.get("key", "")))
    if setting is None:
        raise ActionError("That isn't one of your settings.")
    if not setting.child_ok and is_child(context):
        raise ActionError(ASK_A_PARENT)
    try:
        return setting, clean_setting(setting.key, params.get("value"))
    except ValueError as problem:
        raise ActionError(str(problem)) from None


def _describe_setting(context, params) -> str:
    from core.web_account import current_value, describe_value

    setting, value = _setting(context, params)
    if value == current_value(context, setting):
        raise ActionError(f"{setting.label} is already {describe_value(setting, value)}.")
    return f"Set {setting.label.lower()} to {describe_value(setting, value)}"


def _set_setting(context, params) -> str:
    from core import person_settings
    from core.web_account import describe_value

    setting, value = _setting(context, params)
    if setting.key == "budget.private":
        personal = getattr(context, "personal_data", None)
        if personal is None:
            raise ActionError("That isn't available on this MIA.")
        personal.set_private_budget(_me(context).profile_id, bool(value))
    else:
        person_settings.put(context, setting.key, value)
    return f"{setting.label}: {describe_value(setting, value)}."


def _paused(context, params) -> dict:
    gate = getattr(context, "communication", None)
    if gate is None:
        raise ActionError("That isn't available on this MIA.")
    topic = str(params.get("topic", ""))
    found = next((p for p in gate.paused() if p["topic"] == topic), None)
    if found is None:
        raise ActionError("MIA isn't taking a break from that.")
    return found


def _describe_resume(context, params) -> str:
    return f"Let MIA tell you about {_paused(context, params)['label']} again"


def _resume(context, params) -> str:
    found = _paused(context, params)
    context.communication.resume(found["topic"])
    return f"MIA can tell you about {found['label']} again."


ACCOUNT_ACTIONS: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("profile.edit", "Save", {"name": "optional", "email": "optional", "country": "optional: a country code",
                                        "interests": "optional: areas, comma-separated"},
               _describe_profile, _edit_profile, child_ok=True),
    ActionType("setting.set", "Save", {"key": "the setting", "value": "its new value"},
               _describe_setting, _set_setting, child_ok=True),
    ActionType("communication.resume", "Bring it back", {"topic": "the kind of message"},
               _describe_resume, _resume, child_ok=True),
)}
ACTION_TYPES.update(ACCOUNT_ACTIONS)
