"""
MIA asks which kind of support when it isn't clear (core/support_choice.py,
wired through core/talk_it_out.pre_turn).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
from core.config_manager import ConfigManager
from core.conversation_manager import Conversation
from core.conversation_modes import COMPANION, DIRECT, LISTEN, PERSPECTIVE, PLAN
from core.support_choice import QUESTION, habit, interpret_answer, sounds_heavy
from core.talk_it_out import pre_turn


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    return SimpleNamespace(config=ConfigManager())


@pytest.mark.parametrize("text", [
    "Rough day at the plant.", "I'm so tired of this job", "Work sucks", "I'm exhausted",
    "Same thing every single day", "I'm fed up with all of it", "I can't take this anymore",
])
def test_heavy(text):
    assert sounds_heavy(text)


@pytest.mark.parametrize("text", [
    "Ugh, the mower got a new battery", "What's a rough estimate for lumber?", "Had a great day!",
    "How do I fix a flat tire?", "Add milk to the grocery list",
])
def test_not_heavy(text):
    assert not sounds_heavy(text)


def test_answers():
    assert interpret_answer("Just listen") == LISTEN
    assert interpret_answer("the second one") == PLAN
    assert interpret_answer("help me figure it out I guess") == PLAN
    assert interpret_answer("remind me why") == PERSPECTIVE
    assert interpret_answer("nah just talk") == COMPANION
    assert interpret_answer("well the thing is my boss keeps moving the targets on us every single week and nobody says anything") is None
    assert habit([PLAN, LISTEN, LISTEN, LISTEN]) == LISTEN
    assert habit([LISTEN, PLAN, LISTEN]) is None and habit([COMPANION] * 3) is None


def test_asks_once_then_uses_the_answer(ctx):
    conversation = Conversation(conversation_id="c")
    asked = pre_turn(ctx, conversation, "Rough day. Same thing every single day.")
    assert asked.fixed_reply == QUESTION and conversation.awaiting_support
    answered = pre_turn(ctx, conversation, "just listen")
    assert answered.fixed_reply is None and conversation.mode == LISTEN
    assert ctx.config.get("assistant.support_choices") == [LISTEN]
    # Not again in the same conversation soon after.
    conversation.mode = COMPANION
    assert pre_turn(ctx, conversation, "Honestly work sucks").fixed_reply is None


def test_a_mode_phrase_answer_counts_and_an_ignored_question_passes(ctx):
    conversation = Conversation(conversation_id="c")
    pre_turn(ctx, conversation, "I'm exhausted")
    pre_turn(ctx, conversation, "no bullshit, what should I do")
    assert conversation.mode == DIRECT and ctx.config.get("assistant.support_choices") == [DIRECT]
    other = Conversation(conversation_id="d")
    pre_turn(ctx, other, "I'm exhausted")
    pre_turn(ctx, other, "Anyway, what's on my calendar tomorrow?")
    assert other.mode == COMPANION and not other.awaiting_support


def test_the_usual_choice_is_used_without_asking(ctx):
    ctx.config.set("assistant.support_choices", [LISTEN, LISTEN, LISTEN])
    conversation = Conversation(conversation_id="c")
    prepared = pre_turn(ctx, conversation, "Rough day.")
    assert prepared.fixed_reply is None and conversation.mode == LISTEN
    assert prepared.notice.startswith("I'm listening.")


def test_never_while_journaling_in_a_mode_or_turned_off(ctx):
    journaling = Conversation(conversation_id="j", journal=True)
    assert pre_turn(ctx, journaling, "Rough day.").fixed_reply is None
    planning = Conversation(conversation_id="p", mode=PLAN)
    assert pre_turn(ctx, planning, "Rough day.").fixed_reply is None
    ctx.config.set("assistant.ask_support_kind", False)
    assert pre_turn(ctx, Conversation(conversation_id="x"), "Rough day.").fixed_reply is None


def test_the_safety_floor_still_comes_first(ctx):
    prepared = pre_turn(ctx, Conversation(conversation_id="c"), "Rough day, I want to kill myself")
    assert "988" in prepared.fixed_reply
