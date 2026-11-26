"""
tests.test_offered_phrase
===========================

A plain go-ahead to her own offer runs the words she said to say (core/conversation_state.offered_phrase, the live
sweep 2026-11-26): only an offer she'd carry out, only one, never an undo, stop or delete.
"""

from types import SimpleNamespace

from core.conversation_state import offered_phrase


def _talk(said):
    return SimpleNamespace(messages=[SimpleNamespace(role="user", content="What's my next guitar lesson?"),
                                     SimpleNamespace(role="assistant", content=said)])


def test_a_go_ahead_runs_her_offer():
    talk = _talk('You haven\'t started Guitar yet. Say "I want to learn guitar" and I\'ll set it up with you.')
    assert offered_phrase(talk, "Ok, start it") == "I want to learn guitar"
    assert offered_phrase(talk, "yes please") == "I want to learn guitar"
    assert offered_phrase(talk, "go ahead") == "I want to learn guitar"
    assert offered_phrase(talk, "what's a barre chord?") is None
    for ack in ("ok", "sure", "okay thanks", "sounds good"):
        assert offered_phrase(talk, ack) is None, ack


def test_never_an_undo_a_stop_or_two_offers():
    assert offered_phrase(_talk('Cancelled it. Say "undo that" and I\'ll bring it back.'), "ok") is None
    assert offered_phrase(_talk('Morning briefing on. Say "stop the morning briefing" to turn it off.'), "ok") is None
    two = 'Say "copy the list" and I\'ll copy it, or say "start woodworking" and I\'ll set it up.'
    assert offered_phrase(_talk(two), "ok") is None
    assert offered_phrase(_talk('Say one, like "set my grocery budget to $400", and I\'ll keep count.'), "ok") is None
