"""
tests.test_sweep_20
=====================

The fourteenth live sweep's fixes (2026-11-25): a product or material is found by its name as a plural too ("I sold 2
cutting boards"); extra on a debt he names goes to that debt, its payoff said both ways; "did I pay the electric
bill?" and "how many cutting boards do I have?" are read from his records; a debt's balance is never what he can
afford.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from core import assistant_turn, question_plans
from core.assistant_tools import by_name


def test_a_record_by_its_name_a_plural_too():
    boards = [SimpleNamespace(name="Cutting Board"), SimpleNamespace(name="Bench")]
    assert by_name(boards, "cutting boards").name == "Cutting Board"
    assert by_name(boards, "benches").name == "Bench"
    assert by_name(boards, "birdhouse") is None


def test_a_bill_paid_and_a_products_stock():
    bill = SimpleNamespace(name="Electric", bill_id="e", due_date=(date.today() + timedelta(days=3)).isoformat(),
                           last_paid_date="", recurrence="monthly", paid=False)
    context = SimpleNamespace(budget=SimpleNamespace(all_bills=lambda: [bill]),
                              products=SimpleNamespace(all_products=lambda: [SimpleNamespace(name="Cutting Board",
                                                                                            quantity=3)]))
    said = assistant_turn._records_reply(context, "Did I pay the electric bill?")
    assert said is not None and said.startswith(("Not yet", "Yes"))
    assert assistant_turn._records_reply(context, "How many cutting boards do I have?") == "3 Cutting Boards on hand."
    assert assistant_turn._records_reply(context, "how many kids do I have?") is None


def test_a_debts_balance_is_never_what_he_can_afford():
    assert question_plans._not_for("afford", "How much is my truck loan?")
