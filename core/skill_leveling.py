"""
core.skill_leveling
======================

Pure XP/Level math for a single Skill in "My Hero's Path" — same
"derive it, don't persist a second copy that can drift" philosophy as
core/leveling.py's profile-wide Level, but scaled down: a single
skill's XP pool fills from a handful of small per-activity grants
(core.gamification.grant_xp()'s skill_weights), not the profile-wide
pool's XP-per-action-across-everything, so a skill needs a much
smaller per-level requirement to ever feel like it moves.

No Qt, no persistence — testable in isolation (see
tests/test_skill_leveling.py), same shape as core/leveling.py itself.
"""

from __future__ import annotations

#: Capability status tiers (2026-09-11) — a derived, readable status
#: over a skill's existing level/unlock state, not a new persisted
#: field: every skill's XP already only ever comes from a real
#: completed Mission/Pathway-step/Project (no passive/incidental XP
#: source exists anywhere in this codebase), so "has real XP" already
#: means "did something real" — this just gives that existing evidence
#: a readable label. See capability_status_for_level()'s own docstring
#: for the level->tier boundaries and the deliberate simplifications.
CAPABILITY_STATUSES: tuple[str, ...] = ("locked", "learning", "practiced", "demonstrated")


def capability_status_for_level(unlocked: bool, level: int) -> str:
    """
    Pure. Maps a skill's real unlock state + derived level onto one of
    CAPABILITY_STATUSES. `unlocked` always wins first — a skill with
    unmet prerequisites is "locked" regardless of any level a caller
    passes in. First-cut boundary, not tuned further — same "revisit
    once real usage shows whether this feels right" stance
    xp_required_for_skill_level()'s own docstring already takes for the
    level curve itself.

    Deliberate simplification: level 1 covers both "just became
    available, zero XP yet" and "started but hasn't leveled up once" —
    both genuinely mean "no real demonstrated evidence yet," and a
    distinct 5th "available but untouched" tier would need a real
    signal (e.g. a first-activity timestamp) that doesn't exist yet
    either. Not a sub-capability breakdown (Soil Prep/Garden Beds/etc.
    under one skill) — that's real, separate, much bigger authored
    content, not attempted here.
    """
    if not unlocked:
        return "locked"
    if level == 1:
        return "learning"
    if level in (2, 3):
        return "practiced"
    return "demonstrated"


def xp_required_for_skill_level(level: int) -> int:
    """
    XP needed to advance a single skill from `level` to `level + 1`.
    Linear growth (20 * level) — a gentler curve than
    core.leveling.xp_required_for_level()'s 100 * level, since a
    single skill only ever receives a slice of any one activity's XP
    (level 1->2 needs 20 XP, level 5->6 needs 100). Deliberately not
    tuned further than this; revisit once real per-skill XP flow shows
    whether this curve feels right — same "no formula to derive it
    from today" stance core/gamification.py's reward sizing already
    takes.
    """
    return 20 * max(level, 1)


def compute_skill_level_progress(total_xp: int) -> tuple[int, int, int]:
    """
    Returns (level, xp_into_level, xp_needed_for_level) for a skill's
    lifetime-cumulative `total_xp`. Level starts at 1 for 0 XP — same
    shape as core.leveling.compute_level_progress().
    """
    level = 1
    remaining = max(total_xp, 0)
    while True:
        needed = xp_required_for_skill_level(level)
        if remaining < needed:
            return level, remaining, needed
        remaining -= needed
        level += 1
