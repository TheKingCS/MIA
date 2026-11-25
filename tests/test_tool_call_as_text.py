"""
tests.test_tool_call_as_text
==============================

A tool call the model writes out as its answer is never said (live sweep, 2026-11-25: '{"name": "draft_email",
"parameters": {..."\\$$X"...}}' reached him, invalid JSON, so it was neither caught nor retried): its opening is
enough to be caught (core/llm_manager._looks_like_malformed_tool_call, so the retry without tools runs), and a reply
still shaped like one after that is replaced by a plain line (core/assistant_turn.GARBLED_REPLY).
"""

from core.assistant_turn import GARBLED_REPLY, _garbled
from core.llm_manager import _looks_like_malformed_tool_call


def test_a_tool_calls_opening_is_caught_even_when_the_json_is_broken():
    """A call's opening is caught with broken JSON; a fenced example or prose never is."""
    broken = '{"name": "draft_email", "parameters": {"subject": "Fence", "body": "The cost is \\$$X."}}'
    assert _looks_like_malformed_tool_call(broken)
    # a fenced example is an explanation, never a call (the twelfth review)
    assert not _looks_like_malformed_tool_call('```json\n{"name": "add_task", "arguments": {"title": "x"}}\n```')
    assert _looks_like_malformed_tool_call('{"name": "list_notes"}')
    for text in ("The {name} of the game is patience.", 'Here is the JSON: {"a": 1}', "A plain answer."):
        assert not _looks_like_malformed_tool_call(text), text


def test_the_turn_never_says_one():
    assert _garbled('{"name": "draft_email", "parameters": {"body": "\\$$X"}}')
    assert "didn't do it" in GARBLED_REPLY
