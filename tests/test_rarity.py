"""
tests.test_rarity
====================

Unit tests for core.rarity's pure functions.
"""

from __future__ import annotations

from core.rarity import rarity_color_for_index, rarity_name_for_index


def test_rarity_name_for_index_common():
    assert rarity_name_for_index(0) == "Common"


def test_rarity_name_for_index_legendary():
    assert rarity_name_for_index(4) == "Legendary"


def test_rarity_name_for_index_clamps_above_range():
    assert rarity_name_for_index(9) == "Legendary"


def test_rarity_name_for_index_clamps_below_range():
    assert rarity_name_for_index(-3) == "Common"


def test_rarity_color_for_index_matches_prestige_colors():
    from core.leveling import PRESTIGE_COLORS
    for index in range(5):
        assert rarity_color_for_index(index) == PRESTIGE_COLORS[index]
