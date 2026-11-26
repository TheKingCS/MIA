"""
tests.test_evening_noticed
============================

What she noticed today in the evening wrap (core/evening_wrap.noticed_today, brainstorm round 18): the first unusual
finding the gate sent today, named once, from the gate's own log; never one held back.
"""

from datetime import datetime
from types import SimpleNamespace

from core import evening_wrap
from core.communication_gate import ACT, DROP


def _gate(entries):
    """A gate stub with one day's log."""
    return SimpleNamespace(entries_for_day=lambda day=None: entries)


def test_the_first_sent_finding_is_named_with_how_many_more():
    gate = _gate([{"topic": "unusual", "action": DROP, "title": "Held"},
                  {"topic": "unusual", "action": ACT, "title": "Feed: more than usual", "notification_id": "n1"},
                  {"topic": "money_pulse", "action": ACT, "title": "Money"},
                  {"topic": "unusual", "action": ACT, "title": "Hens: fewer eggs", "notification_id": "n2"},
                  {"topic": "unusual", "action": ACT, "title": "Gone", "notification_id": "n3",
                   "dismissed_at": "2026-11-26T10:00:00"},
                  {"topic": "unusual", "action": ACT, "title": "Undelivered"}])
    said = evening_wrap.noticed_today(SimpleNamespace(communication=gate), datetime(2026, 11, 26).date())
    assert said == "Something I flagged today: Feed, more than usual (and 1 other thing)."


def test_nothing_sent_says_nothing_and_the_wrap_carries_it(monkeypatch):
    assert evening_wrap.noticed_today(SimpleNamespace(communication=_gate([])), datetime(2026, 11, 26).date()) == ""
    for name in ("done_today", "first_tomorrow"):
        monkeypatch.setattr(evening_wrap, name, lambda c, d: "")
    monkeypatch.setattr(evening_wrap, "weather_tomorrow", lambda c: "")
    monkeypatch.setattr(evening_wrap, "streaks", lambda c, d: "")
    gate = _gate([{"topic": "unusual", "action": ACT, "title": "Feed: more than usual", "notification_id": "n1"}])
    said = evening_wrap.wrap(SimpleNamespace(communication=gate), datetime(2026, 11, 26, 20))
    assert said == "A quiet day today. Something I flagged today: Feed, more than usual."
