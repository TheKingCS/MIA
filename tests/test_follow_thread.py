"""
tests.test_follow_thread
==========================

A conversation's thread (core/follow_through.thread, brainstorm round 18): a chain of follow-ups folded in turn, so
the third leans on what the first two made of the question, and "same for X" is one of them.
"""

from core import follow_through as ft


def test_a_period_then_a_thing_keeps_both():
    asked = ["How much did I spend on gas last month?", "what about this month?"]
    assert ft.thread(asked, "groceries") == "How much did I spend on groceries this month?"
    asked.append("and groceries?")
    assert ft.thread(asked, "last week") == "How much did I spend on groceries last week?"


def test_same_for_is_a_follow_up_and_a_far_thread_is_let_go():
    assert ft.follow_on("same for the truck") == "the truck"
    assert ft.follow_on("do the same for the card?") == "the card"
    assert ft.thread(["How much is my truck loan?"], "the card") == "How much is my card?"
    far = ["How much did I spend on gas last month?"] + ["what about this month?"] * 5
    assert ft.thread(far, "groceries") is None
    assert ft.thread(["cancel the dentist reminder"], "today") is None


def test_the_fable_reviews_cases():
    gas = "How much did I spend on gas last month?"
    for said in ("add milk to the list", "the truck needs gas", "remind me to get gas", "the record I hate gas prices"):
        assert ft.merged(gas, said) is None, said
    assert ft.merged("How much did I spend on stuff in the garden last month?", "groceries") is None or \
        "in the garden" not in ft.merged("How much did I spend on stuff in the garden last month?", "groceries")
    assert ft.merged(gas, "groceries in October") == "How much did I spend on groceries in October?"
    assert ft.merged("How much did I spend on gas in October?", "November") == \
        "How much did I spend on gas in November?"
