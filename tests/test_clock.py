"""
tests.test_clock
==================

LS-07 (DEC-0284): one clock. Now is aware of his zone (his setting, else the computer's), tests can freeze it, the week
runs Monday to Sunday, and the day a phrase means is worked out in code: the words life notes already knew, "in N
days/weeks/months", month-name and ISO dates, and "the first Saturday of March", with month ends, missing fifth
weekdays and the turn of the year handled.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from core import clock

SAID = date(2026, 11, 18)  # a Wednesday


def test_now_is_aware_of_his_zone_and_his_setting_wins():
    assert clock.now().tzinfo is not None
    config = SimpleNamespace(get=lambda key, default=None: "Asia/Tokyo" if key == clock.SETTING else default)
    assert str(clock.zone(SimpleNamespace(config=config))) == "Asia/Tokyo"
    unknown = SimpleNamespace(get=lambda key, default=None: "Not/AZone")
    assert clock.zone(SimpleNamespace(config=unknown)) is not None  # an unknown name is the computer's zone


def test_a_frozen_clock_holds_now_and_today_and_lets_go_after():
    moment = datetime(2026, 11, 18, 23, 59, 30, tzinfo=timezone.utc)
    with clock.frozen(moment):
        assert clock.now() == moment and clock.today() == date(2026, 11, 18)
    assert clock.now() != moment


def test_the_week_runs_monday_to_sunday():
    assert clock.week_of(SAID) == (date(2026, 11, 16), date(2026, 11, 22))


@pytest.mark.parametrize("phrase,expected", [
    ("tomorrow", date(2026, 11, 19)), ("by friday", date(2026, 11, 20)), ("next wednesday", date(2026, 11, 25)),
    ("in 3 days", date(2026, 11, 21)), ("in two weeks", date(2026, 12, 2)), ("in a month", date(2026, 12, 18)),
    ("March 5", date(2027, 3, 5)), ("the 5th of december", date(2026, 12, 5)), ("November 18", date(2026, 11, 18)),
    ("2026-12-01", date(2026, 12, 1)), ("the first saturday of march", date(2027, 3, 6)),
    ("the last friday of november", date(2026, 11, 27)), ("on December 25th", date(2026, 12, 25)),
])
def test_the_day_a_phrase_means(phrase, expected):
    assert clock.parse_day(phrase, SAID) == expected


@pytest.mark.parametrize("phrase", ["someday", "when it rains", "2026-02-30", "february 30", ""])
def test_a_phrase_that_isnt_a_day_is_none_never_a_guess(phrase):
    assert clock.parse_day(phrase, SAID) is None


def test_month_ends_and_missing_fifth_weekdays():
    assert clock.parse_day("in a month", date(2026, 1, 31)) == date(2026, 2, 28)
    assert clock.nth_weekday(2026, 2, 5, 0) is None  # February 2026 has no fifth Monday
    assert clock.nth_weekday(2026, 12, -1, 4) == date(2026, 12, 25)
