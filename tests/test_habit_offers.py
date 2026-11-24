"""
tests.test_habit_offers
=========================

Routines offered from his habits (core/habit_offers.py, DEC-0294): the same kind of thing on the same weekday three
weeks running, from his own doing, offered as a weekly reminder once ever, never what MIA did herself.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from core import habit_offers as ho

TODAY = date(2026, 11, 23)  # a Monday


def _event(kind, day, source="manual"):
    return SimpleNamespace(type=kind, at=day.isoformat() + "T18:00:00", source=source)


def _mondays(n, kind="workout_logged", source="manual"):
    return [_event(kind, TODAY - timedelta(days=7 * i), source) for i in range(1, n + 1)]


def test_three_weeks_running_on_one_weekday_is_a_habit():
    assert ho.habits(_mondays(3), TODAY) == [("workout_logged", 0)]
    assert ho.habits(_mondays(2), TODAY) == []  # two weeks isn't three


def test_what_mia_did_herself_is_no_habit_of_his():
    assert ho.habits(_mondays(3, source="mia"), TODAY) == []


def test_it_is_offered_once_ever(monkeypatch):
    import core.life_events as life_events

    monkeypatch.setattr(life_events, "events_for", lambda context, since=None: _mondays(3))
    store = {}
    ctx = SimpleNamespace(config=SimpleNamespace(get=lambda k, d=None: store.get(k, d),
                                                 set=lambda k, v: store.__setitem__(k, v)))
    [said] = ho.offer(ctx, datetime(2026, 11, 23, 19))
    assert said.topic == "habit_offer" and "every Monday" in said.message
    assert "won't bring this one up again" in said.message
    assert ho.offer(ctx, datetime(2026, 11, 30, 19)) == []  # never again
