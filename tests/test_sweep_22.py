"""
tests.test_sweep_22
=====================

The live sweep's new areas (2026-11-25): the homestead's own answers by the words that are their question (why the
hens aren't laying, whether to water, how long the feed lasts, how to can a food), never the model's guesses; and
the Fable review of it: each takes only its own.
"""

from types import SimpleNamespace

from core import assistant_turn


def test_each_question_goes_to_its_own_tool():
    """The hens, the water, the feed, canning and what she may do on her own: each its tool; others none."""
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(
        _actions={"why_hens_not_laying": 1, "should_i_water": 1, "get_eggs": 1, "canning_time": 1, "list_grants": 1},
        execute=lambda c, n, a: ran.append((n, a)) or "ok"))
    for words, tool in (("Why aren't my hens laying?", "why_hens_not_laying"),
                        ("my chickens stopped laying", "why_hens_not_laying"),
                        ("Should I water the garden today?", "should_i_water"),
                        ("How much feed do I have left?", "get_eggs"),
                        ("How do I can tomatoes?", "canning_time"),
                        ("how long do I process quarts of green beans", "canning_time"),
                        ("What can you do on your own?", "list_grants")):
        assert assistant_turn._own_tool_reply(context, words) == "ok", words
        assert ran[-1][0] == tool, words
    for words in ("how do I can I help you", "why is my dog not eating", "should I paint the shed"):
        assert assistant_turn._own_tool_reply(context, words) is None, words


def test_each_own_tool_takes_only_its_own():
    """The Fable review: canning only with a food, water only the garden's, the hens only his not laying, the feed
    only the flock's now, grants said every way, a debt only with a debt word."""
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(
        _actions={"why_hens_not_laying": 1, "should_i_water": 1, "get_eggs": 1, "canning_time": 1, "list_grants": 1},
        execute=lambda c, n, a: ran.append(n) or "ok"))
    for words in ("how do I can afford a new truck", "how long do I process the payment", "should I water down the paint",
                  "do I need to water the dog", "why are my hens laying so much", "my neighbour's chickens quit laying",
                  "how much dog feed do I have", "how long will my feed last if I get 10 more hens",
                  "how much feed do I have left from last week"):
        assert assistant_turn._own_tool_reply(context, words) is None, words
    for words, tool in (("why am I not getting any eggs", "why_hens_not_laying"),
                        ("why did my hens stop laying", "why_hens_not_laying"),
                        ("do the tomatoes need water", "should_i_water"), ("is it time to water", "should_i_water"),
                        ("do I have enough feed", "get_eggs"), ("what can you do without asking me", "list_grants"),
                        ("how do I can green beans in pints", "canning_time")):
        assert assistant_turn._own_tool_reply(context, words) == "ok", words
        assert ran[-1] == tool, words
    debts = [SimpleNamespace(name="Truck Loan", balance=18250, interest_rate=6.9, minimum_payment=345)]
    assert assistant_turn._debt_line(SimpleNamespace(budget=SimpleNamespace(all_debts=lambda: debts)),
                                     "how much is my truck?") is None
