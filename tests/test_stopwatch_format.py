"""
tests.test_stopwatch_format
==============================

Unit tests for modules.toolbox.tools.stopwatch_tool.format_elapsed —
pure formatting logic, no Qt/QApplication needed.
"""

from __future__ import annotations

import pytest

from modules.toolbox.tools.stopwatch_tool import format_elapsed


def test_zero_formats_as_zero():
    assert format_elapsed(0) == "00:00.0"


def test_sub_second_truncates_to_tenths():
    assert format_elapsed(450) == "00:00.4"


def test_seconds_and_tenths():
    assert format_elapsed(5_300) == "00:05.3"


def test_minutes_seconds_tenths():
    assert format_elapsed(65_000) == "01:05.0"


def test_under_an_hour_has_no_hours_component():
    assert format_elapsed(59 * 60_000 + 59_900) == "59:59.9"


def test_exactly_one_hour_switches_to_hh_mm_ss_format():
    assert format_elapsed(60 * 60_000) == "01:00:00.0"


def test_hours_minutes_seconds_tenths():
    total_ms = (2 * 3600 + 3 * 60 + 4) * 1000 + 500
    assert format_elapsed(total_ms) == "02:03:04.5"


def test_negative_raises():
    with pytest.raises(ValueError):
        format_elapsed(-1)
