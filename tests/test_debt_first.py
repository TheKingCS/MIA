"""
tests.test_debt_first
=======================

"Should I pay off the card or the truck first?" (the live sweep, 2026-11-26: "put extra toward #1"): his own debts
by name, the two he named compared, in code.
"""

from types import SimpleNamespace

from core import assistant_domain_actions as dom
from core import assistant_turn


def _ranked():
    card = SimpleNamespace(name="Chase Freedom", balance=4200.0, debt_type="Credit Card")
    truck = SimpleNamespace(name="Truck Loan", balance=18250.0, debt_type="Auto Loan")
    return [SimpleNamespace(debt=card, rank=1, effective_apr=24.99, reason="Highest current APR (24.99%)"),
            SimpleNamespace(debt=truck, rank=2, effective_apr=6.9, reason="Highest current APR (6.90%)")]


def test_the_two_he_names_are_compared_by_name():
    context = SimpleNamespace(budget=SimpleNamespace(debt_payoff_priority=lambda strategy="hybrid": _ranked()))
    said = dom._action_get_debt_payoff_plan(context, {"question": "Should I pay off the card or the truck first?"})
    assert said == ("Chase Freedom first: highest current APR (24.99%), against Truck Loan at 6.9%. Pay the minimums on "
                    "both and put any extra on Chase Freedom.")
    whole = dom._action_get_debt_payoff_plan(context, {})
    assert whole.startswith("Pay the minimums on everything, then put extra toward Chase Freedom ($4,200.00)")
    assert "#" not in whole


def test_the_words_reach_it():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(n) or "the order"))
    for words in ("Should I pay off the card or the truck first?", "which debt should I pay off first",
                  "what should I pay off first?"):
        assert assistant_turn._own_tool_reply(context, words) == "the order", words
