"""
tests.test_onboarding
========================

Unit tests for core.onboarding's pure functions — see
gui/home_dashboard.py's _inject_first_run_welcome() for how this feeds
a brand-new user's very first conversation. Same shape as
tests/test_startup_briefing.py.
"""

from __future__ import annotations

from core.onboarding import build_first_run_welcome_message


def test_build_first_run_welcome_message_includes_the_users_name():
    message = build_first_run_welcome_message("Zac")
    assert "Zac" in message


def test_build_first_run_welcome_message_includes_suggested_prompts():
    message = build_first_run_welcome_message("Zac")
    assert "try asking me" in message.lower()
    assert '"' in message  # at least one quoted example prompt


def test_build_first_run_welcome_message_mentions_teaching_mode():
    """Points a brand-new user toward the "teach me how X works"
    conversational path (2026-09-10) as an explicit next step."""
    message = build_first_run_welcome_message("Zac")
    assert "teach me how" in message.lower()


def test_build_first_run_welcome_message_works_with_fallback_name():
    """gui/home_dashboard.py passes "there" when no active profile exists."""
    message = build_first_run_welcome_message("there")
    assert "there" in message
