"""
core.ownership
================

Whose is it? (2026-10-01) In a shared household some things belong to
one person: the truck is Zac's, the sewing machine is Faith's, the
tractor is everyone's. A maintenance item (vehicle, tool, appliance)
can name its owner (`MaintenanceAsset.owner_profile_id`; None means
shared by the household).

What it changes:
- The item shows whose it is (Maintenance, the Assistant).
- Today (core/today.py) shows maintenance for your things and shared
  ones, not for someone else's truck.
- Rewards already credit the owner (core/rewards_manager.py).

Everyone in the household can still see and update everything: an owner
mark says whose it is, it doesn't hide it.
"""

from __future__ import annotations

from typing import Optional

from core.person_settings import person_id

SHARED_LABEL = "Shared (the household)"


def household_people(context) -> list:
    """The people an item here can belong to: the signed-in person's
    household (everyone on the device without households)."""
    profiles = getattr(context, "profiles", None)
    if profiles is None:
        return []
    households = getattr(context, "households", None)
    me = person_id(context)
    if households is not None and me:
        hid = households.household_of(me)
        return households.members(hid) if hid else []
    return profiles.list_profiles()


def owner_choices(context) -> list[tuple[str, Optional[str]]]:
    return [(SHARED_LABEL, None)] + [(p.name, p.profile_id) for p in household_people(context)]


def owner_name(context, owner_id: Optional[str]) -> Optional[str]:
    if not owner_id:
        return None
    profiles = getattr(context, "profiles", None)
    profile = profiles.get_profile(owner_id) if profiles is not None else None
    return profile.name if profile is not None else None


def possessive(context, owner_id: Optional[str]) -> str:
    """Pure-ish. "yours", "Faith's", or "shared"."""
    if not owner_id:
        return "shared"
    if owner_id == person_id(context):
        return "yours"
    name = owner_name(context, owner_id)
    return f"{name}'s" if name else "shared"


def is_for_me(context, owner_id: Optional[str]) -> bool:
    """Shared things and your own: what your Today list shows."""
    return not owner_id or owner_id == person_id(context) or owner_name(context, owner_id) is None


def resolve_owner(context, words: str) -> tuple[bool, Optional[str]]:
    """Pure-ish. (understood, owner id): "mine"/"me" -> you, "shared"/
    "everyone"/"the household" -> None, a household member's name -> them."""
    text = f" {(words or '').lower().strip()} "
    if any(w in text for w in (" mine ", " me ", " my ", " i ")):
        return True, person_id(context)
    if any(w in text for w in (" shared ", " everyone", " everybody", " household", " family", " ours ", " us ",
                                " nobody", " no one")):
        return True, None
    for person in household_people(context):
        first = person.name.lower().split()[0]
        if f" {person.name.lower()} " in text or f" {first} " in text or f" {first}'s " in text:
            return True, person.profile_id
    return False, None
