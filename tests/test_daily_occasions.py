"""
tests.test_daily_occasions
=============================

Unit tests for core.daily_occasions' pure decision logic — no Qt, no
real clock, no manager instances needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from core.daily_occasions import (
    calendar_events_today,
    is_birthday_today,
    should_run_once_daily,
    should_send_checkin,
)


# ----------------------------------------------------------------------
# is_birthday_today
# ----------------------------------------------------------------------

def test_is_birthday_today_matches_month_and_day():
    assert is_birthday_today("1990-03-03", date(2026, 3, 3)) is True


def test_is_birthday_today_ignores_year():
    assert is_birthday_today("1954-03-03", date(2026, 3, 3)) is True


def test_is_birthday_today_different_day():
    assert is_birthday_today("1990-03-03", date(2026, 3, 4)) is False


def test_is_birthday_today_none_birthday():
    assert is_birthday_today(None, date(2026, 3, 3)) is False


def test_is_birthday_today_empty_string():
    assert is_birthday_today("", date(2026, 3, 3)) is False


def test_is_birthday_today_invalid_format():
    assert is_birthday_today("not-a-date", date(2026, 3, 3)) is False


# ----------------------------------------------------------------------
# calendar_events_today
# ----------------------------------------------------------------------

@dataclass
class _FakeEvent:
    date: str
    title: str = "Event"


def test_calendar_events_today_filters_matching_date():
    events = [_FakeEvent(date="2026-07-14"), _FakeEvent(date="2026-07-15")]
    result = calendar_events_today(events, "2026-07-14")
    assert result == [events[0]]


def test_calendar_events_today_no_matches():
    events = [_FakeEvent(date="2026-07-15")]
    assert calendar_events_today(events, "2026-07-14") == []


def test_calendar_events_today_empty_list():
    assert calendar_events_today([], "2026-07-14") == []


# ----------------------------------------------------------------------
# should_run_once_daily
# ----------------------------------------------------------------------

def test_should_run_once_daily_first_time_ever():
    assert should_run_once_daily(None, "2026-07-14") is True


def test_should_run_once_daily_already_ran_today():
    assert should_run_once_daily("2026-07-14", "2026-07-14") is False


def test_should_run_once_daily_ran_a_different_day():
    assert should_run_once_daily("2026-07-13", "2026-07-14") is True


# ----------------------------------------------------------------------
# should_send_checkin
# ----------------------------------------------------------------------

def test_should_send_checkin_evening_no_activity():
    now = datetime(2026, 7, 14, 19, 0)
    assert should_send_checkin(now, has_conversation_activity_today=False) is True


def test_should_send_checkin_morning_no_activity_yet_is_too_early():
    """The whole point: don't nag first thing in the morning before the user's had a chance to chat."""
    now = datetime(2026, 7, 14, 7, 0)
    assert should_send_checkin(now, has_conversation_activity_today=False) is False


def test_should_send_checkin_evening_with_activity():
    now = datetime(2026, 7, 14, 19, 0)
    assert should_send_checkin(now, has_conversation_activity_today=True) is False


def test_should_send_checkin_exactly_at_threshold_hour():
    now = datetime(2026, 7, 14, 18, 0)
    assert should_send_checkin(now, has_conversation_activity_today=False) is True
