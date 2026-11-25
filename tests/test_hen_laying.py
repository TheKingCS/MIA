"""
tests.test_hen_laying
=======================

"Why did my hens stop laying?" (core/hen_laying.py): short winter days counted from the sun for his town with the
day they're back over 14 hours, molt season by hemisphere, a young or old flock by when it came, a change in the flock
first, and his log's lay rate this week against before; with no flock it says how to add one.
"""

from datetime import date
from types import SimpleNamespace

from core import hen_laying as hl
from core import weather

LAT, LON = 39.8, -89.6  # a stand-in town (Springfield, Illinois)


def _entry(kind, day, count=0.0):
    """A flock log line."""
    return SimpleNamespace(flock_id="f1", kind=kind, date=day, count=count, pounds=0.0, cost=0.0, use="", note="")


def _context(entries, started="2024-04-01", hens=6):
    """A context with one flock and its log."""
    flock = SimpleNamespace(flock_id="f1", name="The girls", hens=hens, roosters=0, started=started)
    book = SimpleNamespace(flocks=[flock], entries_for=lambda fid: entries)
    return SimpleNamespace(flock=book, config=None)


def test_winter_daylight_and_when_its_back():
    """Late November near 40° N: under 10 hours, back over 14 in early May; June is over 14 (a sunset past midnight UTC
    stays on its day)."""
    assert hl.day_hours(LAT, LON, date(2026, 11, 24)) < 10
    back = hl.light_back(LAT, LON, date(2026, 11, 24))
    assert back is not None and back.year == 2027 and back.month == 5 and back.day <= 10
    assert hl.day_hours(LAT, LON, date(2026, 6, 21)) > 14
    assert hl.molt_season(date(2026, 10, 1), 40) and not hl.molt_season(date(2026, 10, 1), -35)


def test_the_answer_puts_a_flock_change_first_and_says_the_light(monkeypatch):
    """Birds lost last week first, then the short days with the timer light, and the lay rate from his log."""
    monkeypatch.setattr(weather, "place", lambda context: {"name": "Springfield", "lat": LAT, "lon": LON})
    monkeypatch.setattr(weather, "card", lambda context: {"high": 45, "unit": "°F", "tomorrow": {"high": 44}})
    entries = [_entry("eggs", f"2026-11-{d:02d}", 5) for d in range(1, 17)]
    entries += [_entry("eggs", f"2026-11-{d:02d}", 1) for d in range(18, 25)]
    entries.append(_entry("birds", "2026-11-18", -1))
    said = hl.say(_context(entries), date(2026, 11, 24))
    assert said.startswith("The girls: 0.17 eggs a hen a day this week, against 0.83 the four weeks before.")
    assert said.index("A change in the flock") < said.index("Short days")
    assert "timer" in said and "Molt season" in said and "Worth checking yourself" in said


def test_young_pullets_and_no_flock(monkeypatch):
    """A 12-week flock is said as too young first; no flock says how to add one."""
    monkeypatch.setattr(weather, "place", lambda context: None)
    monkeypatch.setattr(weather, "card", lambda context: {})
    said = hl.say(_context([], started="2026-09-01"), date(2026, 11, 24))
    assert "about 12 weeks old" in said and "Tell me your town" in said
    assert hl.say(SimpleNamespace(flock=None)).startswith("No flock in MIA yet")
