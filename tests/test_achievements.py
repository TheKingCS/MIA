"""
tests.test_achievements
==========================

Unit tests for core.achievements' pure functions — no Qt, no
persistence, same style as tests/test_leveling.py/
tests/test_skill_leveling.py.
"""

from __future__ import annotations

from core.achievements import (
    crossed_a_level,
    format_profile_level_up,
    format_skill_level_up,
    format_skill_unlocked,
)
from core.leveling import compute_level_progress
from core.skill_leveling import compute_skill_level_progress


def test_crossed_a_level_true_when_level_increases():
    # compute_level_progress: level 1 needs 100 XP -> level 2
    leveled_up, new_level = crossed_a_level(90, 110, compute_level_progress)
    assert leveled_up is True
    assert new_level == 2


def test_crossed_a_level_false_when_staying_in_the_same_level():
    leveled_up, new_level = crossed_a_level(10, 50, compute_level_progress)
    assert leveled_up is False
    assert new_level == 1


def test_crossed_a_level_false_at_exactly_the_boundary_from_zero():
    # 0 -> 0 (no XP granted) never crosses anything
    leveled_up, new_level = crossed_a_level(0, 0, compute_level_progress)
    assert leveled_up is False


def test_crossed_a_level_works_with_skill_progress_curve_too():
    # compute_skill_level_progress: level 1 needs 20 XP -> level 2
    leveled_up, new_level = crossed_a_level(15, 25, compute_skill_level_progress)
    assert leveled_up is True
    assert new_level == 2


def test_crossed_a_level_detects_multi_level_jumps():
    # A big single grant can cross more than one level at once --
    # still just "did it increase," reports the final level reached.
    # Level 1 needs 100 XP, level 2 needs 200 more (300 total to reach
    # level 3) -- 250 total_xp lands mid-level-2, not level 3.
    leveled_up, new_level = crossed_a_level(0, 250, compute_level_progress)
    assert leveled_up is True
    assert new_level == 2


def test_format_skill_level_up():
    title, message = format_skill_level_up("Strength", 5)
    assert title == "\U0001F393 Skill level up!"
    assert message == "Strength reached Level 5!"


def test_format_skill_unlocked():
    title, message = format_skill_unlocked("CAD / 3D Design")
    assert title == "\U0001F513 New skill unlocked!"
    assert message == "You've unlocked CAD / 3D Design — take a look."


def test_format_profile_level_up():
    title, message = format_profile_level_up(7)
    assert title == "\U00002B50 Level up!"
    assert message == "You reached Level 7!"
