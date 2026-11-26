"""
tests.test_last_done
======================

"When did I last change the oil?" from his maintenance record, and "remind me in 2 hours to check the oven" with the
clock worked out in code (core/reminders_view, the full sweep 2026-11-26).
"""

from datetime import date, datetime
from types import SimpleNamespace

from core import assistant_turn, reminders_view


def _maintenance():
    truck = SimpleNamespace(asset_id="a1", name="Truck")
    tasks = [SimpleNamespace(title="Oil change", asset_id="a1", last_completed="2026-11-05"),
             SimpleNamespace(title="Renew tags", asset_id="a1", last_completed=None)]
    return SimpleNamespace(all_tasks=lambda: tasks, get_asset=lambda aid: truck)


def test_when_it_was_last_done_from_the_record():
    context = SimpleNamespace(maintenance=_maintenance())
    said = reminders_view.last_done(context, "change the oil", date(2026, 11, 26))
    assert said == "Oil change (Truck): last done November 5, 2026, 21 days ago."
    assert "never logged as done" in reminders_view.last_done(context, "renew the tags on the truck", date(2026, 11, 26))
    assert reminders_view.last_done(context, "go fishing", date(2026, 11, 26)) is None
    assert reminders_view.last_done(context, "changed the oil", date(2026, 11, 26)).startswith("Oil change (Truck)")
    assert reminders_view.last_done(context, "get the oil changed", date(2026, 11, 26)).startswith("Oil change")
    assert '("I did the renew tags")' in reminders_view.last_done(context, "renew the tags", date(2026, 11, 26))
    assert reminders_view.last_done(context, "run", date(2026, 11, 26)) is None


def test_spoken_amounts_are_read():
    assert reminders_view.minutes_in("an hour and a half") == 90
    assert reminders_view.minutes_in("2 hours and 30 minutes") == 150
    assert reminders_view.minutes_in("a half hour") == 30
    assert reminders_view.minutes_in("six hours") == 360


def test_in_two_hours_is_worked_out_in_code():
    ran = []
    actions = SimpleNamespace(execute=lambda c, name, args: ran.append((name, args)) or "Alarm 'Check the oven' set.")
    context = SimpleNamespace(assistant_actions=actions)
    said = reminders_view.in_a_while(context, "2", "hours", "check the oven", datetime(2026, 11, 26, 16, 5))
    assert ran == [("add_alarm", {"label": "Check the oven", "time": "18:05"})]
    assert said == "Alarm 'Check the oven' set."
    late = reminders_view.in_a_while(context, "90", "minutes", "lock up", datetime(2026, 11, 26, 23, 0))
    assert "tomorrow" in late


def test_the_words_reach_them(monkeypatch):
    monkeypatch.setattr(reminders_view, "last_done", lambda c, w, t=None: "last")
    monkeypatch.setattr(reminders_view, "in_a_while", lambda c, a, u, w, n=None: "later")
    ask = lambda w: assistant_turn._own_tool_reply(SimpleNamespace(), w)  # noqa: E731
    assert ask("When did I last change the oil?") == "last"
    assert ask("Remind me in 2 hours to check the oven") == "later"
    assert ask("remind me in half an hour to flip the brisket") == "later"
    assert ask("can you remind me in an hour and a half to call mom?") == "later"


def test_when_he_last_worked_out_from_his_history(monkeypatch):
    from core import life_events

    events = [SimpleNamespace(event_id="e1", type="workout_logged", at="2026-11-20T08:00:00", summary="Back squat 3x10"),
              SimpleNamespace(event_id="e2", type="workout_logged", at="2026-11-24T08:00:00", summary="Bench 3x8"),
              SimpleNamespace(event_id="u1", type="undone", at="2026-11-24T09:00:00", summary="")]
    monkeypatch.setattr(life_events, "events_for", lambda c, types=None, **k: events)
    monkeypatch.setattr(life_events, "reversed_ids", lambda evs: {"e2"})
    said = reminders_view.last_in_history(None, "work out", date(2026, 11, 26))
    assert said == "You last worked out on Friday, November 20 (6 days ago): Back squat 3x10."
    monkeypatch.setattr(life_events, "events_for", lambda c, types=None, **k: [])
    assert reminders_view.last_in_history(None, "collect eggs", date(2026, 11, 26)).startswith("I don't have a time")
    assert reminders_view.last_in_history(None, "see my mom", date(2026, 11, 26)) is None
