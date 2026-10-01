"""
core.child_accounts
=====================

Child accounts (2026-10-01): a young person in a household gets their own
MIA, set up and looked after by a parent (their guardian).

The rules, all in code (never left to the model):
- **Apps**: a child sees the ones in `CHILD_APPS` (learning, chores,
  missions, skills, music, notes, maps, recipes...). Money, bank,
  documents, files, the workshop, device tools and the Modules screen are
  closed ("ask a parent"), and their Settings shows only Switch User and
  Accessibility.
- **The Assistant** never offers a child the tools in
  `CHILD_BLOCKED_DOMAINS` (money, bank, business, household admin, device
  and security tools) and refuses them if asked; it's told it's talking
  with a child, to keep words simple and topics age-appropriate.
- **Safety**: the safety floor works the same and also tells a child to
  talk to a parent or another adult they trust right now.
- **Privacy**: a child's own things stay theirs (their journal too).
  Guardians can reset the child's password and, when it's time, make it a
  regular account.

Stored on the profile record: `child` (bool), `guardians` (profile ids).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.person_settings import person_id

# The apps a child can open (module ids). Everything else says "ask a parent".
CHILD_APPS = frozenset({
    "dashboard", "assistant", "character", "classroom", "household", "kitchen", "knowledge", "maps", "memories",
    "missions", "music", "navigation", "notes", "observations", "relationships", "skills", "workout", "greenhouse",
    "expeditions", "settings",
})

# Assistant tool domains a child is never offered.
CHILD_BLOCKED_DOMAINS = frozenset({
    "budget", "debts", "real_estate", "homestead_costs", "business_use", "business_tags", "ledger", "jobs",
    "products", "materials", "components", "security", "lab", "field_kit", "power", "toolbox", "inbox", "system",
    "ownership", "private_budget",
})

ASK_A_PARENT = "That one's for grown-ups. Ask a parent if you need it."


def _record(context, profile_id: Optional[str]) -> dict:
    config = getattr(context, "config", None)
    if config is None or not profile_id:
        return {}
    return config.get(f"profiles.{profile_id}") or {}


def is_child(context, profile_id: Optional[str] = None) -> bool:
    return bool(_record(context, profile_id or person_id(context)).get("child"))


def guardians_of(context, profile_id: str) -> list[str]:
    return list(_record(context, profile_id).get("guardians", []))


def children_of(context, guardian_id: str) -> list:
    profiles = getattr(context, "profiles", None)
    listed = profiles.list_profiles() if profiles is not None else []
    return [p for p in listed if guardian_id in guardians_of(context, p.profile_id)]


def age(birthday: Optional[str], today: Optional[date] = None) -> Optional[int]:
    """Pure logic. Whole years, or None without a birthday."""
    if not birthday:
        return None
    try:
        born = date.fromisoformat(birthday)
    except ValueError:
        return None
    today = today or date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def make_child(context, profile_id: str, guardian_ids: list[str]) -> bool:
    record = dict(_record(context, profile_id))
    if not record or not guardian_ids:
        return False
    record["child"] = True
    record["guardians"] = list(dict.fromkeys(guardian_ids))
    context.config.set(f"profiles.{profile_id}", record)
    context.config.save()
    context.events.publish("records.changed", action="child_account")
    return True


def make_adult(context, profile_id: str, guardian_id: str) -> bool:
    """A guardian turns a child account into a regular one."""
    if guardian_id not in guardians_of(context, profile_id):
        return False
    record = dict(_record(context, profile_id))
    record.pop("child", None)
    record.pop("guardians", None)
    context.config.set(f"profiles.{profile_id}", record)
    context.config.save()
    context.events.publish("records.changed", action="child_account")
    return True


def guardian_reset_password(context, child_id: str, guardian_id: str, guardian_password: str,
                            new_password: Optional[str]) -> bool:
    """A child forgot their password: a guardian (typing their own) sets a new one."""
    profiles = context.profiles
    if guardian_id not in guardians_of(context, child_id):
        return False
    if not profiles.verify_password(guardian_id, guardian_password or ""):
        return False
    return profiles.set_password(child_id, new_password or None)


def app_allowed(context, module_id: str) -> bool:
    return not is_child(context) or module_id in CHILD_APPS


def tool_allowed(context, domain: str) -> bool:
    return context is None or not is_child(context) or domain not in CHILD_BLOCKED_DOMAINS


def prompt_note(context) -> str:
    """For the Assistant's system message: who it's talking with."""
    if not is_child(context):
        return ""
    profiles = getattr(context, "profiles", None)
    profile = profiles.get_profile(person_id(context)) if profiles is not None else None
    years = age(getattr(profile, "birthday", None))
    who = f"a child, {years} years old" if years is not None else "a child"
    return (f"You are talking with {who}. Use simple, warm words and short sentences. Keep every topic suitable "
            "for a child. Never discuss money, bank accounts, or adult topics; for anything like that, or anything "
            "worrying, gently suggest they talk to a parent or another adult they trust.")
