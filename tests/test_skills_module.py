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
    format_header_stats_line,
    format_locked_skill_name,
    format_next_honest_step_line,
    format_prerequisites_line,
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


def test_format_next_honest_step_line_names_a_skill():
    assert format_next_honest_step_line("Gardening") == "Put some real time toward Gardening next."


def test_format_next_honest_step_line_none():
    assert format_next_honest_step_line(None) == "Nothing to suggest right now — every skill is locked."


def test_format_prerequisites_line_single():
    assert format_prerequisites_line(["3D Printing"]) == "Requires: 3D Printing"


def test_format_prerequisites_line_multiple():
    assert format_prerequisites_line(["Automation", "Fabrication"]) == "Requires: Automation, Fabrication"
