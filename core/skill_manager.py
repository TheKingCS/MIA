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
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SKILL_DEFINITIONS_FILE = _DATA_DIR / "skill_definitions.json"
_SKILL_PROGRESS_FILE = _DATA_DIR / "skill_progress.json"


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

    def to_dict(self) -> dict:
        return {"profile_id": self.profile_id, "skill_id": self.skill_id, "total_xp": self.total_xp}

    @staticmethod
    def from_dict(data: dict) -> "SkillProgress":
        return SkillProgress(
            profile_id=data["profile_id"],
            skill_id=data["skill_id"],
            total_xp=data.get("total_xp", 0),
        )


class SkillManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._definitions: dict[str, SkillDefinition] = {}
        self._progress: dict[tuple[str, str], SkillProgress] = {}
        self._load_definitions()
        self._load_progress()

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
        new_total = (existing.total_xp if existing else 0) + amount
        self._progress[key] = SkillProgress(profile_id=profile_id, skill_id=skill_id, total_xp=new_total)
        self._save_progress()
        log.info("Profile '%s' earned %d XP in skill '%s' (total now %d)", profile_id, amount, skill_id, new_total)
        self.context.events.publish("profile.skill_xp_changed", profile_id=profile_id, skill_id=skill_id)
        return new_total

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
