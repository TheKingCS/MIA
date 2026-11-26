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
