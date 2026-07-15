"""
tests.test_startup_briefing
==============================

Unit tests for core.startup_briefing's pure functions — see
gui/home_dashboard.py for how these feed the launch-greeting banner.
"""

from __future__ import annotations

from datetime import datetime

from core.startup_briefing import build_stat_highlights, build_startup_briefing, greeting_for_hour


def test_greeting_for_hour_morning():
    assert greeting_for_hour(8) == "Good morning"


def test_greeting_for_hour_afternoon():
    assert greeting_for_hour(13) == "Good afternoon"


def test_greeting_for_hour_evening():
    assert greeting_for_hour(19) == "Good evening"


def test_greeting_for_hour_boundary_noon_is_afternoon():
    assert greeting_for_hour(12) == "Good afternoon"


def test_greeting_for_hour_boundary_6pm_is_evening():
    assert greeting_for_hour(18) == "Good evening"


def test_build_stat_highlights_all_zero_returns_empty():
    assert build_stat_highlights(0, 0) == []


def test_build_stat_highlights_singular_nouns():
    highlights = build_stat_highlights(1, 1)
    assert highlights == ["1 calendar event today", "1 unread notification"]


def test_build_stat_highlights_plural_nouns_and_skips_zero():
    highlights = build_stat_highlights(0, 3)
    assert highlights == ["3 unread notifications"]


def test_build_startup_briefing_nothing_to_report():
    text = build_startup_briefing("Zac", datetime(2026, 7, 15, 19, 0), [], None)
    assert text == "Good evening, Zac. Welcome back. Nothing new to report today — a clean slate."


def test_build_startup_briefing_single_highlight():
    text = build_startup_briefing("Zac", datetime(2026, 7, 15, 8, 0), ["1 active mission"], None)
    assert text == "Good morning, Zac. Welcome back. You have 1 active mission."


def test_build_startup_briefing_multiple_highlights_joined_with_and():
    text = build_startup_briefing(
        "Zac",
        datetime(2026, 7, 15, 13, 0),
        ["2 active missions", "1 calendar event today", "3 unread notifications"],
        None,
    )
    assert text == (
        "Good afternoon, Zac. Welcome back. "
        "You have 2 active missions, 1 calendar event today, and 3 unread notifications."
    )


def test_build_startup_briefing_includes_latest_memory():
    text = build_startup_briefing("Zac", datetime(2026, 7, 15, 19, 0), [], "Rocky Ridge Trip")
    assert text == "Good evening, Zac. Welcome back. Your most recent memory: Rocky Ridge Trip."


def test_build_startup_briefing_highlights_and_memory_together():
    text = build_startup_briefing("Zac", datetime(2026, 7, 15, 19, 0), ["1 active mission"], "Rocky Ridge Trip")
    assert text == (
        "Good evening, Zac. Welcome back. You have 1 active mission. "
        "Your most recent memory: Rocky Ridge Trip."
    )
