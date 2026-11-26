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
    events = [SimpleNamespace(event_id="e1", title="Check the oil", date="2026-11-27", time=None, recurrence="weekly"),
              SimpleNamespace(event_id="e2", title="Call the vet", date="2026-11-27", time="09:00", recurrence=None),
              SimpleNamespace(event_id="e3", title="Old thing", date="2026-01-01", time=None, recurrence=None)]
    alarms = [SimpleNamespace(alarm_id="a1", label="Wake Up", time="07:00", enabled=True)]
    actions = SimpleNamespace(
        propose=lambda c, kind, params: (ran.append((kind, params)) if ran is not None else None)
        or SimpleNamespace(proposal_id="p1"),
        approve=lambda c, pid: SimpleNamespace(status="executed", result="done"))
    return SimpleNamespace(calendar=SimpleNamespace(all_events=lambda: events),
                           alarms=SimpleNamespace(all_alarms=lambda: alarms), actions=actions)


def test_the_reminders_are_listed_with_the_calendars():
    said = reminders_view.listing(_context(), TODAY)
    assert said == "Your reminders: Check the oil (every week); Call the vet (tomorrow at 09:00); the Wake Up alarm at 07:00."


def test_one_is_cancelled_by_its_words_never_all_at_once():
    ran = []
    said = reminders_view.cancel(_context(ran), "the oil reminder", TODAY)
    assert said.startswith("Cancelled Check the oil. It was a repeating one")
    assert ran == [("event.delete", {"event_id": "e1"})]
    assert reminders_view.cancel(_context(ran), "the oil change reminder", TODAY) is None, "every word, never one"
    said = reminders_view.cancel(_context(ran), "all reminders", TODAY)
    assert said.startswith("Your reminders:") and "Which should I cancel?" in said and len(ran) == 1


def test_the_automation_asks_are_never_claimed():
    said = reminders_view.stop_reminding(_context(), "take out the trash", TODAY)
    assert said.startswith("I don't have a reminder about take out the trash, so there's nothing to stop.")
    assert reminders_view.bill_reminder("pay rent").startswith("Add rent as a bill")
    assert "due the 15th" in reminders_view.bill_reminder("pay rent", "15th")
    once = assistant_turn._own_tool_reply(_context(), "remind me to pay the vet bill")
    assert not (once or "").startswith("Add vet"), "a one-off isn't a monthly bill"
    assert "no bank is linked" in reminders_view.when_paid(SimpleNamespace(), "put 10% in savings")
    ask = lambda w: assistant_turn._own_tool_reply(_context(), w)  # noqa: E731
    assert ask("Can you track my spending automatically?") == reminders_view.TRACK_SPENDING
    assert ask("Set up a routine for my mornings") == reminders_view.MORNING_ROUTINE
    assert ask("Remind me on the first of every month to pay rent").startswith("Add rent as a bill")
    assert ask("Stop reminding me to take out the trash").startswith("I don't have a reminder about")


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
