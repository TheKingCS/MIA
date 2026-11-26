"""
tests.test_reports_thread
===========================

The automation conversation check's fixes (2026-11-26): "every morning tell me what's due today" kept (its question
answered in code), "and every Sunday ..." read, "what reports do you send me?" her own list, "stop the Sunday one"
that report, never the model's made-up Bank Sync report or a stop it never made.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, standing_reports, today


def test_the_reports_are_read():
    assert standing_reports.parse("every morning tell me what's due today") == {"every": "daily",
                                                                                "question": "What's due today?"}
    assert standing_reports.parse("and every Sunday tell me how my money is doing")["every"] == "sunday"


def test_due_today_is_answered_in_code(monkeypatch):
    items = [today.TodayItem(when=today.TODAY, title="Water the beds"),
             today.TodayItem(when=today.OVERDUE, title="Pay Electric", detail="3 days late")]
    monkeypatch.setattr(today, "today_items", lambda c, t=None: items)
    assert today.due_today_said(SimpleNamespace()) == "Due today: Water the beds. Overdue: Pay Electric (3 days late)."
    monkeypatch.setattr(today, "due_today_said", lambda c, t=None: "due")
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "What's due today?") == "due"


def test_list_and_stop_reach_her_tools(monkeypatch):
    ran = []
    monkeypatch.setattr(assistant_turn, "_run_own", lambda c, n, a: ran.append((n, a)) or n)
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what reports do you send me?") == "list_standing_reports"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "stop the Sunday one") == "stop_standing_report"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "stop the money report") == "stop_standing_report"
    for words in ("stop reminding me", "stop the morning report", "stop that one", "cancel the update",
                  "turn off updates"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) != "stop_standing_report", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what updates do you send me about windows") != \
        "list_standing_reports"
    assert standing_reports.parse("every Sunday tell me what's due today")["question"] == "What's due today?"
