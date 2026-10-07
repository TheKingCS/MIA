"""
core.web_account
==================

The web's Profile and Settings screens (2026-10-07, Zac: the gear's
Profile and Settings). Profile is who you are: name, email, country,
what MIA helps with, household, password and recovery code. Settings is
how MIA behaves for you: the person's own settings from the PC app's
Settings (core/person_settings.py), nothing device-wide.

Changes go through actions (core/account_actions.py: `profile.edit`,
`setting.set`, `communication.resume`), so they're approved and undoable.
Passwords and recovery codes never do: they have their own endpoints
(server/app.py), so a password is never kept in a proposal or the undo
log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class Setting:
    key: str  # a core.person_settings key
    group: str
    label: str
    kind: str  # number | toggle | choice | text
    default: Any
    help: str = ""
    low: int = 0
    high: int = 0
    options: tuple = field(default=())  # ((value, label), ...) for a choice
    child_ok: bool = True


def _currency_options() -> tuple:
    from core.region import CURRENCIES

    return (("", "My country's"),) + tuple((code, f"{code} {sign.strip()}") for code, sign in CURRENCIES.items())


# The person's settings, in the PC app's words (modules/settings/module.py).
SETTINGS: tuple[Setting, ...] = (
    Setting("communication.daily_budget", "When MIA speaks up", "Messages per day, at most", "number", 5,
            "Her own messages (calendar, budget, check-ins, suggestions) are combined and limited per day. "
            "Urgent things, alarms you set and answers to you don't count.", low=1, high=20),
    Setting("journal.weekly_reflection", "When MIA speaks up", "Weekly journal reflection", "toggle", False,
            "If you journaled that week, MIA lets you know a reflection is ready. The notice never shows what "
            "you wrote."),
    Setting("journal.reflection_weekday", "When MIA speaks up", "Reflection day", "choice", 6,
            options=tuple(enumerate(WEEKDAYS))),
    Setting("assistant.ask_support_kind", "Support and safety", "When I sound worn down, ask what kind of support "
            "I want", "toggle", True, "Just listen, help figure it out, or remind me why. After the same answer "
            "three times, MIA uses it without asking."),
    Setting("assistant.safety.trusted_contact", "Support and safety", "Someone you trust", "text", "",
            "If you ever tell MIA you're in danger, she gives you your country's crisis line and emergency number, "
            "and names this person too. For example: my sister, and her number."),
    Setting("region.currency", "Money", "Currency", "choice", "", "Your country's, unless you pick another.",
            child_ok=False),
    Setting("budget.private", "Money", "Keep my money private", "toggle", False,
            "Your budget and bank accounts are kept apart from the household's.", child_ok=False),
)
SETTINGS_BY_KEY = {s.key: s for s in SETTINGS}


def options_for(setting: Setting) -> tuple:
    return _currency_options() if setting.key == "region.currency" else setting.options


def clean_setting(key: str, value: Any) -> Any:
    """Pure logic. The value to store, or ValueError with a plain sentence."""
    setting = SETTINGS_BY_KEY.get(key)
    if setting is None:
        raise ValueError("That isn't one of your settings.")
    if setting.kind == "toggle":
        return value not in (False, "false", "False", 0, "0", "", None, "off")
    if setting.kind == "number":
        try:
            number = int(str(value).strip())
        except ValueError:
            raise ValueError(f"{setting.label} needs a whole number.") from None
        if not setting.low <= number <= setting.high:
            raise ValueError(f"{setting.label}: pick from {setting.low} to {setting.high}.")
        return number
    if setting.kind == "choice":
        for option, _label in options_for(setting):
            if str(option) == str(value):
                return option
        raise ValueError(f"{setting.label}: pick one from the list.")
    text = str(value or "").strip()
    if len(text) > 200:
        raise ValueError(f"{setting.label} is too long.")
    return text


def describe_value(setting: Setting, value: Any) -> str:
    if setting.kind == "toggle":
        return "on" if value else "off"
    if setting.kind == "choice":
        return next((label for option, label in options_for(setting) if str(option) == str(value)), str(value))
    if setting.kind == "text" and not value:
        return "nobody"
    return str(value)


def current_value(context, setting: Setting) -> Any:
    from core import person_settings

    if setting.key == "budget.private":
        personal = getattr(context, "personal_data", None)
        pid = person_settings.person_id(context)
        return bool(personal.has_private_budget(pid)) if personal is not None and pid else False
    value = person_settings.get(context, setting.key, setting.default)
    return setting.default if value is None else value


def _me(context):
    from core.person_settings import person_id

    profiles = getattr(context, "profiles", None)
    pid = person_id(context)
    return profiles.get_profile(pid) if profiles is not None and pid else None


def profile_page(context) -> dict:
    """The Profile screen: who you are on this MIA."""
    from core.child_accounts import is_child
    from core.first_account import MIN_PASSWORD
    from core.region import REGIONS, country_of
    from core.web_progress import level_block

    me = _me(context)
    if me is None:
        return {"signed_in": False}
    households = getattr(context, "households", None)
    hid = households.household_of(me.profile_id) if households is not None else None
    others = []
    if households is not None and hid:
        others = [p.name for p in households.members(hid) if getattr(p, "profile_id", None) != me.profile_id]
    skills = getattr(context, "skills", None)
    return {
        "signed_in": True,
        "profile_id": me.profile_id,
        "name": me.name,
        "email": me.email,
        "country": country_of(context),
        "countries": [{"code": r.code, "name": r.name} for r in REGIONS.values()]
                     + [{"code": "OTHER", "name": "Somewhere else"}],
        "interests": list(me.interests),
        "interest_options": skills.categories() if skills is not None else [],
        "household": {"name": households.name(hid), "others": others} if hid else None,
        "has_password": me.has_password,
        "has_recovery_code": context.profiles.has_recovery_code(me.profile_id),
        "min_password": MIN_PASSWORD,
        "me": level_block(me),
        "child": bool(is_child(context)),
        "since": (me.created_at or "")[:10],
    }


def settings_page(context) -> dict:
    """The Settings screen: the person's own settings, grouped."""
    from core.child_accounts import is_child

    child = bool(is_child(context))
    groups: dict[str, list] = {}
    for setting in SETTINGS:
        if child and not setting.child_ok:
            continue
        groups.setdefault(setting.group, []).append({
            "key": setting.key, "label": setting.label, "kind": setting.kind, "help": setting.help,
            "value": current_value(context, setting), "low": setting.low, "high": setting.high,
            "options": [{"value": v, "label": label} for v, label in options_for(setting)],
        })
    gate = getattr(context, "communication", None)
    breaks = []
    if gate is not None and hasattr(gate, "paused"):
        breaks = [{"topic": p["topic"], "label": p["label"], "until": str(p["until"])[:10]} for p in gate.paused()]
    return {"groups": [{"title": title, "settings": items} for title, items in groups.items()],
            "breaks": breaks, "child": child}


def find_interest(context, name: str) -> Optional[str]:
    skills = getattr(context, "skills", None)
    known = skills.categories() if skills is not None else []
    return next((k for k in known if k.lower() == str(name).strip().lower()), None)
