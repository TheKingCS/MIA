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


# ----------------------------------------------------------------------
# Prestige (2026-09-14) — the user's own design, confirmed via
# AskUserQuestion before any code was written: after fully leveling
# through 1-100, a real "Prestige" action resets the DISPLAYED level to
# 1 with a different color tier (a Borderlands-style white/green/blue/
# purple/orange scale) — celebratory, not punishing. Two decisions
# were locked in up front: (1) every prestige cycle costs the SAME XP
# as the first (not scaled up per tier), and (2) orange is the max
# color — prestiging past tier 4 keeps working mechanically, it just
# doesn't unlock a new color.
#
# `Profile.total_xp` stays lifetime-cumulative and UNCAPPED (existing
# invariant other code — achievements, crossed_a_level() below — relies
# on); `Profile.prestige_tier` is the one new persisted field (how many
# times the user has actually clicked "Prestige" — a real choice, not
# something derivable from total_xp alone, since a profile sitting at
# the level-100 ceiling hasn't necessarily prestiged yet). Everything
# else here is pure derivation from those two numbers, same "derive it,
# don't persist a second copy" philosophy as compute_level_progress()
# itself.
# ----------------------------------------------------------------------

#: XP to fully complete levels 1 through 100 inclusive — one full
#: prestige cycle. sum(100 * level for level in 1..100) = 100 * 5050.
XP_PER_PRESTIGE_CYCLE = sum(xp_required_for_level(level) for level in range(1, 101))

#: Borderlands-style tier colors, white (never prestiged) through
#: orange (tier 4, the user's own explicit max — see module docstring).
PRESTIGE_COLORS: tuple[str, ...] = ("white", "green", "blue", "purple", "orange")


def prestige_color_for_tier(tier: int) -> str:
    """Pure logic — testable without a real profile. Caps at
    PRESTIGE_COLORS' last entry (orange) for any tier at or past that
    point — prestiging further still works, the color just stops
    changing, the user's own explicit call."""
    index = min(max(tier, 0), len(PRESTIGE_COLORS) - 1)
    return PRESTIGE_COLORS[index]


def cycle_xp_for_profile(total_xp: int, prestige_tier: int) -> int:
    """XP earned within the CURRENT prestige cycle — total_xp minus
    whatever prior completed cycles already accounted for, clamped to
    one full cycle's ceiling. The clamp matters for a profile that's
    eligible to prestige but hasn't clicked the button yet: without it,
    compute_level_progress() would happily report a level past 100,
    which the "same curve every tier" design never defines — capping
    here keeps the display pinned at a maxed-out level 100 instead
    until the user actually prestiges."""
    earned_this_cycle = max(total_xp, 0) - (prestige_tier * XP_PER_PRESTIGE_CYCLE)
    return min(max(earned_this_cycle, 0), XP_PER_PRESTIGE_CYCLE)


def is_eligible_to_prestige(total_xp: int, prestige_tier: int) -> bool:
    """Pure logic — testable without a real profile. True once the
    current cycle's XP has reached the full-100-levels ceiling."""
    return cycle_xp_for_profile(total_xp, prestige_tier) >= XP_PER_PRESTIGE_CYCLE


def compute_prestige_level_progress(total_xp: int, prestige_tier: int) -> tuple[int, int, int]:
    """Same 3 numbers compute_level_progress() returns — (level,
    xp_into_level, xp_needed) — but computed against just the current
    prestige cycle's XP, so the displayed level genuinely resets to 1
    after a real Prestige action rather than climbing forever.

    Explicitly caps at a maxed-out level 100 (xp_into_level ==
    xp_needed, a full bar) rather than ever reporting a "level 101" —
    plain compute_level_progress() has no ceiling concept, so a profile
    that has earned exactly (or just past, before clamping) a full
    cycle's XP but hasn't clicked Prestige yet would otherwise report
    the nonexistent next level. Level 100 fully maxed IS the correct,
    real "ready to prestige" state to display."""
    level, xp_into_level, xp_needed = compute_level_progress(cycle_xp_for_profile(total_xp, prestige_tier))
    if level > 100:
        capped_needed = xp_required_for_level(100)
        return 100, capped_needed, capped_needed
    return level, xp_into_level, xp_needed
