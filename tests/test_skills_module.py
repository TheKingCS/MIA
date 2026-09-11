"""
tests.test_skills_module
===========================

Unit tests for modules.skills.module's pure functions, same style as
tests/test_missions_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from modules.skills.module import (
    format_locked_skill_name,
    format_prerequisites_line,
    format_skill_subtitle,
    format_skills_trained_summary,
)


def test_format_skill_subtitle():
    assert format_skill_subtitle(3, 12, 60) == "Lv. 3 · 12/60 XP"


def test_format_locked_skill_name():
    assert format_locked_skill_name("CAD / 3D Design") == "(Locked) CAD / 3D Design"


def test_format_skills_trained_summary():
    assert format_skills_trained_summary(5, 80) == "5 of 80 skills trained"


def test_format_skills_trained_summary_none_trained():
    assert format_skills_trained_summary(0, 80) == "0 of 80 skills trained"


def test_format_prerequisites_line_single():
    assert format_prerequisites_line(["3D Printing"]) == "Requires: 3D Printing"


def test_format_prerequisites_line_multiple():
    assert format_prerequisites_line(["Automation", "Fabrication"]) == "Requires: Automation, Fabrication"
