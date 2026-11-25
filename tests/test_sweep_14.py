"""
tests.test_sweep_14
=====================

The eighth live sweep's fixes (2026-11-25): a turn the model answers ends a plan's thread and "thanks" never
follows one up; "what should I plant in the spring?" is no project's picture; a reply that is only a humor example
is never said; an outlet's voltage is said in fixed safe words; his request is never her opening; the hook-size
lesson leads with the fish he asked about.
"""

from core import assistant_turn, conversation_state, lesson_answer, question_plans
from core.personality import only_example
from core.response_composer import polish


def test_thanks_is_no_follow_up():
    for words in ("Thanks, that's helpful", "thank you", "cool", "ok"):
        assert not conversation_state.looks_like_follow_up(words), words
    assert conversation_state.looks_like_follow_up("and what about them?")


def test_planting_is_no_project_picture():
    assert question_plans._not_for("project picture", "What should I plant in the spring?")
    assert not question_plans._not_for("project picture", "I'm planning a garden")


def test_a_humor_example_alone_is_never_the_answer():
    assert only_example("It's in the last place you'll look. Statistically, that's the couch.")
    assert not only_example("Carry a whistle. It's in the last place you'll look. Statistically, that's the couch.")


def test_an_outlets_voltage_is_said_safely():
    for words in ("How do I check the voltage at an outlet?", "how do I test if an outlet is live",
                  "is the outlet live?", "how do I measure voltage in my breaker panel"):
        assert assistant_turn._mains_reply(None, words) == assistant_turn.MAINS_REPLY, words
    for words in ("how do I check the voltage on a 9v battery", "how do I check the oil", "the outlet mall"):
        assert assistant_turn._mains_reply(None, words) is None, words


def test_his_request_is_never_her_opening():
    said = polish("I want to learn about tying a bowline. Make a small loop in the standing part.",
                  "Teach me how to tie a bowline")
    assert said == "Make a small loop in the standing part."


def test_the_hook_lesson_leads_with_his_fish():
    said = lesson_answer.reply(None, "What size hook should I use for catfish?")
    assert said.split(": ", 1)[1].startswith("Catfish")
