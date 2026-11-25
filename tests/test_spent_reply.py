"""
tests.test_spent_reply
========================

What he says he spent is recorded (core/assistant_turn._spent_reply; brainstorm round 14's sweep: "I spent $30 on
groceries" went to the money month's plan and nothing was kept, "spent 12 dollars on gas" got small talk): an expense
in the category its words name, undoable through add_expense; feed with its weight goes to the flock's feed log
(log_feed, core/assistant_goods_actions.py) when there's a flock; a bill, a loan or money paid to a person never.
"""

from types import SimpleNamespace

from core import assistant_turn
from core.assistant_goods_actions import _log_feed


def _context(flock=None):
    """A context recording what tool would run, with or without a flock."""
    ran = []
    return ran, SimpleNamespace(flock=flock, assistant_actions=SimpleNamespace(
        execute=lambda c, name, args: ran.append((name, args)) or "ok"))


def test_what_he_spent_becomes_an_expense_in_its_category():
    ran, context = _context()
    for words, category in (("I spent $30 on groceries", "Groceries"), ("spent 12 dollars on gas", "Transportation"),
                            ("Paid $60 for the vet visit", "Animals & Feed"),
                            ("I bought a new saw blade for $35.50", "Tools & Equipment")):
        assert assistant_turn._spent_reply(context, words) == "ok", words
        assert ran[-1][0] == "add_expense" and ran[-1][1]["category"] == category, words
    assert ran[-1][1]["amount"] == 35.5


def test_feed_with_its_weight_goes_to_the_flock_when_there_is_one():
    ran, context = _context(SimpleNamespace(flocks=["layers"]))
    assistant_turn._spent_reply(context, "bought 50 lb of layer feed for $22")
    assert ran[-1] == ("log_feed", {"pounds": 50.0, "cost": 22.0})
    assert _log_feed(SimpleNamespace(flock=None), {"pounds": 50}).startswith("No flock in MIA yet")


def test_bills_loans_people_and_questions_are_never_an_expense_here():
    ran, context = _context()
    for words in ("I paid $120 for the electric bill", "I paid $500 on the truck loan", "I paid Sarah $40 back",
                  "how much have I spent on groceries?", "I spent the day on the fence"):
        assert assistant_turn._spent_reply(context, words) is None, words
