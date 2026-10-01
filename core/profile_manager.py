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
import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.achievements import crossed_a_level, format_prestige_achieved, format_profile_level_up
from core.app_context import AppContext
from core.leveling import compute_prestige_level_progress, is_eligible_to_prestige, prestige_color_for_tier
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
    # Prestige (2026-09-14) — how many times this profile has actually
    # clicked "Prestige" (core.leveling's own module docstring has the
    # full design). A real choice, not derivable from total_xp alone —
    # a profile sitting at the level-100 ceiling hasn't necessarily
    # prestiged yet, and total_xp itself stays lifetime-cumulative and
    # uncapped regardless (existing invariant this doesn't touch).
    prestige_tier: int = 0
    # Rewards (2026-09-14) — real reward_ids this profile has actually
    # unlocked (core.rewards_manager.REWARD_DEFINITIONS). A real,
    # one-way state, not derivable from live stat values alone: once
    # unlocked, a reward stays unlocked even if the underlying stat
    # somehow later reads lower (a corrected reading, a data fix) —
    # same "a real choice/event, not a live computation" reasoning as
    # prestige_tier above.
    unlocked_reward_ids: list[str] = field(default_factory=list)
    # Profile-creation interview (2026-09-14, per the user's own Master
    # Vision handoff: "a kind of user interview upon profile creation
    # to get a feel of the user's life, hobbies, goals, and interests").
    # `interests` holds real core.skill_manager category names the user
    # picked (e.g. "Homestead", "Maker") — not free text, so downstream
    # code (Skills' own tab ordering) can match it directly without any
    # NLP. `interview_notes` is the free-text answer to "anything else
    # MIA should know about your goals or responsibilities" — read-only
    # color today; nothing parses it (see gui/profile_interview_dialog.py's
    # own docstring for what's deliberately not built yet). Both empty
    # for every profile created before this existed, or if the
    # interview was skipped — never required.
    interests: list[str] = field(default_factory=list)
    interview_notes: str = ""
    # Spatial/"any user" vision (2026-09-14) — interview_notes went
    # from "read-only color, nothing parses it" to a real input: the
    # first time this profile reaches Home with unprocessed notes,
    # gui/home_dashboard.py runs them through the exact same memory-
    # extraction pipeline a real chat message already goes through
    # (core.assistant_chat.build_memory_extraction_prompt()/
    # parse_extracted_memories()) — same "gather real facts, let the
    # LLM phrase them, never treat its output as authoritative without
    # parsing" discipline as everywhere else that pipeline is used.
    # This flag is the one-shot gate so a repeat Home construction
    # doesn't re-extract (and re-store near-duplicate) the same notes
    # every session — set True once extraction actually runs, even if
    # zero real facts came back, since "nothing to extract" is still a
    # real, final answer for these particular notes.
    interview_notes_extracted: bool = False
    # Accounts (2026-10-01, docs/ROADMAP.md "People and ownership"): the
    # email a person signs in with (unique on this device, compared
    # lowercase), a one-time recovery code (stored hashed, like the
    # password) and the household they belong to (core/household_manager.py).
    email: str = ""
    recovery_hash: str = field(default="", repr=False)
    recovery_salt: str = field(default="", repr=False)
    household_id: str = ""

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


def _profile_from_record(profile_id: str, data: dict) -> Profile:
    return Profile(
        profile_id=profile_id,
        name=data.get("name", "Unknown"),
        created_at=data.get("created_at", ""),
        password_hash=data.get("password_hash", ""),
        password_salt=data.get("password_salt", ""),
        birthday=data.get("birthday"),
        total_xp=data.get("total_xp", 0),
        total_credits=data.get("total_credits", 0),
        prestige_tier=data.get("prestige_tier", 0),
        unlocked_reward_ids=list(data.get("unlocked_reward_ids", [])),
        interests=list(data.get("interests", [])),
        interview_notes=data.get("interview_notes", ""),
        interview_notes_extracted=data.get("interview_notes_extracted", False),
        email=data.get("email", ""),
        recovery_hash=data.get("recovery_hash", ""),
        recovery_salt=data.get("recovery_salt", ""),
        household_id=data.get("household_id", ""),
    )


