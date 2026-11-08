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

from core.logger import get_logger
from core.display_style import DEFAULT_STYLE, STYLES
from core.themes import DEFAULT_THEME, THEMES
from core.personality import HUMOR_DEFAULT
from core.startup_sounds import DEFAULT_STARTUP
from core.startup_sounds import options as startup_options

log = get_logger(__name__)

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class Setting:
    """One setting on the Settings screen: its person_settings key, group, label, kind (number, toggle, choice,
    text), default, help, range, options, whether a child may change it, and whether it's changed on its app's own
    screen instead.
    """
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
    own_screen: bool = False  # changed on its app's own screen (the vault asks Android first), not in Settings


def _currency_options() -> tuple:
    """The currency choices: the country's own, then each currency by code and sign."""
    from core.region import CURRENCIES

    return (("", "My country's"),) + tuple((code, f"{code} {sign.strip()}") for code, sign in CURRENCIES.items())


# The person's settings, in the PC app's words (modules/settings/module.py).
SETTINGS: tuple[Setting, ...] = (
    # DEC-0135 (Zac, 2026-11-08): the spatial look or the cards look, per person; "switch to the cards look" too.
    Setting("display.style", "Look", "Display style", "choice", DEFAULT_STYLE,
            "Spatial opens on the Nexus, each area a room. Cards opens on the Dashboard, each area's apps as cards. "
            "By device: spatial on the computer, cards on the phone. Or tell MIA: \"switch to the cards look\".",
            options=tuple((k, label) for k, (label, _line) in STYLES.items())),
    # DEC-0136: the theme, in both looks; "make it cyberpunk" too.
    Setting("display.theme", "Look", "Theme", "choice", DEFAULT_THEME,
            "Colours, type, materials and light, in either look. Or tell MIA: \"switch to the Y2K theme\".",
            options=tuple((t.id, t.name) for t in THEMES.values())),
    Setting("communication.daily_budget", "When MIA speaks up", "Messages per day, at most", "number", 5,
            "Her own messages (calendar, budget, check-ins, suggestions) are combined and limited per day. "
            "Urgent things, alarms you set and answers to you don't count.", low=1, high=20),
    Setting("journal.weekly_reflection", "When MIA speaks up", "Weekly journal reflection", "toggle", False,
            "If you journaled that week, MIA lets you know a reflection is ready. The notice never shows what "
            "you wrote."),
    Setting("journal.reflection_weekday", "When MIA speaks up", "Reflection day", "choice", 6,
            options=tuple(enumerate(WEEKDAYS))),
    # How funny she is (2026-11-07): the same setting "be funnier" / "no jokes for now" moves (set_humor), here too
    # so it can be changed without talking (DEC-0125).
    Setting("assistant.humor_level", "MIA", "How funny MIA is", "choice", HUMOR_DEFAULT,
            "Or tell her: \"be funnier\", \"tone down the jokes\", \"no jokes for now\".",
            options=(("off", "No jokes"), ("rare", "The odd joke"), ("sometimes", "Now and then, when it fits"),
                     ("often", "Often"), ("lots", "As funny as she can be"))),
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
    # Sound (DEC-0028 #11): chimes and fanfares on wins (web/sound.js), MIA's voice lines.
    Setting("sound.on", "Sound", "Sounds when you win", "toggle", True,
            "A chime for an objective, a fanfare for a level. Never for anything you didn't do."),
    Setting("sound.voice", "Sound", "MIA says a line when you win", "toggle", False,
            "Spoken out loud by this device's voice."),
    # The startup sound (2026-11-07): one for the whole computer (it plays before anyone signs in), or off.
    Setting("sound.startup", "Sound", "Startup sound", "choice", DEFAULT_STARTUP,
            "Plays as MIA starts on this computer. Press Play to hear one before choosing.",
            options=startup_options()),
    # Location quests (DEC-0028 #13, core/places.py): checked on this device only, while MIA is open.
    Setting("places.watch", "Location quests", "Notice when I arrive at my places", "toggle", False,
            "While MIA is open, this device checks where you are against your places. Where you are never leaves it."),
    Setting("vault.on", "Memory vault", "Keep my photos safe on the home computer", "toggle", False,
            "MIA copies this phone's photos and videos to your home computer, so the phone can let them go. "
            "MIA never deletes: it only offers, and Android asks you itself.", child_ok=False, own_screen=True),
    Setting("vault.wifi_only", "Memory vault", "Copy only on Wi-Fi", "toggle", True,
            "Off: it copies on mobile data too.", child_ok=False, own_screen=True),
    Setting("vault.keep_days", "Memory vault", "Keep recent photos on the phone (days)", "number", 30,
            "MIA only offers to free photos older than this.", low=0, high=365, child_ok=False, own_screen=True),
)
SETTINGS_BY_KEY = {s.key: s for s in SETTINGS}


