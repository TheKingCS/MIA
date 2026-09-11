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
