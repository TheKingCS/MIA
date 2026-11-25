"""
tests.test_his_words_reach_the_tool
=====================================

A calculator whose one detail is his question (canning_time, feed_mix, bleach_for_water, meat_cure) gets his own
words, never the model's (core/tool_loop.his_words; live check, 2026-11-25: "how long do I pressure can quart jars of
green beans?" reached canning_time with the tool's own description as the question and was refused); on a follow-up,
the question it makes; and "per gallon" is one gallon for the bleach.
"""

from types import SimpleNamespace

from core import conversation_state
from core.assistant_today_actions import _action_bleach_for_water
from core.tool_loop import his_words

DESCRIPTION = "How long to process home-canned jars and at what pressure, from the USDA"


def _registry():
    """A registry holding canning_time with its prompt_arg, and a tool without one."""
    return SimpleNamespace(_actions={"canning_time": SimpleNamespace(prompt_arg="question"),
                                     "list_notes": SimpleNamespace(prompt_arg="")})


def test_the_question_detail_is_his_words_not_the_models():
    call = SimpleNamespace(name="canning_time", arguments={"question": DESCRIPTION})
    said = "How long do I pressure can quart jars of green beans?"
    assert his_words(_registry(), call, said) == {"question": said}
    other = SimpleNamespace(name="list_notes", arguments={"query": "eggs"})
    assert his_words(_registry(), other, said) == {"query": "eggs"}


def test_a_follow_up_gives_the_question_it_makes():
    conversation_state.set_turn_follow_up("And what about corn?",
                                          "And what about corn? (after: How long do I process quarts of green beans?)",
                                          "How long do I process quarts of green beans?", ("canning_time",))
    try:
        call = SimpleNamespace(name="canning_time", arguments={"question": DESCRIPTION})
        assert his_words(_registry(), call, "And what about corn?")["question"].startswith("And what about corn? (after:")
    finally:
        conversation_state.clear_turn_follow_up()


def test_per_gallon_is_one_gallon_for_the_bleach():
    said = _action_bleach_for_water(None, {"question": "How much bleach per gallon of creek water?"})
    assert "for 6% it's 8 drops" in said and "1 gal" in said
    assert _action_bleach_for_water(None, {"question": "how much bleach for my water"}).startswith("How much water")
