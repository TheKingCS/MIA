"""
tests.test_money_left
=======================

The money conversation check's fixes (2026-11-26): "how much is left this month?" from the month's records (the model
had made up a starting balance), "can I afford a $300 chainsaw?" reaching the afford check, and "what bills are still
due?" the month's due list with the debts' minimums; "I paid the electric bill" marks that bill paid; never a bare
"how much is left?" as money unless her last reply was about money.
"""

from types import SimpleNamespace

from core import assistant_turn, money_periods


def test_the_words_reach_their_answers(monkeypatch):
    monkeypatch.setattr(money_periods, "afford", lambda c, a, t=None: f"afford[{a}]")
    for words in ("how much is left this month?", "how much money do I have left?", "what's left after the bills?",
                  "hey mia, how much is left this month?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "afford[None]", words
    for words in ("how much is left?", "and what's left?", "how much do I have left?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) != "afford[None]", words
    from core import her_asks

    assert her_asks.reply(SimpleNamespace(), "Marked 'Electric' paid \u2014 recorded $120.00.", "how much is left after that?") \
        == "afford[None]"
    assert her_asks.reply(SimpleNamespace(), "Feed: 4 days left.", "how much is left?") is None
    for words, amount in (("can I afford a $300 chainsaw this month?", 300.0), ("can I afford $500?", 500.0),
                          ("can I afford to buy a $1,200 generator?", 1200.0)):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == f"afford[{amount}]", words
    for words in ("can I afford $300 a month for a truck?", "can I afford a $300 car payment?", "can I afford $300 rent?",
                  "can I afford $300 a week on feed?", "can I afford a $15 subscription?"):
        assert not str(assistant_turn._own_tool_reply(SimpleNamespace(), words) or "").startswith("afford["), words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "how much is left on my truck loan?") != "afford[None]"
    assert assistant_turn._DUE_MONTH.match("what bills are still due?")


def test_a_bill_of_his_marked_paid():
    ran = []
    bills = [SimpleNamespace(name="Electric"), SimpleNamespace(name="Water Bill")]
    context = SimpleNamespace(budget=SimpleNamespace(all_bills=lambda: bills),
                              assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "Marked."))
    for words in ("pay the electric bill", "I paid the electric bill", "mark the water bill paid"):
        assert assistant_turn._own_tool_reply(context, words) == "Marked.", words
    assert ran == [("mark_bill_paid", {"name": "Electric"}), ("mark_bill_paid", {"name": "Electric"}),
                   ("mark_bill_paid", {"name": "Water Bill"})]
    for words in ("pay attention", "I paid $85 for the electric bill", "pay the plumber"):
        assert assistant_turn._own_tool_reply(context, words) != "Marked.", words
