"""
tests.test_sweep_20
=====================

The fourteenth live sweep's fixes (2026-11-25): a product or material is found by its name as a plural too ("I sold 2
cutting boards"); extra on a debt he names goes to that debt, its payoff said both ways; "did I pay the electric
bill?" and "how many cutting boards do I have?" are read from his records; a debt's balance is never what he can
afford. The Fable review of it: a name is matched whole, a paid monthly bill is paid, ordinary words pick nothing.
And a debt's balance, from the first live sweep run as a command.
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
    """A bill not yet paid this time is "Not yet"; a product's stock reads its quantity_in_stock."""
    bill = SimpleNamespace(name="Electric", bill_id="e", due_date=(date.today() + timedelta(days=3)).isoformat(),
                           last_paid_date="", recurrence="monthly", paid=False)
    context = SimpleNamespace(budget=SimpleNamespace(all_bills=lambda: [bill]),
                              products=SimpleNamespace(all_products=lambda: [SimpleNamespace(name="Cutting Board",
                                                                                            quantity_in_stock=3)]))
    said = assistant_turn._records_reply(context, "Did I pay the electric bill?")
    assert said is not None and said.startswith("Not yet")
    assert assistant_turn._records_reply(context, "How many cutting boards do I have?") == "Cutting Board: 3 on hand."
    assert assistant_turn._records_reply(context, "how many kids do I have?") is None


def test_a_debts_balance_is_never_what_he_can_afford():
    assert question_plans._not_for("afford", "How much is my truck loan?")


def test_the_fable_review_of_sweep_20():
    """A sale is never put on a product named by only some of his words; a paid monthly bill is paid; the stock
    reads the Product's own field; ordinary words never pick a bill or a debt."""
    boards = [SimpleNamespace(name="Board"), SimpleNamespace(name="Charcuterie Board"), SimpleNamespace(name="Shelf")]
    for words in ("cutting boards", "walnut board", "2 cutting boards"):
        assert by_name(boards, words) is None, words
    assert by_name(boards, "2 boards").name == "Board" and by_name(boards, "shelves").name == "Shelf"
    bill = SimpleNamespace(name="Electric", due_date=(date.today() - timedelta(days=20)).isoformat(),
                           last_paid_date=date.today().isoformat(), recurrence="monthly")
    context = SimpleNamespace(budget=SimpleNamespace(all_bills=lambda: [bill]),
                              products=SimpleNamespace(all_products=lambda: [SimpleNamespace(name="Bench",
                                                                                            quantity_in_stock=2)]))
    assert assistant_turn._records_reply(context, "Did I pay the electric bill?").startswith("Yes: Electric was paid")
    assert assistant_turn._records_reply(context, "How many benches do I have?") == "Bench: 2 on hand."
    for words in ("did I pay too much for the insurance?", "did I pay the guy who fixed the water heater?",
                  "how many days of water do I have?"):
        assert assistant_turn._records_reply(context, words) is None, words
    assert question_plans._not_for("afford", "How much is my truck loan?")
    assert not question_plans._not_for("afford", "How much is the new truck and can I afford it with my loan?")


def test_a_debts_balance_is_read_from_his_debts():
    """"How much is my truck loan?" is the Truck Loan's line; "my card" with two cards is the model's."""
    debts = [SimpleNamespace(name="Truck Loan", balance=18250, interest_rate=6.9, minimum_payment=345),
             SimpleNamespace(name="Chase Freedom", balance=4200, interest_rate=24.99, minimum_payment=200)]
    context = SimpleNamespace(budget=SimpleNamespace(all_debts=lambda: debts))
    said = assistant_turn._records_reply(context, "How much is my truck loan?")
    assert said.startswith("Truck Loan: $18,250.00 left at 6.9%")
    assert assistant_turn._records_reply(context, "how much do I still owe on the chase freedom?").startswith("Chase")
    assert assistant_turn._records_reply(context, "how much is my phone?") is None
