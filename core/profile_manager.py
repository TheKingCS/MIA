"""
core.profile_manager
======================

Manages MIA user profiles — distinct from ConfigManager, which holds
app-wide settings (theme, kiosk mode, etc.) that apply regardless of
who's using the device. A "profile" is a person: their display name,
when they were created, an optional password, and (going forward) the
namespace their personal data lives under.

Why a separate service rather than folding this into ConfigManager:
profiles are a different kind of thing than settings — they're
records with an identity and a lifecycle (created, selected, deleted),
not key/value preferences. Keeping them in their own service means
future per-profile data isolation (journal entries, inventory, notes)
has one clear owner to ask "whose data is this."

Storage: profile records live in config.json under "profiles" (a
profile_id -> record mapping) and "system.active_profile_id". Each
profile's personal data directory is data/profiles/<profile_id>/,
reserved for future modules to use.

Password handling: passwords are never stored in plaintext or with
reversible encryption. Each protected profile stores a random salt and
a PBKDF2-HMAC-SHA256 hash of (salt + password). Verification recomputes
the hash and compares with hmac.compare_digest (constant-time, avoids
timing attacks). Using hashlib's built-in pbkdf2_hmac keeps this
dependency-free — no bcrypt/argon2 package needed for what a
personal-device profile lock requires.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DATA_PROFILES_DIR = Path(__file__).resolve().parent.parent / "data" / "profiles"
_PBKDF2_ITERATIONS = 200_000


def _hash_password(password: str) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for a new password."""
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return salt.hex(), hashed.hex()


@dataclass
class Profile:
    """A single user profile record."""

    profile_id: str
    name: str
    created_at: str
    password_hash: str = field(default="", repr=False)
    password_salt: str = field(default="", repr=False)
    # 2026-07-14 aesthetic pass part 5: lets the Assistant know and
    # celebrate the user's birthday (core.assistant_chat.build_user_context_block()),
    # at the user's explicit request. ISO "YYYY-MM-DD", set
    # conversationally via the set_birthday action
    # (core/application.py) rather than a dedicated form field — no
    # existing Settings UI edits profile fields at all yet (Settings
    # today only covers Appearance/Device Profile), and adding one
    # wasn't asked for.
    birthday: Optional[str] = None
    # 2026-07-18 design handoff (CCH.zip's Missions screen gamification):
    # lifetime-cumulative XP/credits, credited by
    # core/mission_manager.py's update_mission() on mission completion.
    # What *level* this corresponds to is derived on demand
    # (core/leveling.py's compute_level_progress()), never stored here —
    # same "derive it, don't persist a second copy that can drift"
    # philosophy MissionManager already uses for objective progress.
    total_xp: int = 0
    total_credits: int = 0

    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    @property
    def data_dir(self) -> Path:
        """
        This profile's reserved personal-data directory. Created on
        profile creation; modules that store per-user data (journal,
        inventory, etc., in later milestones) should write under here,
        keyed by this profile_id, rather than inventing their own
        per-user storage convention.
        """
        return _DATA_PROFILES_DIR / self.profile_id


class ProfileManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._migrate_legacy_user_if_needed()

    # ------------------------------------------------------------------
    # Migration
    # ------------------------------------------------------------------

    def _migrate_legacy_user_if_needed(self) -> None:
        """
        v0.1 stored a single "user.name" directly in config, with no
        concept of multiple profiles. If that key exists and no
        profiles have been created yet, convert it into this device's
        first profile automatically — so upgrading doesn't force
        re-running setup.
        """
        config = self.context.config
        legacy_name = config.get("user.name")
        existing_profiles = config.get("profiles", {})

        if legacy_name and not existing_profiles:
            log.info("Migrating legacy single-user config into a profile for '%s'.", legacy_name)
            profile = self._create_profile_record(legacy_name)
            config.set(f"profiles.{profile.profile_id}", {
                "name": profile.name,
                "created_at": profile.created_at,
            })
            config.set("system.active_profile_id", profile.profile_id)
            config.save()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_profile(self, name: str, password: Optional[str] = None, make_active: bool = True) -> Profile:
        """Create a new profile, optionally password-protected, and optionally activate it."""
        profile = self._create_profile_record(name)
        record = {"name": profile.name, "created_at": profile.created_at}

        if password:
            salt_hex, hash_hex = _hash_password(password)
            record["password_salt"] = salt_hex
            record["password_hash"] = hash_hex
            profile.password_salt = salt_hex
            profile.password_hash = hash_hex

        config = self.context.config
        config.set(f"profiles.{profile.profile_id}", record)
        if make_active:
            config.set("system.active_profile_id", profile.profile_id)
        config.save()

        self.context.events.publish("profile.created", profile_id=profile.profile_id, name=profile.name)
        log.info("Created profile '%s' (%s)%s", profile.name, profile.profile_id, " [password protected]" if password else "")
        return profile

    @staticmethod
    def _create_profile_record(name: str) -> Profile:
        profile_id = uuid.uuid4().hex[:8]
        profile = Profile(
            profile_id=profile_id,
            name=name,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        profile.data_dir.mkdir(parents=True, exist_ok=True)
        return profile

    def list_profiles(self) -> list[Profile]:
        """Return all known profiles, oldest first."""
        raw = self.context.config.get("profiles", {})
        profiles = [
            Profile(
                profile_id=pid,
                name=data.get("name", "Unknown"),
                created_at=data.get("created_at", ""),
                password_hash=data.get("password_hash", ""),
                password_salt=data.get("password_salt", ""),
                birthday=data.get("birthday"),
                total_xp=data.get("total_xp", 0),
                total_credits=data.get("total_credits", 0),
            )
            for pid, data in raw.items()
        ]
        return sorted(profiles, key=lambda p: p.created_at)

    def get_active_profile(self) -> Optional[Profile]:
        """Return the currently active profile, or None if none is set/exists."""
        active_id = self.context.config.get("system.active_profile_id")
        if not active_id:
            return None
        raw = self.context.config.get(f"profiles.{active_id}")
        if raw is None:
            return None
        return Profile(
            profile_id=active_id,
            name=raw.get("name", "Unknown"),
            created_at=raw.get("created_at", ""),
            password_hash=raw.get("password_hash", ""),
            password_salt=raw.get("password_salt", ""),
            birthday=raw.get("birthday"),
            total_xp=raw.get("total_xp", 0),
            total_credits=raw.get("total_credits", 0),
        )

    def set_active_profile(self, profile_id: str) -> None:
        """Switch the active profile and persist the choice."""
        config = self.context.config
        if config.get(f"profiles.{profile_id}") is None:
            log.warning("Attempted to activate unknown profile_id '%s'", profile_id)
            return
        config.set("system.active_profile_id", profile_id)
        config.save()
        self.context.events.publish("profile.switched", profile_id=profile_id)
        log.info("Switched active profile to '%s'", profile_id)

    def rename_profile(self, profile_id: str, new_name: str) -> bool:
        """Rename an existing profile. Returns False if the profile
        doesn't exist or new_name is blank after stripping."""
        new_name = new_name.strip()
        if not new_name:
            return False

        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to rename unknown profile_id '%s'", profile_id)
            return False

        old_name = raw.get("name", "Unknown")
        record = dict(raw)
        record["name"] = new_name
        config.set(f"profiles.{profile_id}", record)
        config.save()
        self.context.events.publish("profile.renamed", profile_id=profile_id, old_name=old_name, new_name=new_name)
        log.info("Renamed profile '%s' -> '%s'", old_name, new_name)
        return True

    def set_birthday(self, profile_id: str, birthday: str) -> bool:
        """Set a profile's birthday (ISO "YYYY-MM-DD"). Returns False if the profile doesn't exist."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to set birthday on unknown profile_id '%s'", profile_id)
            return False

        record = dict(raw)
        record["birthday"] = birthday
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("Birthday set for profile '%s'", profile_id)
        return True

    def add_xp(self, profile_id: str, amount: int) -> Optional[int]:
        """Credits `amount` XP to a profile's lifetime total. Returns the
        new total, or None if the profile doesn't exist. Publishes
        "profile.xp_changed" (2026-09-11, added alongside
        core.gamification.grant_xp()) so any UI showing a Level/XP
        readout outside the Missions module — e.g. gui/main_window.py's
        header badge — can refresh live instead of only updating the
        next time that screen happens to rebuild. A real, latent gap
        this closes: core.mission_manager.MissionManager's own reward
        crediting never published anything either, so even Mission-
        earned XP was invisible anywhere but the Missions module until
        it was reopened."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to add XP to unknown profile_id '%s'", profile_id)
            return None

        record = dict(raw)
        new_total = record.get("total_xp", 0) + amount
        record["total_xp"] = new_total
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("Profile '%s' earned %d XP (total now %d)", profile_id, amount, new_total)
        self.context.events.publish("profile.xp_changed", profile_id=profile_id)
        return new_total

    def add_credits(self, profile_id: str, amount: int) -> Optional[int]:
        """Credits `amount` credits to a profile's lifetime total. Returns
        the new total, or None if the profile doesn't exist. Publishes
        "profile.xp_changed" too — see add_xp()'s own docstring; shared
        event name since both are "this profile's stats changed,
        re-check whatever you're showing" from a UI listener's view."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to add credits to unknown profile_id '%s'", profile_id)
            return None

        record = dict(raw)
        new_total = record.get("total_credits", 0) + amount
        record["total_credits"] = new_total
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("Profile '%s' earned %d credits (total now %d)", profile_id, amount, new_total)
        self.context.events.publish("profile.xp_changed", profile_id=profile_id)
        return new_total

    def has_any_profiles(self) -> bool:
        return bool(self.context.config.get("profiles", {}))

    def needs_profile_selection(self) -> bool:
        """True if there's more than one profile and the user should be asked which one to use."""
        return len(self.list_profiles()) > 1

    # ------------------------------------------------------------------
    # Passwords
    # ------------------------------------------------------------------

    def set_password(self, profile_id: str, password: Optional[str]) -> bool:
        """
        Set (or, if password is None/empty, remove) a profile's password.
        Returns False if the profile doesn't exist.
        """
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to set password on unknown profile_id '%s'", profile_id)
            return False

        record = dict(raw)
        if password:
            salt_hex, hash_hex = _hash_password(password)
            record["password_salt"] = salt_hex
            record["password_hash"] = hash_hex
        else:
            record.pop("password_salt", None)
            record.pop("password_hash", None)

        config.set(f"profiles.{profile_id}", record)
        config.save()
        self.context.events.publish("profile.password_changed", profile_id=profile_id)
        log.info("Password %s for profile '%s'", "set" if password else "removed", profile_id)
        return True

    def verify_password(self, profile_id: str, password: str) -> bool:
        """
        Check `password` against the stored hash for `profile_id`.
        Returns True if the profile has no password set at all (nothing
        to verify against), False if the profile doesn't exist or the
        password is wrong.
        """
        raw = self.context.config.get(f"profiles.{profile_id}")
        if raw is None:
            return False

        stored_hash = raw.get("password_hash", "")
        if not stored_hash:
            return True  # no password set on this profile

        salt = bytes.fromhex(raw.get("password_salt", ""))
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS).hex()
        return hmac.compare_digest(computed, stored_hash)

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete_profile(self, profile_id: str, password: Optional[str] = None) -> bool:
        """
        Delete a profile. Refuses if it's the only remaining profile
        (a device must always have at least one) or if it's password
        protected and the wrong password (or none) was supplied.

        Does NOT erase the profile's data directory — it's renamed to
        an "_deleted_<id>_<timestamp>" archive folder instead, so an
        accidental or malicious deletion doesn't destroy real data.
        A future Backup/Restore or Settings feature can offer to purge
        archived profile data permanently; this method deliberately
        never does that itself.
        """
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to delete unknown profile_id '%s'", profile_id)
            return False

        if len(self.list_profiles()) <= 1:
            log.warning("Refusing to delete profile '%s' — it's the only remaining profile.", profile_id)
            return False

        if raw.get("password_hash") and not self.verify_password(profile_id, password or ""):
            log.warning("Incorrect password — refusing to delete profile '%s'.", profile_id)
            return False

        # Archive rather than erase.
        profile_data_dir = _DATA_PROFILES_DIR / profile_id
        if profile_data_dir.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            archive_dir = _DATA_PROFILES_DIR / f"_deleted_{profile_id}_{timestamp}"
            profile_data_dir.rename(archive_dir)
            log.info("Archived profile data dir to %s", archive_dir)

        all_profiles = dict(config.get("profiles", {}))
        all_profiles.pop(profile_id, None)
        config.set("profiles", all_profiles)

        if config.get("system.active_profile_id") == profile_id:
            config.set("system.active_profile_id", None)

        config.save()
        self.context.events.publish("profile.deleted", profile_id=profile_id)
        log.info("Deleted profile '%s' (data archived, not erased).", profile_id)
        return True
