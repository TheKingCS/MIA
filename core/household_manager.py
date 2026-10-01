"""
core.household_manager
========================

Households (2026-10-01, docs/ROADMAP.md "People and ownership"): MIA is
built for anyone, so nothing is shared between people unless they choose
it. Every new account starts in a household of its own. Two people share
the household things (calendar, kitchen, budget, maintenance, builds,
inventory, the document inbox...) only when the newer one *joins* the
other's household, and joining needs a current member's approval: they
type their own password on the device.

Each person's own things (conversations, memories, journals, notes,
workouts, classes) are never shared, household or not
(core/personal_data.py).

Storage: households in config "households.<id>" ({name, created_at,
first}); each profile record carries its "household_id".

Where a household's things live:
- The device's **first** household keeps the main `data/` folder, so an
  existing MIA keeps every file where it is. Upgrading puts all the
  profiles already on the device into that one household (they were
  sharing everything already).
- Every other household gets `data/households/<id>/`.

Leaving a household starts a new, empty one of your own; the shared
things stay with the household.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)


def households_dir() -> Path:
    """Next to the profiles folder (tests/conftest.py redirects both)."""
    import core.profile_manager as profile_manager_module

    return profile_manager_module._DATA_PROFILES_DIR.parent / "households"


class HouseholdManager:
    def __init__(self, context) -> None:
        self.context = context
        self._migrate_existing_profiles()
        context.events.subscribe("profile.created", self._on_profile_created)

    # ------------------------------------------------------------------

    @property
    def _config(self):
        return self.context.config

    def _all(self) -> dict:
        return dict(self._config.get("households", {}) or {})

    def _migrate_existing_profiles(self) -> None:
        """Once: the profiles already on the device become one household,
        the device's first."""
        if self._config.get("households") is not None:
            return
        profiles = self.context.profiles.list_profiles() if self.context.profiles is not None else []
        if not profiles:
            return
        owner = profiles[0]
        hid = self._new_household(f"{owner.name}'s household")
        for profile in profiles:
            self._set_household(profile.profile_id, hid)
        log.info("Put the %d existing profile(s) into one household (%s).", len(profiles), hid)

    def _new_household(self, name: str) -> str:
        households = self._all()
        hid = uuid.uuid4().hex[:8]
        households[hid] = {"name": name, "created_at": datetime.now().isoformat(timespec="seconds"),
                           "first": not any(h.get("first") for h in households.values())}
        self._config.set("households", households)
        self._config.save()
        return hid

    def _set_household(self, profile_id: str, hid: str) -> None:
        raw = self._config.get(f"profiles.{profile_id}")
        if raw is None:
            return
        record = dict(raw)
        record["household_id"] = hid
        self._config.set(f"profiles.{profile_id}", record)
        self._config.save()

    def _on_profile_created(self, profile_id: str = "", name: str = "", **_kwargs) -> None:
        self.household_of(profile_id)

    def _drop_if_empty(self, hid: str) -> None:
        """A household nobody belongs to anymore is forgotten (its folder,
        if it has one, is kept)."""
        if hid and not self.members(hid) and not self.is_first(hid):
            households = self._all()
            households.pop(hid, None)
            self._config.set("households", households)
            self._config.save()

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def household_of(self, profile_id: str) -> Optional[str]:
        """This person's household id; a new account gets one of its own."""
        profile = self.context.profiles.get_profile(profile_id) if profile_id else None
        if profile is None:
            return None
        if profile.household_id and profile.household_id in self._all():
            return profile.household_id
        hid = self._new_household(f"{profile.name}'s household")
        self._set_household(profile_id, hid)
        log.info("Profile %s starts in a household of its own (%s).", profile_id, hid)
        return hid

    def name(self, hid: str) -> str:
        return self._all().get(hid, {}).get("name", "Household")

    def rename(self, hid: str, name: str) -> bool:
        households = self._all()
        if hid not in households or not name.strip():
            return False
        households[hid] = {**households[hid], "name": name.strip()}
        self._config.set("households", households)
        self._config.save()
        return True

    def members(self, hid: str) -> list:
        return [p for p in self.context.profiles.list_profiles() if p.household_id == hid]

    def is_first(self, hid: str) -> bool:
        return bool(self._all().get(hid, {}).get("first"))

    def folder(self, hid: str) -> Optional[Path]:
        """Where this household's shared things live; None for the device's
        first household (the main data/ folder)."""
        if not hid or self.is_first(hid):
            return None
        return households_dir() / hid

    def list_households(self) -> list[tuple[str, str]]:
        return [(hid, data.get("name", "Household")) for hid, data in self._all().items()]

    def shares_with(self, profile_id: str) -> list:
        """The other people this person shares household things with."""
        hid = self.household_of(profile_id)
        return [p for p in self.members(hid) if p.profile_id != profile_id] if hid else []

    # ------------------------------------------------------------------
    # Joining and leaving
    # ------------------------------------------------------------------

    def join(self, profile_id: str, hid: str, approver_id: str, approver_password: str) -> bool:
        """Join `hid`, approved by a current member typing their password.
        A member without a password approves by being there (same as their
        own sign-in). Things the joiner had in their own household stay
        there; a brand-new account has nothing to lose."""
        if hid not in self._all() or self.household_of(profile_id) == hid:
            return False
        approver = self.context.profiles.get_profile(approver_id)
        if approver is None or approver.household_id != hid or approver.profile_id == profile_id:
            return False
        if not self.context.profiles.verify_password(approver_id, approver_password or ""):
            log.warning("Household join for %s refused: wrong approval password.", profile_id)
            return False
        old = self.household_of(profile_id)
        self._set_household(profile_id, hid)
        self._drop_if_empty(old)
        self.context.events.publish("household.changed", profile_id=profile_id, household_id=hid)
        log.info("Profile %s joined household %s (approved by %s).", profile_id, hid, approver_id)
        return True

    def leave(self, profile_id: str) -> Optional[str]:
        """Start a new, empty household of your own. The shared things stay
        with the household you left. None if you're its only member."""
        hid = self.household_of(profile_id)
        if hid is None or len(self.members(hid)) <= 1:
            return None
        profile = self.context.profiles.get_profile(profile_id)
        new = self._new_household(f"{profile.name}'s household")
        self._set_household(profile_id, new)
        self.context.events.publish("household.changed", profile_id=profile_id, household_id=new)
        log.info("Profile %s left household %s for a new one (%s).", profile_id, hid, new)
        return new
