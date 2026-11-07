"""
tests.test_look_by_voice
==========================

Look asked out loud (DEC-0125, core/sight.py `wants_look`): "look at this"
opens Look with the question and the camera, since no tool can take the
photo; ordinary talk about looking at something doesn't.
"""

from core.sight import LOOK_REPLY, wants_look
from tests.engine_world import build_world


def test_asking_her_to_look_picks_the_question_to_look_with():
    """What, read or inspect, from the words."""
    assert wants_look("MIA, look at this") == "What is this?"
    assert wants_look("What am I looking at?") == "What is this?"
    assert wants_look("can you read this label for me?") == "Read this label"
    assert wants_look("Inspect this part.") == "Inspect this part"
    assert wants_look("is this worn?") == "Inspect this part"


def test_talk_about_looking_at_something_else_is_not_a_look():
    """Only the whole ask opens the camera."""
    assert wants_look("look at this week's budget") is None
    assert wants_look("what is this charge on my card?") is None
    assert wants_look("I was looking at trucks") is None


def test_saying_it_opens_look_with_the_camera(tmp_path, monkeypatch):
    """The turn answers by code and opens Look with the camera and the question, before any model."""
    from core.assistant_turn import run_assistant_turn
    from core.conversation_manager import Conversation

    w = build_world(tmp_path, monkeypatch)
    w.llm = None
    turn = run_assistant_turn(w, Conversation(conversation_id="c", title="t"), "read this label")
    assert turn.open == "look.html?camera=1&ask=Read%20this%20label" and turn.replies == [LOOK_REPLY]
