"""
tests.test_main_window
=========================

Unit tests for gui.main_window's pure functions, same style as
tests/test_missions_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from gui.main_window import format_level_badge_text


def test_format_level_badge_text_omits_prestige_at_tier_zero():
    assert format_level_badge_text(7) == "Lv. 7"


def test_format_level_badge_text_omits_prestige_when_explicitly_zero():
    assert format_level_badge_text(7, 0) == "Lv. 7"


def test_format_level_badge_text_includes_prestige_once_earned():
    assert format_level_badge_text(100, 2) == "Lv. 100 · P2"
