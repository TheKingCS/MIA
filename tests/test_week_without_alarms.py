"""
tests.test_week_without_alarms
================================

The week said by voice (get_week, and the weekend plan through it) never lists an alarm as something due (the live
sweep, 2026-11-25: the weekend plan said "you've got to pay your electric bill and wake up on time"); the evening
wrap and the morning briefing leave alarms out the same way.
"""

from datetime import date

from core import assistant_today_actions, today


def test_an_alarm_is_never_something_due_this_week(monkeypatch):
    """An alarm is left out of the week; a bill and a task (the toolbox's too) stay."""
    days = [{"date": date.today().isoformat(), "items": [
        {"module_id": "budget", "record_id": "b1", "title": "Pay Electric", "when": "today", "time": ""},
        {"module_id": "toolbox", "record_id": None, "title": "Wake Up", "when": "today", "time": "07:00",
         "detail": "alarm"},
        {"module_id": "toolbox", "record_id": "t1", "title": "Call the vet", "when": "today", "time": "",
         "detail": "due today"}]}]
    monkeypatch.setattr(today, "week_days", lambda context, day=None: days)
    said = assistant_today_actions._action_get_week(None, {})
    # a task shares the toolbox with alarms and stays (the thirteenth review: every task had been dropped)
    assert "Pay Electric" in said and "Call the vet" in said and "Wake Up" not in said
