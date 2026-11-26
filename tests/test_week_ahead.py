"""
tests.test_week_ahead
=======================

The weekly look-ahead (core/week_ahead.py, 2026-11-25): "what does my week look like?" (get_week) ends with what the
rest of MIA knows about the coming week: a holiday, the weather against his plans, feed running out, the garden's
steps and low supplies; a part that can't be read never stops the rest.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_today_actions, today, week_ahead


def test_the_week_ends_with_what_is_coming(monkeypatch):
    monkeypatch.setattr(today, "week_days", lambda context, day=None: [
        {"date": date.today().isoformat(), "items": [{"module_id": "budget", "record_id": "b1", "title": "Pay Electric",
                                                      "when": "today", "time": ""}]}])
    monkeypatch.setattr(week_ahead, "extras", lambda c, t=None: ["Thanksgiving is Thursday.", "Frost Tuesday night."])
    said = assistant_today_actions._action_get_week(None, {})
    assert "Pay Electric" in said and said.endswith("Looking ahead: Thanksgiving is Thursday. Frost Tuesday night.")


def test_a_part_that_fails_leaves_the_rest(monkeypatch):
    def broken(context, day):
        raise RuntimeError("no forecast")

    monkeypatch.setattr(week_ahead, "_weather", broken)
    monkeypatch.setattr(week_ahead, "_holidays", lambda c, d: ["Thanksgiving is Thursday."])
    monkeypatch.setattr(week_ahead, "_feed", lambda c, d: [])
    monkeypatch.setattr(week_ahead, "_garden", lambda c, d: ["In the garden: start the onions (Friday)."])
    monkeypatch.setattr(week_ahead, "_supplies", lambda c, d: [])
    assert week_ahead.extras(None, date(2026, 11, 23)) == ["Thanksgiving is Thursday.",
                                                           "In the garden: start the onions (Friday)."]


def test_supplies_leave_the_feed_to_its_own_line(monkeypatch):
    from core import homestead_health

    monkeypatch.setattr(homestead_health, "days", lambda c, t=None: ({"Water": 4.0, "Feed": 2, "Food": 30.0}, []))
    assert week_ahead._supplies(None, date(2026, 11, 23)) == ["Running low: water 4 days."]


def test_an_empty_context_has_nothing_to_add():
    """No stores at all is no look-ahead, never an error."""
    assert isinstance(week_ahead.extras(SimpleNamespace(), date(2026, 11, 23)), list)
