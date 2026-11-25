"""
tests.test_review_13
======================

The thirteenth review's findings (2026-11-25), each kept fixed: a brand or a store (Netflix, Costco, Uber, Roundup)
is a purchase, a person only someone he knows; "on Monday" alone or "last week" is the model's to ask, never today;
his phone or a job is the bill tools'; "at 12:30" keeps its time; a tool call written as text is caught as a whole
fenced reply, with "tool"/"input", or a made-up snake_case name, while a JSON example or a fenced explanation stays;
and a quote's lowercase "for the shop" never asks him to add a customer named Shop.
"""

from types import SimpleNamespace

import pytest

from core import assistant_turn


@pytest.fixture()
def spend():
    """What _spent_reply would record, with Sarah Lee among his people."""
    ran = []
    people = SimpleNamespace(all_people=lambda: [SimpleNamespace(name="Sarah Lee")])
    context = SimpleNamespace(flock=None, relationships=people, business=None,
                              assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "ok"))
    return ran, lambda words: assistant_turn._spent_reply(context, words)


def test_a_brand_is_a_purchase_and_a_person_is_someone_he_knows(spend):
    ran, say = spend
    for words in ("I spent $40 on Netflix", "spent $60 on Costco", "bought Roundup for $25", "I paid $30 for Uber"):
        assert say(words) == "ok", words
    assert ran[1]["category"] == "Groceries"
    for words in ("I paid $100 for Sarah", "spent $20 on Sarah yesterday", "spent $30 on Monday",
                  "spent $25 on groceries last week", "I paid $85 for my phone", "I paid $300 for the job"):
        assert say(words) is None, words


def test_half_past_twelve_keeps_its_time():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "ok"))
    assistant_turn._daily_reminder_reply(context, "remind me every day at 12:30 to eat")
    assert ran[-1]["time"] == "12:30"


def test_a_tool_call_as_text_in_any_shape_and_never_an_example():
    context = SimpleNamespace(assistant_actions=SimpleNamespace(_actions={"add_task": 1}))
    for text in ('{"name": "send_email", "parameters": {}}', '{"name": "Add_Task", "parameters": {}}',
                 '```json\n{"name":"add_task","arguments":{}}\n```', '{"tool": "add_task", "input": {}}'):
        assert assistant_turn._garbled(text, context), text
    for text in ('{"name": "Zac", "age": 30}', '{"name": "Buddy", "input": 3}',
                 'Here: ```json\n{"name":"add_task","arguments":{}}\n``` is how it looks'):
        assert not assistant_turn._garbled(text, context), text


def test_a_lowercase_purpose_is_never_a_customer_to_add(monkeypatch):
    from core import assistant_correction_actions, job_quote

    monkeypatch.setattr(assistant_correction_actions, "_run", lambda c, k, p: "Added it. (Say “undo that” to take it back.)")
    context = SimpleNamespace(materials=None, business=SimpleNamespace(customers=[]))
    said = job_quote.reply(context, "write a quote for a 10 by 12 shed for the shop")
    assert "add a customer named" not in said
