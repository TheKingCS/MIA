"""
tests.test_standing_reports
=============================

His questions answered on a schedule (core/standing_reports.py, the automation sweep 2026-11-26): read from his
words, kept only when her code can answer them, sent on their day once through the gate, stopped by his words.
"""

from datetime import datetime
from types import SimpleNamespace

from core import assistant_turn, standing_reports as sr


def test_his_words_are_read_into_a_schedule_and_a_question():
    assert sr.parse("Every Sunday tell me what's due this week") == {"every": "sunday",
                                                                     "question": "What's due this week?"}
    assert sr.parse("Every month tell me how much I spent") == {"every": "monthly",
                                                                "question": "How much did I spend last month?"}
    assert sr.parse("tell me how my money looks every friday")["question"] == "How's my money this week?"
    assert sr.parse("Tell me every morning if it's going to freeze") is None, "a watch, not a report"
    assert sr.parse("tell me a joke") is None


def test_it_is_kept_only_when_her_code_answers_it(monkeypatch, tmp_path):
    context = SimpleNamespace()
    context.standing_reports = sr.ReportList(context, data_dir=tmp_path)
    monkeypatch.setattr(sr, "answer", lambda c, q: "Due: Electric." if "due" in q.lower() else None)
    said = sr._add_execute(context, {"words": "Every Sunday tell me what's due this week"})
    assert said.startswith('I\'ll send you every Sunday: "What\'s due this week?"')
    assert 'Say "stop the Sunday report"' in said
    assert sr._stop_tool(context, {"question": "stop the sunday report"}).startswith("Stopped")
    try:
        sr._made(context, {"words": "every Monday tell me the meaning of life"})
        raise AssertionError("a question her code can't answer is never kept")
    except sr.ActionError as problem:
        assert "can't answer" in str(problem)


def test_it_is_sent_on_its_day_once(monkeypatch, tmp_path):
    context = SimpleNamespace()
    reports = sr.ReportList(context, data_dir=tmp_path)
    context.standing_reports = reports
    reports.add(sr.Report("r1", "sunday", "What's due this week?"))
    monkeypatch.setattr(sr, "answer", lambda c, q: "Due: Electric.")
    assert sr.offer(context, datetime(2026, 11, 28, 9)) == [], "a Saturday"
    assert sr.offer(context, datetime(2026, 11, 29, 6)) == [], "before the hour"
    sent = sr.offer(context, datetime(2026, 11, 29, 9))
    assert len(sent) == 1 and sent[0].topic == "standing_report" and sent[0].message == "Due: Electric."
    assert sr.offer(context, datetime(2026, 11, 29, 12)) == [], "once in its period"


def test_the_words_reach_it_and_a_freeze_goes_to_the_watch(monkeypatch):
    ran = []
    actions = SimpleNamespace(execute=lambda c, name, args: ran.append(name) or "kept")
    context = SimpleNamespace(assistant_actions=actions)
    assert assistant_turn._own_tool_reply(context, "Every Sunday tell me what's due this week") == "kept"
    assert ran[-1] == "keep_standing_report"
    from core import condition_watch

    assert condition_watch.parse("Tell me every morning if it's going to freeze")["standing"] is True
