"""
tests.test_money_left
=======================

The money conversation check's fixes (2026-11-26): "how much is left this month?" from the month's records (the model
had made up a starting balance), "can I afford a $300 chainsaw?" reaching the afford check, and "what bills are still
due?" the month's due list.
"""

from types import SimpleNamespace

from core import assistant_turn, money_periods


def test_the_words_reach_their_answers(monkeypatch):
    monkeypatch.setattr(money_periods, "afford", lambda c, a, t=None: f"afford[{a}]")
    for words in ("how much is left this month?", "and how much is left after that?", "what's left after the bills?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "afford[None]", words
    for words, amount in (("can I afford a $300 chainsaw this month?", 300.0), ("can I afford $500?", 500.0),
                          ("can I afford to buy a $1,200 generator?", 1200.0)):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == f"afford[{amount}]", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "can I afford $300 a month for a truck?") != "afford[300.0]"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "how much is left on my truck loan?") != "afford[None]"
    assert assistant_turn._DUE_MONTH.match("what bills are still due?")
