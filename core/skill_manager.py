"""
core.skill_manager
=====================

"My Hero's Path" — a skill-tree layer underneath core/gamification.py's
existing XP system, added 2026-09-11 at the user's own explicit request
to turn real activity across MIA's modules into RPG-style character
progression, NOT a replacement for the profile-wide Level/Missions
system already built (docs/ROADMAP.md's 2026-07-14 through 2026-09-11
entries) — a Skill levels up independently, alongside it, credited by
the same core.gamification.grant_xp() call every existing hook already
uses (via its new `skill_weights` parameter).

Two separate concerns, two separate files (deliberately NOT one):

- SKILL DEFINITIONS (data/skill_definitions.json) are the taxonomy —
  what skills exist, their category, and their prerequisite_skill_ids.
  This file is meant to be hand-edited directly to add, remove, split,
  merge, or reorganize skills without touching any code — the user's
  own explicit requirement. SkillManager only ever READS this file; it
  never writes definitions.
- SKILL PROGRESS (data/skill_progress.json) is real per-profile state —
  how much XP a profile has earned in each skill. SkillManager owns
  this file the same way every other core/*_manager.py owns its data
  file (load/save, dataclasses, to_dict/from_dict).

A skill's level is NEVER stored, only its cumulative total_xp — level
is derived on every read via core.skill_leveling.compute_skill_level_
progress(), the same "derive it, don't persist a second copy that can
drift" philosophy core/leveling.py's profile-wide Level and
core/mission_manager.py's trip_duration_hours/task_done objectives
already use. A skill's "unlocked" state (are its prerequisites met) is
likewise derived at read time, never stored as a separate flag.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.achievements import crossed_a_level, format_skill_level_up, format_skill_unlocked
from core.app_context import AppContext
from core.logger import get_logger
from core.skill_leveling import capability_status_for_level, compute_skill_level_progress

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SKILL_DEFINITIONS_FILE = _DATA_DIR / "skill_definitions.json"
_SKILL_PROGRESS_FILE = _DATA_DIR / "skill_progress.json"
_SKILL_XP_LOG_FILE = _DATA_DIR / "skill_xp_log.json"
# Pattern Insights slice 4 (2026-09-14) — "skill momentum" needs a real
# recent-vs-prior XP comparison, which total_xp/last_touched can't
# answer (a cumulative total and a single latest timestamp can't tell
# you HOW MUCH was earned in the last 7 days vs the 7 before that).
# Retention is generous relative to that window on purpose — capped so
# a long-running kiosk device's log file doesn't grow unbounded (same
# concern core/activity_log_manager.py's own docstring states), not
# tuned tightly to today's one consumer.
_XP_LOG_MAX_AGE_DAYS = 90


def _event_date(timestamp: str) -> Optional[date]:
    """Pure logic — testable without Qt. None for blank/unparseable —
    same "no evidence" stance as core.skill_patterns._last_touched_date."""
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp).date()
    except ValueError:
        return None


@dataclass
class SkillDefinition:
    skill_id: str
    name: str
    category: str
    description: str = ""
    icon: str = ""
    # A skill with no prerequisites is always unlocked. Otherwise every
    # listed skill_id must have SOME xp (any real progress at all, not
    # a specific level) before this skill counts as unlocked — see
    # SkillManager.is_unlocked(). Can name skills in other categories
    # (e.g. "robotics" requires both a Technology skill and a Maker
    # skill) — the taxonomy is a graph, not one tree per category.
    prerequisite_skill_ids: list[str] = field(default_factory=list)
    tier: int = 1

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "icon": self.icon,
            "prerequisite_skill_ids": list(self.prerequisite_skill_ids),
            "tier": self.tier,
        }

    @staticmethod
    def from_dict(data: dict) -> "SkillDefinition":
        return SkillDefinition(
            skill_id=data["skill_id"],
            name=data.get("name", data["skill_id"]),
            category=data.get("category", "General"),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            prerequisite_skill_ids=list(data.get("prerequisite_skill_ids", [])),
            tier=data.get("tier", 1),
        )


@dataclass
class SkillProgress:
    profile_id: str
    skill_id: str
    total_xp: int = 0
    # Pattern Insights slice 3 (2026-09-14) — "when was this skill last
    # trained," a real gap: XP is granted from many places (Missions,
    # Workout, Kitchen, Budget, Maintenance, Project, Classroom, all
    # through the one shared core.gamification.grant_xp() -> this
    # class's own add_skill_xp() choke point), so deriving "last
    # touched" from any ONE of those sources (e.g. completed Missions
    # alone) would be wrong — it'd read as "decline" for someone
    # actively engaged through a different activity type entirely.
    # This is the one place persisting a real timestamp is correct
    # rather than a "derive it" violation: there's no other single
    # authoritative source to derive it from. Blank for every skill
    # touched before this field existed — see core/skill_patterns.py's
    # own handling of that case.
    last_touched: str = ""

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id, "skill_id": self.skill_id,
            "total_xp": self.total_xp, "last_touched": self.last_touched,
        }

    @staticmethod
    def from_dict(data: dict) -> "SkillProgress":
        return SkillProgress(
            profile_id=data["profile_id"],
            skill_id=data["skill_id"],
            total_xp=data.get("total_xp", 0),
            last_touched=data.get("last_touched", ""),
        )


@dataclass
class SkillXpEvent:
    """One real XP grant, kept as its own timestamped event rather than
    folded into SkillProgress — Pattern Insights slice 4 (skill
    momentum) needs to compare how much was earned in a recent window
    vs the window before it, which a cumulative total_xp and a single
    last_touched can't answer. See _XP_LOG_MAX_AGE_DAYS above for why
    this doesn't grow unbounded."""

    profile_id: str
    skill_id: str
    amount: int
    timestamp: str  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id, "skill_id": self.skill_id,
            "amount": self.amount, "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "SkillXpEvent":
        return SkillXpEvent(
            profile_id=data["profile_id"], skill_id=data["skill_id"],
            amount=data.get("amount", 0), timestamp=data.get("timestamp", ""),
        )


class SkillManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._definitions: dict[str, SkillDefinition] = {}
        self._progress: dict[tuple[str, str], SkillProgress] = {}
        self._xp_log: list[SkillXpEvent] = []
        self._load_definitions()
        self._load_progress()
        self._load_xp_log()

    # ------------------------------------------------------------------
    # Definitions — read-only from this class's own perspective
    # ------------------------------------------------------------------

    def _load_definitions(self) -> None:
        if not _SKILL_DEFINITIONS_FILE.exists():
            log.info("No skill_definitions.json found — no skills registered yet.")
            return
        try:
            raw = json.loads(_SKILL_DEFINITIONS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load skill_definitions.json — no skills registered.")
            return
        for entry in raw.get("skills", []):
            definition = SkillDefinition.from_dict(entry)
            self._definitions[definition.skill_id] = definition

    def all_skills(self) -> list[SkillDefinition]:
        return list(self._definitions.values())

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        return self._definitions.get(skill_id)

    def categories(self) -> list[str]:
        """Distinct categories present in the current taxonomy, derived
        live rather than maintained as a separate list — same pattern
        as core.script_library_manager.ScriptLibraryManager.categories()."""
        return sorted({d.category for d in self._definitions.values()})

    def skills_in_category(self, category: str) -> list[SkillDefinition]:
        return [d for d in self._definitions.values() if d.category == category]

    # ------------------------------------------------------------------
    # Progress — owned, persisted
    # ------------------------------------------------------------------

    def _load_progress(self) -> None:
        if not _SKILL_PROGRESS_FILE.exists():
            return
        try:
            raw = json.loads(_SKILL_PROGRESS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load skill_progress.json — starting with no progress.")
            return
        for entry in raw.get("progress", []):
            progress = SkillProgress.from_dict(entry)
            self._progress[(progress.profile_id, progress.skill_id)] = progress

    def _save_progress(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"progress": [p.to_dict() for p in self._progress.values()]}
        _SKILL_PROGRESS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_xp_log(self) -> None:
        if not _SKILL_XP_LOG_FILE.exists():
            return
        try:
            raw = json.loads(_SKILL_XP_LOG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load skill_xp_log.json — starting with no XP history.")
            return
        self._xp_log = [SkillXpEvent.from_dict(e) for e in raw.get("events", [])]

    def _save_xp_log(self) -> None:
        # Drop events older than the retention window before writing —
        # an unparseable/blank timestamp is kept rather than dropped
        # (same "no evidence, don't guess" stance as _event_date's own
        # callers elsewhere), since there's no safe way to judge its age.
        cutoff = datetime.now().date() - timedelta(days=_XP_LOG_MAX_AGE_DAYS)
        self._xp_log = [
            e for e in self._xp_log
            if _event_date(e.timestamp) is None or _event_date(e.timestamp) >= cutoff
        ]
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"events": [e.to_dict() for e in self._xp_log]}
        _SKILL_XP_LOG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def xp_earned_between(self, profile_id: str, skill_id: str, start: date, end: date) -> int:
        """Sum of real XP-grant events for this skill with
        start <= event date < end (half-open, so adjacent windows —
        e.g. Pattern Insights' recent/prior split — never double-count
        a day). Reads the real per-grant event log, unlike total_xp
        (a lifetime cumulative) or last_touched (a single latest
        timestamp) — this is the one query that needs actual history."""
        total = 0
        for event in self._xp_log:
            if event.profile_id != profile_id or event.skill_id != skill_id:
                continue
            event_date = _event_date(event.timestamp)
            if event_date is not None and start <= event_date < end:
                total += event.amount
        return total

    def get_progress(self, profile_id: str, skill_id: str) -> SkillProgress:
        """Never returns None — an untrained skill is just 0 XP, not a
        missing record, so callers never need a null-check before
        reading .total_xp."""
        key = (profile_id, skill_id)
        if key not in self._progress:
            return SkillProgress(profile_id=profile_id, skill_id=skill_id, total_xp=0)
        return self._progress[key]

    def progress_for_profile(self, profile_id: str) -> list[SkillProgress]:
        """Only ever returns skills the profile has actually earned XP
        in — untrained skills (0 XP) simply don't appear, same as how
        an untrained skill's SkillProgress is never persisted."""
        return [p for p in self._progress.values() if p.profile_id == profile_id]

    def add_skill_xp(self, profile_id: str, skill_id: str, amount: int) -> Optional[int]:
        """Credits `amount` XP to a profile's lifetime total in
        `skill_id`. Returns the new total, or None if `skill_id` isn't
        a known definition (never silently creates an undefined skill
        — a typo'd skill_weights entry should be loud, not silent data
        drift, same "unknown profile_id logs a warning and returns
        None" stance as core.profile_manager.ProfileManager.add_xp()).
        Always grants, even if the skill is currently locked (see
        is_unlocked()) — a real activity's XP is real evidence of what
        happened and must never be silently dropped just because the
        skill tree UI hasn't "revealed" that node yet; is_unlocked() is
        a display concern, not a gate on this method.
        Publishes "profile.skill_xp_changed" (profile_id, skill_id),
        same live-refresh convention as
        core.profile_manager.ProfileManager.add_xp()'s
        "profile.xp_changed"."""
        if skill_id not in self._definitions:
            log.warning("Attempted to grant XP to unknown skill_id '%s'", skill_id)
            return None
        key = (profile_id, skill_id)
        existing = self._progress.get(key)
        old_total = existing.total_xp if existing else 0
        new_total = old_total + amount
        now_iso = datetime.now().isoformat(timespec="seconds")
        self._progress[key] = SkillProgress(
            profile_id=profile_id, skill_id=skill_id, total_xp=new_total,
            last_touched=now_iso,
        )
        self._save_progress()
        self._xp_log.append(SkillXpEvent(profile_id=profile_id, skill_id=skill_id, amount=amount, timestamp=now_iso))
        self._save_xp_log()
        log.info("Profile '%s' earned %d XP in skill '%s' (total now %d)", profile_id, amount, skill_id, new_total)
        self.context.events.publish("profile.skill_xp_changed", profile_id=profile_id, skill_id=skill_id)
        self._notify_achievements(profile_id, skill_id, old_total, new_total)
        return new_total

    def _notify_achievements(self, profile_id: str, skill_id: str, old_total: int, new_total: int) -> None:
        """Achievements/Milestones (2026-09-11) — the deterministic
        "you unlocked something" narration layer over add_skill_xp().
        See core/achievements.py's own docstring for why this is a
        pure before/after comparison rather than a new persisted
        entity. Graceful no-op with no notifications service, same
        stance as every other optional-service check in this codebase."""
        if self.context.notifications is None:
            return

        leveled_up, new_level = crossed_a_level(old_total, new_total, compute_skill_level_progress)
        if leveled_up:
            title, message = format_skill_level_up(self._definitions[skill_id].name, new_level)
            self.context.notifications.notify(title=title, message=message, level="info", source="achievements")

        # A skill only ever transitions locked -> unlocked at the exact
        # moment one of its prerequisites goes from 0 XP to any XP —
        # once a prerequisite already has XP, later grants to it can
        # never flip a dependent's unlock state again (is_unlocked()
        # checks a prerequisite's XP, not whether IT is "unlocked," so
        # this can never cascade to a second level of dependents from
        # one grant). Only worth scanning for on that one transition.
        if old_total == 0 and new_total > 0:
            for other in self._definitions.values():
                if skill_id in other.prerequisite_skill_ids and self.is_unlocked(profile_id, other.skill_id):
                    title, message = format_skill_unlocked(other.name)
                    self.context.notifications.notify(title=title, message=message, level="info", source="achievements")

    def capability_status(self, profile_id: str, skill_id: str) -> str:
        """
        Real-evidence-derived status for this skill (2026-09-11) — one
        of core.skill_leveling.CAPABILITY_STATUSES. Gathers the real
        inputs (is_unlocked(), current level from real total_xp) and
        delegates the tier boundary itself to
        core.skill_leveling.capability_status_for_level(), the single
        shared rule every consumer (Skills module, Discovery's prompt)
        should call through rather than re-deriving.
        """
        unlocked = self.is_unlocked(profile_id, skill_id)
        level, _, _ = compute_skill_level_progress(self.get_progress(profile_id, skill_id).total_xp)
        return capability_status_for_level(unlocked, level)

    def is_unlocked(self, profile_id: str, skill_id: str) -> bool:
        """A skill with no prerequisites is always unlocked. Unknown
        skill_ids are treated as unlocked too (nothing to gate on) —
        callers checking a real definition's own prerequisites are the
        only ones that matter here."""
        definition = self._definitions.get(skill_id)
        if definition is None or not definition.prerequisite_skill_ids:
            return True
        return all(
            self.get_progress(profile_id, prereq_id).total_xp > 0
            for prereq_id in definition.prerequisite_skill_ids
        )
