from core.skill_leveling import (
    capability_status_for_level,
    compute_skill_level_progress,
    xp_required_for_skill_level,
)


def test_xp_required_for_skill_level_scales_linearly():
    assert xp_required_for_skill_level(1) == 20
    assert xp_required_for_skill_level(5) == 100


def test_xp_required_for_skill_level_floors_at_level_1():
    assert xp_required_for_skill_level(0) == 20


def test_compute_skill_level_progress_at_zero_xp():
    assert compute_skill_level_progress(0) == (1, 0, 20)


def test_compute_skill_level_progress_partway_through_level_1():
    assert compute_skill_level_progress(12) == (1, 12, 20)


def test_compute_skill_level_progress_exactly_at_level_boundary():
    assert compute_skill_level_progress(20) == (2, 0, 40)


def test_compute_skill_level_progress_advances_multiple_levels():
    # Level 1 needs 20, level 2 needs 40, level 3 needs 60 -> 120 total to reach level 4.
    assert compute_skill_level_progress(120) == (4, 0, 80)


def test_compute_skill_level_progress_partway_through_a_later_level():
    # 130 = 120 (levels 1-3 complete) + 10 into level 4 (needs 80).
    assert compute_skill_level_progress(130) == (4, 10, 80)


def test_compute_skill_level_progress_negative_xp_treated_as_zero():
    assert compute_skill_level_progress(-50) == (1, 0, 20)


def test_capability_status_locked_overrides_any_level():
    assert capability_status_for_level(unlocked=False, level=1) == "locked"
    assert capability_status_for_level(unlocked=False, level=10) == "locked"


def test_capability_status_level_1_is_learning():
    assert capability_status_for_level(unlocked=True, level=1) == "learning"


def test_capability_status_levels_2_and_3_are_practiced():
    assert capability_status_for_level(unlocked=True, level=2) == "practiced"
    assert capability_status_for_level(unlocked=True, level=3) == "practiced"


def test_capability_status_level_4_and_above_is_demonstrated():
    assert capability_status_for_level(unlocked=True, level=4) == "demonstrated"
    assert capability_status_for_level(unlocked=True, level=10) == "demonstrated"
