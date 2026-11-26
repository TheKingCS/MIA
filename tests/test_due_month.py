"""
tests.test_due_month
======================

"What's due this month?" (core/assistant_today_actions.due_through, the live sweep 2026-11-26): overdue first, then
each day to the month's end, alarms out; "bills" keeps the budget's; the words reach it in code.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_today_actions, assistant_turn, today


def test_the_month_to_its_end_overdue_first(monkeypatch):
    asked = []

    def days(context, day=None, days=7):
        asked.append(days)
        return [{"date": "2026-11-26", "items": [{"module_id": "budget", "record_id": "b1", "title": "Pay Electric",
                                                  "when": "overdue", "time": ""},
                                                 {"module_id": "toolbox", "record_id": None, "title": "Wake Up",
                                                  "when": "today", "time": "07:00", "detail": "alarm"}]},
                {"date": "2026-11-29", "items": [{"module_id": "maintenance", "record_id": "m1", "title": "Oil change",
                                                  "when": "today", "time": ""}]}]

    monkeypatch.setattr(today, "week_days", days)
    said = assistant_today_actions.due_through(None, "what's due this month", date(2026, 11, 26))
    assert asked == [5], "the 26th through the 30th"
    assert "Pay Electric" in said and "Oil change" in said and "Wake Up" not in said
    bills = assistant_today_actions.due_through(None, "what bills are due this month", date(2026, 11, 26))
    assert "Pay Electric" in bills and "Oil change" not in bills


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(assistant_today_actions, "due_through", lambda c, w, t=None: "the month")
    for words in ("What's due this month?", "what bills are due this month", "what's coming up in the next 30 days"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the month", words
