"""
tests.test_wrap_streaks
=========================

Hobby streaks in the evening wrap (core/evening_wrap.streaks, brainstorm round 17): a course practised today on a
streak of three days or more is named; a shorter streak, or one not practised today, isn't.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from core import evening_wrap, paths

TODAY = date(2026, 11, 25)


def _book(days):
    """A guitar path practised on each of these days back from today."""
    sessions = [{"date": (TODAY - timedelta(days=i)).isoformat(), "minutes": 20} for i in days]
    record = {"goal": "", "started": "2026-11-01", "plan": {"days_a_week": 5}, "sessions": sessions, "attempts": []}
    return SimpleNamespace(started=lambda: ["guitar"], path=lambda pid: record)


def test_a_streak_practised_today_is_named(monkeypatch):
    program = SimpleNamespace(id="guitar", name="Guitar", stages=[], drafted=False, check=lambda k: None)
    monkeypatch.setattr(paths, "program_of", lambda c, pid: program)
    monkeypatch.setattr(paths, "stage_of", lambda b, p: SimpleNamespace(number=1, name="Start"))
    monkeypatch.setattr(paths.PathBook, "best", lambda self, a, b: None, raising=False)
    book = _book(range(4))
    book.best = lambda a, b: None
    book.passed = lambda a, b: False
    assert evening_wrap.streaks(SimpleNamespace(paths=book), TODAY) == "Guitar: 4 days in a row."
    short = _book(range(2))
    short.best, short.passed = book.best, book.passed
    assert evening_wrap.streaks(SimpleNamespace(paths=short), TODAY) == ""
    not_today = _book(range(1, 5))
    not_today.best, not_today.passed = book.best, book.passed
    assert evening_wrap.streaks(SimpleNamespace(paths=not_today), TODAY) == ""