def normalize_email(email: Optional[str]) -> str:
    """Pure logic. Emails are compared lowercase, without spaces."""
    return (email or "").strip().lower()


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def looks_like_email(text: Optional[str]) -> bool:
    """Pure logic. Good enough to catch typos. MIA doesn't need to send a
    check email: the account lives on this device."""
    return bool(_EMAIL.match(normalize_email(text)))


# Recovery codes: easy to read aloud and copy by hand (no 0/O, 1/I/L).
_RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_recovery_code() -> str:
    """Pure logic (random). Four groups of four, e.g. "K7QM-2XRP-9HTA-WC4E"."""
    raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def _canonical_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


class AccountError(ValueError):
    """A sign-up or account change MIA refuses, with a message to show."""


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

    def create_profile(self, name: str, password: Optional[str] = None, make_active: bool = True,
                       email: Optional[str] = None) -> Profile:
        """Create a new profile, optionally password-protected, and optionally
        activate it. With an email, the person can sign in with it; a taken or
        malformed email raises AccountError before anything is saved."""
        email = self._checked_email(email) if email else ""
        profile = self._create_profile_record(name)
        record = {"name": profile.name, "created_at": profile.created_at}
        if email:
            record["email"] = profile.email = email

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
        profiles = [_profile_from_record(pid, data) for pid, data in raw.items()]
        return sorted(profiles, key=lambda p: p.created_at)

    def get_active_profile(self) -> Optional[Profile]:
        """Return the currently active profile, or None if none is set/exists."""
        active_id = self.context.config.get("system.active_profile_id")
        if not active_id:
            return None
        raw = self.context.config.get(f"profiles.{active_id}")
        if raw is None:
            return None
        return _profile_from_record(active_id, raw)

    def get_profile(self, profile_id: str) -> Optional[Profile]:
        """Look up any profile by id, active or not — a real, missing
        lookup this class never had before Rewards needed it (every
        other read path was either "the active one" or "all of
        them")."""
        return next((p for p in self.list_profiles() if p.profile_id == profile_id), None)

    def set_active_profile(self, profile_id: str) -> None:
        """Switch the active profile and persist the choice."""
        config = self.context.config
        if config.get(f"profiles.{profile_id}") is None:
            log.warning("Attempted to activate unknown profile_id '%s'", profile_id)
            return
        config.set("system.active_profile_id", profile_id)
        config.save()
        self.context.events.publish("profile.switched", profile_id=profile_id)

    def set_interview_answers(self, profile_id: str, interests: list[str], interview_notes: str) -> bool:
        """Records the profile-creation interview's real answers (see
        gui/profile_interview_dialog.py). Returns True if the profile
        existed and this actually saved, False otherwise — same
        idempotent-and-tells-you-so shape unlock_reward() already uses.
        A real, deliberate write, not something inferred: interests
        must be real core.skill_manager category names (not validated
        here — the dialog itself only ever offers real categories, so
        there's nothing to police)."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to save interview answers for unknown profile_id '%s'", profile_id)
            return False
        record = dict(raw)
        record["interests"] = list(interests)
        record["interview_notes"] = interview_notes
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("Saved interview answers for profile '%s': interests=%s", profile_id, interests)
        return True

    def mark_interview_notes_extracted(self, profile_id: str) -> bool:
        """The one-shot gate gui/home_dashboard.py sets once it's run
        this profile's interview_notes through memory extraction —
        same shape as set_interview_answers() above. Set regardless of
        whether any real fact actually came back; "nothing to extract"
        is still a final answer for these particular notes, not a
        reason to keep retrying every session."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to mark interview notes extracted for unknown profile_id '%s'", profile_id)
            return False
        record = dict(raw)
        record["interview_notes_extracted"] = True
        config.set(f"profiles.{profile_id}", record)
        config.save()
        return True

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
        old_total = record.get("total_xp", 0)
        new_total = old_total + amount
        record["total_xp"] = new_total
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("Profile '%s' earned %d XP (total now %d)", profile_id, amount, new_total)
        self.context.events.publish("profile.xp_changed", profile_id=profile_id)
        # Achievements/Milestones (2026-09-11) — see core/achievements.py's
        # own docstring; graceful no-op with no notifications service.
        # Prestige (2026-09-14) — uses compute_prestige_level_progress()
        # (capped at a maxed-out level 100), not the raw uncapped
        # compute_level_progress(), so a grant that crosses the
        # prestige ceiling reports "Level 100!" — the real level the
        # rest of the UI would show — never a "Level 101" that only
        # exists in the uncapped math and nowhere in this design.
        if self.context.notifications is not None:
            prestige_tier = record.get("prestige_tier", 0)
            leveled_up, new_level = crossed_a_level(
                old_total, new_total, lambda xp: compute_prestige_level_progress(xp, prestige_tier)
            )
            if leveled_up:
                title, message = format_profile_level_up(new_level)
                self.context.notifications.notify(title=title, message=message, level="info", source="achievements")
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

    def prestige(self, profile_id: str) -> Optional[int]:
        """A real, deliberate action — not automatic once a profile
        crosses the XP threshold (core.leveling's own module docstring
        explains why: reaching the ceiling should feel like earning a
        celebratory choice, not a silent rollover). Returns the new
        prestige_tier, or None if the profile doesn't exist or isn't
        actually eligible yet (checked here, not just trusted from the
        caller — same "don't trust the UI already gated this" stance
        every other real state-changing method in this codebase takes)."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to prestige unknown profile_id '%s'", profile_id)
            return None

        total_xp = raw.get("total_xp", 0)
        old_tier = raw.get("prestige_tier", 0)
        if not is_eligible_to_prestige(total_xp, old_tier):
            log.warning("Profile '%s' attempted to prestige without being eligible yet.", profile_id)
            return None

        new_tier = old_tier + 1
        record = dict(raw)
        record["prestige_tier"] = new_tier
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("Profile '%s' prestiged to tier %d (%s)", profile_id, new_tier, prestige_color_for_tier(new_tier))
        self.context.events.publish("profile.prestiged", profile_id=profile_id, new_tier=new_tier)
        # Same "profile stats changed, re-check whatever you're
        # showing" signal add_xp()/add_credits() already publish — a
        # prestige changes the displayed level/color just as much as
        # an XP change does.
        self.context.events.publish("profile.xp_changed", profile_id=profile_id)

        if self.context.notifications is not None:
            title, message = format_prestige_achieved(new_tier, prestige_color_for_tier(new_tier))
            self.context.notifications.notify(title=title, message=message, level="info", source="achievements")

        return new_tier

    def unlock_reward(self, profile_id: str, reward_id: str) -> bool:
        """Records `reward_id` as unlocked for this profile. Returns
        True if this actually changed anything (a real, new unlock),
        False if the profile doesn't exist or already had it — same
        idempotent-and-tells-you-so shape as
        core.insight_manager.InsightManager.create_insight_if_new(),
        so a caller (core.rewards_manager.RewardsManager) knows whether
        to actually fire a celebration notification or stay quiet.
        Deliberately no notification/formatting here — this class
        doesn't know a reward's name/icon/description, only that one
        got unlocked; RewardsManager owns that content."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            log.warning("Attempted to unlock a reward for unknown profile_id '%s'", profile_id)
            return False

        unlocked = list(raw.get("unlocked_reward_ids", []))
        if reward_id in unlocked:
            return False

        unlocked.append(reward_id)
        record = dict(raw)
        record["unlocked_reward_ids"] = unlocked
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("Profile '%s' unlocked reward '%s'", profile_id, reward_id)
        self.context.events.publish("profile.reward_unlocked", profile_id=profile_id, reward_id=reward_id)
        return True

    def has_any_profiles(self) -> bool:
        return bool(self.context.config.get("profiles", {}))

    def needs_profile_selection(self) -> bool:
        """True if there's more than one profile and the user should be asked which one to use."""
        return len(self.list_profiles()) > 1

    # ------------------------------------------------------------------
    # Accounts: email sign-in and recovery codes
    # ------------------------------------------------------------------

    def _checked_email(self, email: str, for_profile: Optional[str] = None) -> str:
        email = normalize_email(email)
        if not looks_like_email(email):
            raise AccountError("That doesn't look like an email address.")
        taken = self.find_by_email(email)
        if taken is not None and taken.profile_id != for_profile:
            raise AccountError("Someone on this MIA already signs in with that email.")
        return email

    def find_by_email(self, email: str) -> Optional[Profile]:
        wanted = normalize_email(email)
        if not wanted:
            return None
        return next((p for p in self.list_profiles() if normalize_email(p.email) == wanted), None)

    def find_for_sign_in(self, identifier: str) -> Optional[Profile]:
        """The profile someone means when signing in: their email, or (for
        profiles made before emails) their id or name, ignoring case."""
        text = (identifier or "").strip()
        if not text:
            return None
        if "@" in text:
            return self.find_by_email(text)
        by_id = self.get_profile(text)
        if by_id is not None:
            return by_id
        lowered = text.lower()
        named = [p for p in self.list_profiles() if p.name.strip().lower() == lowered]
        return named[0] if len(named) == 1 else None

    def set_email(self, profile_id: str, email: Optional[str]) -> bool:
        """Set (or, with an empty email, remove) a profile's sign-in email.
        Raises AccountError for a malformed or taken email."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            return False
        record = dict(raw)
        if email:
            record["email"] = self._checked_email(email, for_profile=profile_id)
        else:
            record.pop("email", None)
        config.set(f"profiles.{profile_id}", record)
        config.save()
        self.context.events.publish("profile.email_changed", profile_id=profile_id)
        log.info("Sign-in email %s for profile '%s'", "set" if email else "removed", profile_id)
        return True

    def sign_in(self, identifier: str, password: str) -> Optional[Profile]:
        """The profile, if `identifier` names one and the password is right.
        A profile with no password can't be signed into this way (the
        phone needs one; the desktop picks it from the list)."""
        profile = self.find_for_sign_in(identifier)
        if profile is None or not profile.has_password:
            return None
        return profile if self.verify_password(profile.profile_id, password) else None

    def issue_recovery_code(self, profile_id: str) -> Optional[str]:
        """Make a new recovery code, store only its hash, and return the code
        to show once. Any older code stops working."""
        config = self.context.config
        raw = config.get(f"profiles.{profile_id}")
        if raw is None:
            return None
        code = new_recovery_code()
        salt_hex, hash_hex = _hash_password(_canonical_code(code))
        record = dict(raw)
        record["recovery_salt"], record["recovery_hash"] = salt_hex, hash_hex
        config.set(f"profiles.{profile_id}", record)
        config.save()
        log.info("New recovery code issued for profile '%s'", profile_id)
        return code

    def has_recovery_code(self, profile_id: str) -> bool:
        profile = self.get_profile(profile_id)
        return bool(profile and profile.recovery_hash)

    def check_recovery_code(self, profile_id: str, code: str) -> bool:
        raw = self.context.config.get(f"profiles.{profile_id}")
        if raw is None or not raw.get("recovery_hash"):
            return False
        salt = bytes.fromhex(raw.get("recovery_salt", ""))
        computed = hashlib.pbkdf2_hmac("sha256", _canonical_code(code).encode("utf-8"), salt, _PBKDF2_ITERATIONS).hex()
        return hmac.compare_digest(computed, raw["recovery_hash"])

    def reset_password_with_code(self, identifier: str, code: str, new_password: str) -> Optional[str]:
        """Forgot your password: the recovery code sets a new one. Returns a
        fresh recovery code (the used one stops working), or None when the
        account or code is wrong. The private journal's passphrase is
        separate and can't be recovered this way, by design."""
        profile = self.find_for_sign_in(identifier)
        if profile is None or not new_password or not self.check_recovery_code(profile.profile_id, code):
            return None
        self.set_password(profile.profile_id, new_password)
        return self.issue_recovery_code(profile.profile_id)

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
