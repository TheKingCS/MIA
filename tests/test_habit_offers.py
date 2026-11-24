"""
tests.test_habit_offers
=========================

Routines offered from his habits (core/habit_offers.py, DEC-0294): the same kind of thing on the same weekday three
weeks running, from his own doing, offered as a weekly reminder once ever, never what MIA did herself or an email
brought; one counts as offered only once the gate let it through, tried once a day until then.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from core import habit_offers as ho

TODAY = date(2026, 11, 23)  # a Monday


def _event(kind, day, source="manual"):
    """One event in his history: its kind, that day at six in the evening, where it came from."""
    return SimpleNamespace(type=kind, at=day.isoformat() + "T18:00:00", source=source)


def _mondays(n, kind="workout_logged", source="manual"):
    """The same kind of event on each of the last `n` Mondays."""
    return [_event(kind, TODAY - timedelta(days=7 * i), source) for i in range(1, n + 1)]


def test_three_weeks_running_on_one_weekday_is_a_habit():
    assert ho.habits(_mondays(3), TODAY) == [("workout_logged", 0)]
    assert ho.habits(_mondays(2), TODAY) == []  # two weeks isn't three


def test_what_mia_did_herself_is_no_habit_of_his():
    """Neither what she ran on a standing yes nor what an email brought each week."""
    assert ho.habits(_mondays(3, source="mia"), TODAY) == []
    assert ho.habits(_mondays(3, source="email"), TODAY) == []  # an emailed receipt each week is no habit of his


class _Gate:
    """The communication gate's log, as much as habit offers read of it."""

    def __init__(self):
        """An empty log."""
        self.log = []

    def entries_since(self, since):
        """The decisions logged at or after `since`."""
        return [e for e in self.log if e["at"] >= since]


def _ctx(monkeypatch):
    """A context whose history holds three Monday workouts, with settings in a dict and the gate's log."""
    import core.life_events as life_events

    monkeypatch.setattr(life_events, "events_for", lambda context, since=None: _mondays(3))
    store = {}
    config = SimpleNamespace(get=lambda k, d=None: store.get(k, d), set=lambda k, v: store.__setitem__(k, v))
    return SimpleNamespace(config=config, communication=_Gate())


def test_it_is_offered_once_ever_once_it_reached_him(monkeypatch):
    ctx = _ctx(monkeypatch)
    [said] = ho.offer(ctx, datetime(2026, 11, 23, 19))
    assert said.topic == "habit_offer" and "every Monday" in said.message
    assert "won't bring this one up again" in said.message
    ctx.communication.log.append({"at": "2026-11-23T19:00:00", "topic": "habit_offer", "title": said.title,
                                  "action": "act"})
    assert ho.offer(ctx, datetime(2026, 11, 30, 19)) == []  # never again


def test_one_the_gate_held_back_is_tried_again_another_day_never_lost(monkeypatch):
    import core.life_events as life_events

    ctx = _ctx(monkeypatch)
    week = _mondays(3) + [_event("workout_logged", TODAY)]  # and this Monday too, so it still holds tomorrow
    monkeypatch.setattr(life_events, "events_for", lambda context, since=None: week)
    [said] = ho.offer(ctx, datetime(2026, 11, 23, 19))
    ctx.communication.log.append({"at": "2026-11-23T19:00:00", "topic": "habit_offer", "title": said.title,
                                  "action": "drop"})
    assert ho.offer(ctx, datetime(2026, 11, 23, 19, 5)) == []  # one try a day
    [again] = ho.offer(ctx, datetime(2026, 11, 24, 19))
    assert again.title == said.title
