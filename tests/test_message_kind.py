"""Intent before action, watched first: what kind of message it is, sorted in code (core/message_kind.py, T-0009)."""

import json

import pytest

from core import message_kind as mk


@pytest.mark.parametrize("text,kind", [
    ("Add eggs to the grocery list.", "command"),
    ("Please remind me to call the dentist tomorrow", "command"),
    ("What's the difference between RAM and storage?", "question"),
    ("Morning MIA.", "chat"),
    ("Hey, you there?", "chat"),
    ("Ugh, the printer jammed again.", "frustration"),
    ("I'm feeling kind of overwhelmed.", "feeling"),
    ("Tell me something funny.", "humor"),
    ("Any ideas for something useful I could do in the next hour?", "advice"),
    ("Help me think through what to do this weekend.", "plan"),
    ("What if the power goes out for a week?", "hypothetical"),
    ("Why?", "follow-up"),
    ("It's been raining all week.", "observation"),
])
def test_each_kind_of_message_is_sorted(text, kind):
    assert mk.sort(text) == kind


def test_a_word_inside_another_word_does_not_count():
    assert mk.sort("Walk me through the wiring diagram.") != "frustration"  # "ugh" in "through"


def test_a_short_question_after_her_reply_is_a_follow_up():
    assert mk.sort("what about the roof?", previous="The walls take a weekend.") == "follow-up"


def test_every_sorted_kind_is_one_of_the_kinds():
    for text in ("", "hello", "set a timer", "I want to build a shed", "joke please"):
        assert mk.sort(text) in mk.KINDS


def test_the_corpus_is_sorted_almost_entirely_right():
    from tools.conversation_check import CASES

    found = mk.accuracy(json.loads(CASES.read_text(encoding="utf-8"))["cases"])
    assert found["share"] >= 0.9, found["misses"]


def test_a_follow_up_agrees_with_a_question_label():
    assert mk.accuracy([{"say": "Why?", "kind": "question"}])["right"] == 1


def test_each_traced_turn_carries_its_kind(tmp_path):
    from types import SimpleNamespace

    from core import turn_trace

    rows = []
    ctx = SimpleNamespace(traces=SimpleNamespace(add=rows.append), llm=None)
    turn = SimpleNamespace(route="model", replies=["Sure."], tools_offered=[], tools_called=[], used=[])
    turn_trace.record(ctx, SimpleNamespace(conversation_id="c1", mode=""), "Add eggs to the list", turn, 0.5)
    assert rows and rows[0]["kind"] == "command"
