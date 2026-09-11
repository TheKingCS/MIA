"""
core.achievements
====================

The deterministic "you unlocked something" narration layer — the
"Achievements/Milestones" piece flagged as a real gap across both the
"My Hero's Path" plan and the "connective infrastructure" architecture
review that followed the whole-codebase audit (see docs/ROADMAP.md's
dated entry).

No new persisted entity here, deliberately. Every achievement this
module recognizes is a real, already-derivable fact — "did this
skill's level number just increase," "did a skill's prerequisites just
become satisfied" — computed as a pure before/after comparison, same
"derive, don't persist a second copy that can drift" philosophy
core/leveling.py and core/skill_leveling.py already use for the level
numbers themselves. Delivery is the existing
core.notification_manager.NotificationManager.notify() call (already
both a toast and a persisted, readable record) with
source="achievements" — one shared, filterable source distinct from
the existing "gamification" source used for routine XP grants.

Deliberately rule-based, not LLM-driven — same stance as
core.mission_manager.MissionManager's own auto-assignment rules, and
the architecture discussion's own agreed position that Discovery-style
pattern-noticing should stay deterministic for now.
"""

from __future__ import annotations

from typing import Callable


def crossed_a_level(old_total: int, new_total: int, compute_progress: Callable[[int], tuple]) -> tuple[bool, int]:
    """Returns (did_level_up, new_level) by comparing the level
    `compute_progress` derives from `old_total` vs. `new_total`.
    `compute_progress` is either core.leveling.compute_level_progress
    or core.skill_leveling.compute_skill_level_progress — both return
    the same (level, xp_into_level, xp_needed) shape, so one comparison
    works for either the profile-wide Level or a single Skill's level."""
    old_level, _, _ = compute_progress(old_total)
    new_level, _, _ = compute_progress(new_total)
    return new_level > old_level, new_level


def format_skill_level_up(skill_name: str, new_level: int) -> tuple[str, str]:
    """Pure formatting logic — testable without Qt (see tests/test_achievements.py)."""
    return ("\U0001F393 Skill level up!", f"{skill_name} reached Level {new_level}!")


def format_skill_unlocked(skill_name: str) -> tuple[str, str]:
    """Pure formatting logic — testable without Qt (see tests/test_achievements.py)."""
    return ("\U0001F513 New skill unlocked!", f"You've unlocked {skill_name} — take a look.")


def format_profile_level_up(new_level: int) -> tuple[str, str]:
    """Pure formatting logic — testable without Qt (see tests/test_achievements.py)."""
    return ("\U00002B50 Level up!", f"You reached Level {new_level}!")
