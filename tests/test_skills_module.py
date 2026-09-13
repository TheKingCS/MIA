"""
tests.test_skills_module
===========================

Unit tests for modules.skills.module's pure functions, same style as
tests/test_missions_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from modules.skills.module import (
    format_achievement_title_for_display,
    format_capability_status_label,
    format_chain_maxed_line,
    format_earned_title_line,
    format_header_stats_line,
    format_locked_skill_name,
    format_next_honest_step_line,
    format_prerequisites_line,
    format_prestige_status,
    format_reward_status_line,
    format_skill_status_line,
    format_skill_subtitle,
    format_tier_chip,
)


def test_format_skill_subtitle():
    assert format_skill_subtitle(3, 12, 60) == "Lv. 3 · 12/60 XP"


def test_format_locked_skill_name():
    assert format_locked_skill_name("CAD / 3D Design") == "(Locked) CAD / 3D Design"


def test_format_capability_status_label():
    assert format_capability_status_label("learning") == "Learning"
    assert format_capability_status_label("practiced") == "Practiced"
    assert format_capability_status_label("demonstrated") == "Demonstrated"


def test_format_skill_status_line():
    assert format_skill_status_line(5, "demonstrated") == "LV 5 · DEMONSTRATED"


def test_format_tier_chip():
    assert format_tier_chip(3) == "T3"


def test_format_achievement_title_for_display_strips_leading_emoji():
    assert format_achievement_title_for_display("\U0001F393 Skill level up!") == "Skill level up!"


def test_format_achievement_title_for_display_leaves_ascii_titles_alone():
    assert format_achievement_title_for_display("Plain Title Here") == "Plain Title Here"


def test_format_header_stats_line():
    assert format_header_stats_line(7, 23, 96, 4) == "PROFILE LEVEL 7 · SKILLS TOUCHED 23/96 · DEMONSTRATED 4"


def test_format_header_stats_line_omits_prestige_at_tier_zero():
    assert format_header_stats_line(7, 23, 96, 4, prestige_tier=0) == "PROFILE LEVEL 7 · SKILLS TOUCHED 23/96 · DEMONSTRATED 4"


def test_format_header_stats_line_includes_prestige_once_earned():
    assert format_header_stats_line(1, 23, 96, 4, prestige_tier=2) == "PROFILE LEVEL 1 · PRESTIGE 2 · SKILLS TOUCHED 23/96 · DEMONSTRATED 4"


# ------------------------------------------------------------------
# Prestige (2026-09-14)
# ------------------------------------------------------------------

def test_format_prestige_status_not_yet_eligible():
    assert format_prestige_status(42, eligible=False, prestige_tier=0) == "Level 42/100 — prestige unlocks once you max out level 100."


def test_format_prestige_status_eligible_names_the_next_color():
    assert format_prestige_status(100, eligible=True, prestige_tier=0) == "Level 100 maxed out! Prestige now — next badge color: green."


def test_format_prestige_status_eligible_at_a_later_tier():
    assert format_prestige_status(100, eligible=True, prestige_tier=3) == "Level 100 maxed out! Prestige now — next badge color: orange."


def test_format_next_honest_step_line_names_a_skill():
    assert format_next_honest_step_line("Gardening") == "Put some real time toward Gardening next."


def test_format_next_honest_step_line_none():
    assert format_next_honest_step_line(None) == "Nothing to suggest right now — every skill is locked."


def test_format_prerequisites_line_single():
    assert format_prerequisites_line(["3D Printing"]) == "Requires: 3D Printing"


def test_format_prerequisites_line_multiple():
    assert format_prerequisites_line(["Automation", "Fabrication"]) == "Requires: Automation, Fabrication"


def test_format_reward_status_line_locked_shows_progress_and_unit():
    assert format_reward_status_line("Log 10 hours on your mower.", "hrs", 4.0, 10.0, False) == \
        "4/10 hrs — Log 10 hours on your mower."


def test_format_reward_status_line_locked_omits_unit_when_blank():
    assert format_reward_status_line("Complete 5 missions.", "", 2.0, 5.0, False) == \
        "2/5 — Complete 5 missions."


def test_format_reward_status_line_unlocked_drops_the_numbers():
    assert format_reward_status_line("Log 10 hours on your mower.", "hrs", 12.0, 10.0, True) == \
        "Unlocked — Log 10 hours on your mower."


def test_format_earned_title_line():
    assert format_earned_title_line("🧢", "Lawn Rookie") == "Earned: 🧢 Lawn Rookie"


def test_format_chain_maxed_line():
    assert format_chain_maxed_line("🏆", "Master of the Grounds") == "\U0001F3C6 Maxed out — 🏆 Master of the Grounds"
