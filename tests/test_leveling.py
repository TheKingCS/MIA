from core.leveling import compute_level_progress, xp_required_for_level


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
