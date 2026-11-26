"""
tests.test_follow_through
===========================

A short follow-up to a code answer, made whole (core/follow_through.py, the live sweep 2026-11-26): a period for a
period, a thing for a thing, answered by the same code; "my card" is his one credit card.
"""

from types import SimpleNamespace

from core import assistant_turn, follow_through


def test_the_follow_up_is_joined_to_his_last_question():
    assert follow_through.follow_on("What about this month?") == "this month"
    assert follow_through.follow_on("And the card?") == "the card"
    assert follow_through.follow_on("thanks, that's helpful") is None
    assert follow_through.merged("How much did I spend last month?", "this month") == "How much did I spend this month?"
    assert follow_through.merged("How much is my truck loan?", "the card") == "How much is my card?"
    assert follow_through.merged("How many cutting boards do I have?", "the bowls") == "How many bowls do I have?"
    assert follow_through.merged("What's the weather tomorrow?", "the garden") is None
    assert follow_through.merged("cancel the dentist reminder", "today") is None, "never a command re-run"
    assert follow_through.merged("How much is my truck loan?", "the mortgage") == "How much do I owe on my mortgage?"
    assert follow_through.merged("How much feed do I have left?", "water") == "How much water do I have left?"
    assert follow_through.merged("How many days until Christmas?", "until New Year's") == \
        "How many days until New Year's?"
    assert follow_through.merged("What's the square footage of a 12 by 16 shed?", "a 10 by 12") == \
        "What's the square footage of a 10 by 12 shed?"


def test_thinking_of_building_offers_what_she_can_work_out():
    said = assistant_turn._own_tool_reply(SimpleNamespace(), "I'm thinking about building a chicken coop")
    assert said.startswith("Good project. I can work out a chicken coop's materials")
    assert 'Say "materials for a 4 by 8 chicken coop" and I\'ll do it' in said
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "I'm thinking about building a business") is None


def test_and_the_card_after_the_truck_loan_reads_his_card():
    card = SimpleNamespace(name="Chase Freedom", balance=4200.0, interest_rate=24.99, minimum_payment=95.0,
                           debt_type="Credit Card")
    truck = SimpleNamespace(name="Truck Loan", balance=18250.0, interest_rate=6.9, minimum_payment=455.0,
                            debt_type="Auto Loan")
    context = SimpleNamespace(budget=SimpleNamespace(all_debts=lambda: [card, truck]))
    conversation = SimpleNamespace(messages=[SimpleNamespace(role="user", content="How much is my truck loan?"),
                                             SimpleNamespace(role="assistant", content="Truck Loan: ..."),
                                             SimpleNamespace(role="user", content="And the card?")])
    said = assistant_turn._follow_through_reply(context, conversation, "And the card?")
    assert said == "Chase Freedom: $4,200.00 left at 24.99%, $95.00 a month minimum."
