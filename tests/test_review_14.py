"""
tests.test_review_14
======================

The fourteenth review's findings (2026-11-25), each kept fixed: "every night at 12:30" is half past midnight and
"every evening at 12:30" sets no time; a tool call is caught wherever its name sits, a fenced function-call example
is an answer; "my phone yesterday" and "the job on Monday" are still the bill tools'; a first name is a person only
written as a name ("gas" is never Gas Station Co); "my mother" is a person; and "for the Johnsons" finds the
Johnson family's customer.
"""

from types import SimpleNamespace

from core import assistant_turn


def _context():
    """Candy Lee among his people, Gas Station Co a customer, add_task and draft_email her tools; what runs kept."""
    ran = []
    return ran, SimpleNamespace(
        flock=None, relationships=SimpleNamespace(all_people=lambda: [SimpleNamespace(name="Candy Lee")]),
        business=SimpleNamespace(customers=[SimpleNamespace(name="Gas Station Co")]),
        assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "ok",
                                          _actions={"add_task": 1, "draft_email": 1}))


def test_half_past_twelve_at_night_is_after_midnight():
    ran, context = _context()
    assistant_turn._daily_reminder_reply(context, "remind me every night at 12:30 to take pills")
    assert ran[-1]["time"] == "00:30"
    assistant_turn._daily_reminder_reply(context, "remind me every evening at 12:30 to stretch")
    assert "time" not in ran[-1]


def test_a_tool_call_wherever_its_name_sits_and_never_an_example():
    ran, context = _context()
    for text in ('{"arguments": {"to": "x"}, "name": "draft_email"}', '{"type": "function", "name": "add_task", '
                 '"arguments": {}}', '{"name": "send_email", "parameters": {}}'):
        assert assistant_turn._garbled(text, context), text
    for text in ('```json\n{"name": "get_current_weather", "arguments": {}}\n```', '{"name": "my_tool", "input": 3}',
                 '{"name": "Zac", "age": 30}'):
        assert not assistant_turn._garbled(text, context), text


def test_the_bill_tools_words_and_people_with_a_day_said():
    ran, context = _context()
    for words in ("I paid $80 for my phone yesterday", "I spent $200 on the job on Monday", "I spent $50 on my mother",
                  "I spent $20 on Candy"):
        assert assistant_turn._spent_reply(context, words) is None, words
    for words in ("I spent $40 on gas", "I spent $5 on candy"):
        assert assistant_turn._spent_reply(context, words) == "ok", words


def test_the_johnsons_are_found_as_a_family(monkeypatch):
    from core import assistant_correction_actions, job_quote

    made = []
    monkeypatch.setattr(assistant_correction_actions, "_run", lambda c, k, p: made.append(p) or
                        "Added it. (Say “undo that” to take it back.)")
    context = SimpleNamespace(materials=None, business=SimpleNamespace(
        customers=[SimpleNamespace(name="Dave Johnson", customer_id="c9")]))
    job_quote.reply(context, "make a quote for a 12 by 16 deck for the Johnsons")
    assert made[-1].get("customer_id") == "c9"
