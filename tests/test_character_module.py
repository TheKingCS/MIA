"""
tests.test_character_module
==============================

Unit tests for modules.character.module's pure functions, same style
as tests/test_household_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.rewards_manager import ChallengeTier, HiddenAchievement
from modules.character.module import (
    format_character_level_line,
    format_collection_entry_title,
    format_rarity_tally_line,
    format_stat_line,
    sorted_collection,
)


def test_format_character_level_line_omits_prestige_at_tier_zero():
    assert format_character_level_line(47, 7820, 10000, 0) == "LEVEL 47 · 7,820/10,000 XP"


def test_format_character_level_line_includes_prestige_once_earned():
    assert format_character_level_line(1, 0, 100, 2) == "LEVEL 1 · 0/100 XP · PRESTIGE 2"


def test_format_stat_line_with_unit():
    assert format_stat_line("\U0001F69C", "Engine Hours Logged", 42.5, "hrs") == "\U0001F69C Engine Hours Logged — 42.5 hrs"


def test_format_stat_line_without_unit():
    assert format_stat_line("\U0001F3C6", "Missions Completed", 12, "") == "\U0001F3C6 Missions Completed — 12"


def test_format_collection_entry_title():
    assert format_collection_entry_title("\U0001F9E2", "Lawn Ranger") == "\U0001F9E2 Lawn Ranger"


def test_format_rarity_tally_line():
    assert format_rarity_tally_line("Legendary", 2) == "Legendary ×2"


def test_sorted_collection_orders_by_rarity_then_name():
    common_b = ChallengeTier("b", "Bravo", "desc", "x", 1.0, 0)
    common_a = ChallengeTier("a", "Alpha", "desc", "x", 1.0, 0)
    legendary = HiddenAchievement("legend", "Zulu", "desc", "x", 4, ("stat",), 1.0)
    epic = ChallengeTier("c", "Charlie", "desc", "x", 1.0, 3)

    result = sorted_collection([common_b, common_a, epic], [legendary])

    assert [entry.name for entry in result] == ["Zulu", "Charlie", "Alpha", "Bravo"]


def test_sorted_collection_empty():
    assert sorted_collection([], []) == []
