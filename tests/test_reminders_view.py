"""
tests.test_reminders_view
===========================

His reminders and the everyday turns around them (core/reminders_view.py, the live sweep 2026-11-26): listed with
the calendar's and the alarms, one cancelled by its words (never all at once), "good morning" back in kind with the
day, and yesterday from his history.
"""

from datetime import date, datetime
from types import SimpleNamespace

from core import assistant_turn, reminders_view

TODAY = date(2026, 11, 26)


def _context(ran=None):
    events = [SimpleNamespace(title="Check the oil", date="2026-11-27", time=None, recurrence="weekly"),
              SimpleNamespace(title="Call the vet", date="2026-11-27", time="09:00", recurrence=None),
              SimpleNamespace(title="Old thing", date="2026-01-01", time=None, recurrence=None)]
    alarms = [SimpleNamespace(label="Wake Up", time="07:00", enabled=True)]
    actions = SimpleNamespace(execute=lambda c, n, a: (ran.append((n, a)) if ran is not None else None) or "Deleted.")
    return SimpleNamespace(calendar=SimpleNamespace(all_events=lambda: events),
                           alarms=SimpleNamespace(all_alarms=lambda: alarms), assistant_actions=actions)


def test_the_reminders_are_listed_with_the_calendars():
    said = reminders_view.listing(_context(), TODAY)
    assert said == "Your reminders: Check the oil (every week); Call the vet (tomorrow at 09:00); the Wake Up alarm at 07:00."


def test_one_is_cancelled_by_its_words_never_all_at_once():
    ran = []
    assert reminders_view.cancel(_context(ran), "the oil reminder", TODAY) == "Deleted."
    assert ran == [("delete_calendar_event", {"title": "Check the oil"})]
    said = reminders_view.cancel(_context(ran), "all reminders", TODAY)
    assert said.startswith("Your reminders:") and "Which should I cancel?" in said and len(ran) == 1


def test_good_morning_back_in_kind(monkeypatch):
    from core import morning_briefing

    monkeypatch.setattr(morning_briefing, "briefing", lambda c, now: "Good morning. Today: clear, 40.")
    assert reminders_view.greeting(None, "Good morning", datetime(2026, 11, 26, 7)) == "Good morning. Today: clear, 40."
    assert reminders_view.greeting(None, "hi", datetime(2026, 11, 26, 19)) == "Hey. What can I do for you?"


def test_the_words_reach_them(monkeypatch):
    for name in ("listing", "greeting", "yesterday", "cancel"):
        monkeypatch.setattr(reminders_view, name, lambda *a, _n=name, **k: _n)
    ask = lambda w: assistant_turn._own_tool_reply(SimpleNamespace(), w)  # noqa: E731
    assert ask("What reminders do I have?") == "listing"
    assert ask("Good morning") == "greeting" and ask("hey mia") == "greeting"
    assert ask("What did I do yesterday?") == "yesterday"
    assert ask("Cancel the oil reminder") == "cancel" and ask("Turn off all reminders") == "cancel"
    assert ask("cancel my subscription") not in ("cancel",)
    assert ask("turn off the wake up alarm") != "cancel", "silencing a ringing alarm never deletes it"