def options_for(setting: Setting, context=None) -> tuple:
    """A setting's choices (the currency list for region.currency; for the theme, with a person, their own themes
    from the Theme Studio after the built-in ones, core/themes.py)."""
    if setting.key == "display.theme" and context is not None:
        from core.themes import choices

        return tuple(choices(context))
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
    """A setting's value said plainly: on or off, a choice's label, nobody for empty text, else the value."""
    if setting.kind == "toggle":
        return "on" if value else "off"
    if setting.kind == "choice":
        return next((label for option, label in options_for(setting) if str(option) == str(value)), str(value))
    if setting.kind == "text" and not value:
        return "nobody"
    return str(value)


def current_value(context, setting: Setting) -> Any:
    """A setting's value for this person (whether their budget is private comes from personal_data), or its
    default.
    """
    from core import person_settings

    if setting.key == "budget.private":
        personal = getattr(context, "personal_data", None)
        pid = person_settings.person_id(context)
        return bool(personal.has_private_budget(pid)) if personal is not None and pid else False
    value = person_settings.get(context, setting.key, setting.default)
    return setting.default if value is None else value


def _me(context):
    """The signed-in person's profile, or None."""
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
    """The Settings screen: the person's own settings, grouped (the theme's choices include their own themes), and
    the starter sets they can add."""
    from core.child_accounts import is_child

    child = bool(is_child(context))
    groups: dict[str, list] = {}
    for setting in SETTINGS:
        if (child and not setting.child_ok) or setting.own_screen:
            continue
        groups.setdefault(setting.group, []).append({
            "key": setting.key, "label": setting.label, "kind": setting.kind, "help": setting.help,
            "value": current_value(context, setting), "low": setting.low, "high": setting.high,
            "options": [{"value": v, "label": label} for v, label in options_for(setting, context)],
        })
    gate = getattr(context, "communication", None)
    breaks = []
    if gate is not None and hasattr(gate, "paused"):
        breaks = [{"topic": p["topic"], "label": p["label"], "until": str(p["until"])[:10]} for p in gate.paused()]
    from core.starter_actions import starters

    return {"groups": [{"title": title, "settings": items} for title, items in groups.items()],
            "breaks": breaks, "child": child, "starters": starters(context),
            "model_test": getattr(context, "local_models", None) is not None and not child,
            # DEC-0022: the home computer's bigger model, on the phone (core/home_link.py).
            "home_link": _home_link(context) if getattr(context, "local_models", None) is not None and not child else None}


def _home_link(context) -> dict:
    """The phone's home-link status with the two-way sync's status; when it fails it's logged and shown as not
    linked.
    """
    from core.home_link import status

    try:
        from core.sync import status as sync_status

        return {**status(context), "sync": sync_status(context)}  # two-way sync (core/sync.py)
    except Exception:
        log.exception("Settings: home link status failed")
        return {"linked": False, "url": "", "who": "", "reachable": False, "model": "", "level": "", "sync": None}


def find_interest(context, name: str) -> Optional[str]:
    """The skill category a name means (ignoring case), or None."""
    skills = getattr(context, "skills", None)
    known = skills.categories() if skills is not None else []
    return next((k for k in known if k.lower() == str(name).strip().lower()), None)
