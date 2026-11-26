"""
tests.test_homestead_health
=============================

The homestead's health in one line (core/homestead_health.py, 2026-11-25): its days of water, food, feed and fuel, the
lowest first, what isn't counted said; "how's the homestead?" reaches it; the morning briefing names what's low.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, homestead_health


def test_the_lowest_is_said_first(monkeypatch):
    monkeypatch.setattr(homestead_health, "days", lambda c, t=None: ({"Water": 9.0, "Food": 23.0, "Feed": 6},
                                                                     ["fuel (your generator's burn rate isn't set)"]))
    said = homestead_health.line(None)
    assert said.startswith("Feed: 6 days, the lowest. Water: 9 days. Food: 23 days.")
    assert "Not counted: fuel" in said
    assert homestead_health.low_line(None) == "", "the feed is feed_runway.soon's"


def test_the_briefing_says_each_low_once_a_week(monkeypatch):
    from datetime import date as d
    from core import person_settings

    kept = {}
    monkeypatch.setattr(person_settings, "get", lambda c, k, default=None: kept.get(k, default))
    monkeypatch.setattr(person_settings, "put", lambda c, k, v: kept.__setitem__(k, v))
    monkeypatch.setattr(homestead_health, "days", lambda c, t=None: ({"Water": 3.0, "Food": 40.0}, []))
    assert homestead_health.low_line(None, d(2026, 11, 25)) == "Running low: water 3 days."
    assert homestead_health.low_line(None, d(2026, 11, 26)) == ""
    assert homestead_health.low_line(None, d(2026, 12, 2)) == "Running low: water 3 days."


def test_nothing_counted_says_how_to_start(monkeypatch):
    monkeypatch.setattr(homestead_health, "days", lambda c, t=None: ({}, []))
    assert homestead_health.line(None).startswith("Nothing to count yet")


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(homestead_health, "line", lambda c, t=None: "the line")
    for words in ("How's the homestead?", "how long could we last?", "homestead status", "Homestead status.",
                  "how's the homestead holding up", "how long will we last?", "how are we doing on supplies?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the line", words
    for words in ("how long could we last on a road trip?", "how long can I last"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) is None, words


def test_it_reads_his_real_stores_without_failing():
    """An empty context reads as nothing counted, never an error."""
    found, missing = homestead_health.days(SimpleNamespace(), date(2026, 11, 25))
    assert isinstance(found, dict) and isinstance(missing, list)
