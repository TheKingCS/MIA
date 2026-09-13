from core.leveling import (
    XP_PER_PRESTIGE_CYCLE,
    compute_level_progress,
    compute_prestige_level_progress,
    cycle_xp_for_profile,
    is_eligible_to_prestige,
    prestige_color_for_tier,
    xp_required_for_level,
)


def test_xp_required_for_level_scales_linearly():
    assert xp_required_for_level(1) == 100
    assert xp_required_for_level(5) == 500


def test_xp_required_for_level_floors_at_level_1():
    assert xp_required_for_level(0) == 100


def test_compute_level_progress_at_zero_xp():
    assert compute_level_progress(0) == (1, 0, 100)


def test_compute_level_progress_partway_through_level_1():
    assert compute_level_progress(60) == (1, 60, 100)


def test_compute_level_progress_exactly_at_level_boundary():
    assert compute_level_progress(100) == (2, 0, 200)


def test_compute_level_progress_advances_multiple_levels():
    # Level 1 needs 100, level 2 needs 200, level 3 needs 300 -> 600 total to reach level 4.
    assert compute_level_progress(600) == (4, 0, 400)


def test_compute_level_progress_partway_through_a_later_level():
    # 650 = 600 (levels 1-3 complete) + 50 into level 4 (needs 400).
    assert compute_level_progress(650) == (4, 50, 400)


def test_compute_level_progress_negative_xp_treated_as_zero():
    assert compute_level_progress(-50) == (1, 0, 100)


# ------------------------------------------------------------------
# Prestige (2026-09-14)
# ------------------------------------------------------------------

def test_xp_per_prestige_cycle_is_levels_1_through_100():
    # sum(100 * level for level in 1..100) == 100 * 5050
    assert XP_PER_PRESTIGE_CYCLE == 505000


def test_prestige_color_for_tier_scale():
    assert prestige_color_for_tier(0) == "white"
    assert prestige_color_for_tier(1) == "green"
    assert prestige_color_for_tier(2) == "blue"
    assert prestige_color_for_tier(3) == "purple"
    assert prestige_color_for_tier(4) == "orange"


def test_prestige_color_for_tier_caps_at_orange():
    """The user's own explicit call: orange is the max, prestiging
    further still works mechanically, the color just stops changing."""
    assert prestige_color_for_tier(5) == "orange"
    assert prestige_color_for_tier(100) == "orange"


def test_prestige_color_for_tier_negative_treated_as_zero():
    assert prestige_color_for_tier(-1) == "white"


def test_cycle_xp_for_profile_first_cycle_matches_raw_total():
    assert cycle_xp_for_profile(50000, prestige_tier=0) == 50000


def test_cycle_xp_for_profile_subtracts_completed_cycles():
    assert cycle_xp_for_profile(XP_PER_PRESTIGE_CYCLE + 1000, prestige_tier=1) == 1000


def test_cycle_xp_for_profile_clamps_to_cycle_ceiling_when_not_yet_prestiged():
    """Eligible to prestige but hasn't clicked the button yet — stays
    pinned at the cycle's own ceiling, not overflowing past it."""
    assert cycle_xp_for_profile(XP_PER_PRESTIGE_CYCLE + 50000, prestige_tier=0) == XP_PER_PRESTIGE_CYCLE


def test_is_eligible_to_prestige_false_before_the_cycle_completes():
    assert is_eligible_to_prestige(XP_PER_PRESTIGE_CYCLE - 1, prestige_tier=0) is False


def test_is_eligible_to_prestige_true_exactly_at_the_boundary():
    assert is_eligible_to_prestige(XP_PER_PRESTIGE_CYCLE, prestige_tier=0) is True


def test_is_eligible_to_prestige_false_right_after_a_real_prestige():
    assert is_eligible_to_prestige(XP_PER_PRESTIGE_CYCLE, prestige_tier=1) is False


def test_compute_prestige_level_progress_resets_after_a_real_prestige():
    """Same shape compute_level_progress() itself returns, but reset
    to level 1 once prestige_tier accounts for the prior cycle — the
    user's own explicit "same XP curve every tier" choice, not a
    harder climb the second time."""
    assert compute_prestige_level_progress(XP_PER_PRESTIGE_CYCLE, prestige_tier=1) == (1, 0, 100)


def test_compute_prestige_level_progress_matches_plain_progress_at_tier_zero():
    assert compute_prestige_level_progress(600, prestige_tier=0) == compute_level_progress(600)


def test_compute_prestige_level_progress_caps_at_a_maxed_level_100():
    """Real gap caught while wiring this up: plain compute_level_progress()
    has no ceiling, so exactly completing a cycle reports "level 101" —
    a level the prestige model never defines. This must cap at a
    maxed-out level 100 (a full bar) instead, since that's the real
    state ("ready to prestige") every other display should show."""
    level, xp_into_level, xp_needed = compute_prestige_level_progress(XP_PER_PRESTIGE_CYCLE, prestige_tier=0)
    assert level == 100
    assert xp_into_level == xp_needed
