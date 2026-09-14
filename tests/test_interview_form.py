"""
tests.test_interview_form
============================

Unit tests for gui.widgets.interview_form's pure functions, same style
as every other *_module.py test file in this project (no Qt event
loop, no fixtures).
"""

from __future__ import annotations

from gui.widgets.interview_form import format_interview_intro


def test_format_interview_intro_uses_the_real_name():
    assert format_interview_intro("Faith").startswith("Hey Faith —")


def test_format_interview_intro_strips_whitespace():
    assert format_interview_intro("  Zac  ").startswith("Hey Zac —")


def test_format_interview_intro_falls_back_when_blank():
    assert format_interview_intro("").startswith("Hey there —")


def test_format_interview_intro_falls_back_when_only_whitespace():
    assert format_interview_intro("   ").startswith("Hey there —")
