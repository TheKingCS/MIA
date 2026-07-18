"""
core.leveling
===============

Pure XP/Level math for the Missions gamification system — no Qt, no
persistence, testable in isolation (see tests/test_leveling.py).
`core/profile_manager.py` stores the one number that matters
(`Profile.total_xp`, lifetime cumulative); everything else — what level
that corresponds to, and how far into the current level the player is —
is derived here, on demand, the same "derive it, don't persist a second
copy that can drift" philosophy `core/mission_manager.py`'s
`objective_progress()` already uses for trip_duration_hours/task_done.

**2026-07-18 design handoff** (`CCH.zip`'s Missions screen): missions
now carry `reward_xp`/`reward_credits`, credited to the active profile
on completion (`core/mission_manager.py`'s `update_mission()`). The
level-progress bar reads as "XP earned so far *within the current
level* / XP needed *for the current level*" (matching the design's
"9,143 / 13,886" readout), not a lifetime total — `compute_level_progress()`
returns exactly those three numbers.
"""

from __future__ import annotations


def xp_required_for_level(level: int) -> int:
    """
    XP needed to advance from `level` to `level + 1`. Linear growth
    (100 * level) — level 1->2 needs 100, 5->6 needs 500, and so on —
    simple, predictable, and scales naturally against the kind of
    per-mission rewards (tens to low hundreds of XP) this system hands
    out, without needing a lookup table.
    """
    return 100 * max(level, 1)


def compute_level_progress(total_xp: int) -> tuple[int, int, int]:
    """
    Returns (level, xp_into_level, xp_needed_for_level) for a given
    lifetime-cumulative `total_xp`. Level starts at 1 for 0 XP.
    """
    level = 1
    remaining = max(total_xp, 0)
    while True:
        needed = xp_required_for_level(level)
        if remaining < needed:
            return level, remaining, needed
        remaining -= needed
        level += 1
