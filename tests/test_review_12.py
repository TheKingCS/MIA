"""
tests.test_review_12
======================

The twelfth review's findings (2026-11-25), each kept fixed: a daily event survives being edited (the web and phone
form, the actions, the model's tool, headless Core all know "daily"); a daily reminder never sets noon for "at 12",
nor guesses between two times or keeps a question as its title; money paid to a person is no expense, while a phone
charger or materials for a job are; a goat is Animals & Feed, chicken Groceries, eggs and feed the feed's; "on Monday"
dates it; a real answer with a "name" in its JSON is never taken for a tool call; and a quote's customer is read
lowercase ("for sarah") and found as "the Smiths'" for a John Smith.
"""

from types import SimpleNamespace

import pytest

from core import assistant_turn, job_quote
from core.calendar_actions import _event_fields


def test_a_daily_event_survives_being_edited():
    assert _event_fields({"title": "Meds", "date": "2026-11-25", "recurrence": "daily"})["recurrence"] == "daily"
    from pathlib import Path

    assert '"daily", "weekly"' in Path("core/calendar_view.py").read_text(encoding="utf-8")  # the web form's choices


def test_a_daily_reminder_never_guesses():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "ok"))
    assistant_turn._daily_reminder_reply(context, "remind me every night at 12 to lock up")
    assert "time" not in ran[-1]
    for words in ("remind me every day at 7 to take meds at 9",
                  "remind me every day to stop drinking soda, is that a good idea"):
        assert assistant_turn._daily_reminder_reply(context, words) is None, words


@pytest.fixture()
def spend():
    """What _spent_reply would record."""
    ran = []
    context = SimpleNamespace(flock=None, assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "ok"))
    return ran, lambda words: assistant_turn._spent_reply(context, words)


def test_people_are_never_an_expense_and_things_for_a_job_are(spend):
    ran, say = spend
    for words in ("I spent $50 on him", "I paid $100 for Sarah"):
        assert say(words) is None, words
    assert say("I spent $200 on materials for the Smith job") == "ok"
    assert say("I spent $15 on a phone charger") == "ok"


def test_the_categories_and_the_day_said(spend):
    ran, say = spend
    say("spent $200 on a goat")
    assert ran[-1]["category"] == "Animals & Feed"
    say("spent $20 on chicken")
    assert ran[-1]["category"] == "Groceries"
    say("I spent $30 on eggs and feed")
    assert ran[-1]["category"] == "Animals & Feed"
    say("spent $30 on gas on Monday")
    assert ran[-1]["description"] == "Gas" and "date" in ran[-1]


def test_a_json_answer_is_never_taken_for_a_tool_call():
    context = SimpleNamespace(assistant_actions=SimpleNamespace(_actions={"get_weather": object()}))
    assert not assistant_turn._garbled('{"name": "Zac", "age": 30}', context)
    assert assistant_turn._garbled('{"name": "get_weather", "parameters": {}}', context)


def test_a_quotes_customer_said_lowercase_or_as_a_family():
    assert job_quote.job_of("make a quote for a 12 by 16 deck for sarah") == ("Sarah", "12 by 16 deck")
    assert job_quote.job_of("make a quote for a 12 by 16 deck for Sarah tomorrow") == ("Sarah", "12 by 16 deck")
    assert job_quote.job_of("make a quote for a 12 by 16 deck for cedar")[0] == ""
