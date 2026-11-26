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
                                                                     ["fuel (his generator's burn rate isn't set)"]))
    said = homestead_health.line(None)
    assert said.startswith("Feed: 6 days, the lowest. Water: 9 days. Food: 23 days.")
    assert "Not counted: fuel" in said
    assert homestead_health.low_line(None) == "Running low: feed 6 days."


def test_nothing_counted_says_how_to_start(monkeypatch):
    monkeypatch.setattr(homestead_health, "days", lambda c, t=None: ({}, []))
    assert homestead_health.line(None).startswith("Nothing to count yet")


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(homestead_health, "line", lambda c, t=None: "the line")
    for words in ("How's the homestead?", "how long could we last?", "homestead status"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the line", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "how long could we last on a road trip?") is None


def test_it_reads_his_real_stores_without_failing():
    """An empty context reads as nothing counted, never an error."""
    found, missing = homestead_health.days(SimpleNamespace(), date(2026, 11, 25))
    assert isinstance(found, dict) and isinstance(missing, list)
