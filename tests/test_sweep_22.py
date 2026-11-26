"""
tests.test_sweep_22
=====================

The live sweep's new areas (2026-11-25): the homestead's own answers by the words that are their question (why the
hens aren't laying, whether to water, how long the feed lasts, how to can a food), never the model's guesses.
"""

from types import SimpleNamespace

from core import assistant_turn


def test_each_question_goes_to_its_own_tool():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(
        _actions={"why_hens_not_laying": 1, "should_i_water": 1, "get_eggs": 1, "canning_time": 1},
        execute=lambda c, n, a: ran.append((n, a)) or "ok"))
    for words, tool in (("Why aren't my hens laying?", "why_hens_not_laying"),
                        ("my chickens stopped laying", "why_hens_not_laying"),
                        ("Should I water the garden today?", "should_i_water"),
                        ("How much feed do I have left?", "get_eggs"),
                        ("How do I can tomatoes?", "canning_time"),
                        ("how long do I process quarts of green beans", "canning_time")):
        assert assistant_turn._own_tool_reply(context, words) == "ok", words
        assert ran[-1][0] == tool, words
    for words in ("how do I can I help you", "why is my dog not eating", "should I paint the shed"):
        assert assistant_turn._own_tool_reply(context, words) is None, words
