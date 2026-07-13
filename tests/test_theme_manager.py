"""
tests.test_theme_manager
===========================

Unit tests for gui.theme_manager. Pure string-lookup logic — no Qt
event loop needed.
"""

from __future__ import annotations

from gui.styles import DARK_FIELD_THEME
from gui.theme_manager import THEME_DISPLAY_NAMES, THEMES, get_theme_stylesheet


def test_all_four_themes_registered():
    assert set(THEMES.keys()) == {"dark_field", "low_energy", "colored", "anime_monochrome"}


def test_dark_field_theme_matches_gui_styles_constant():
    assert get_theme_stylesheet("dark_field") == DARK_FIELD_THEME


def test_get_theme_stylesheet_returns_distinct_content_per_theme():
    stylesheets = {theme_id: get_theme_stylesheet(theme_id) for theme_id in THEMES}
    assert len(set(stylesheets.values())) == len(stylesheets)


def test_get_theme_stylesheet_falls_back_to_default_for_unknown_id():
    assert get_theme_stylesheet("does-not-exist") == get_theme_stylesheet("dark_field")


def test_every_theme_has_a_display_name():
    assert set(THEME_DISPLAY_NAMES.keys()) == set(THEMES.keys())
