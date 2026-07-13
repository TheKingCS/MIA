"""
tests.test_assistant_module
=============================

Unit tests for modules.assistant.module's pure logic — format_chat_line
and looks_like_action_request — no Qt event loop needed. Same shape as
tests/test_notes_module.py's format_entry_row test: the widget-building
and worker-thread wiring in AssistantModule needs a real Qt event loop
to exercise meaningfully, so that was verified with a manual headless
smoke test instead (offscreen QPA platform) rather than unit-tested
here.
"""

from __future__ import annotations

from modules.assistant.module import format_chat_line, looks_like_action_request


def test_formats_speaker_and_text():
    assert format_chat_line("You", "hello") == "You: hello"


def test_formats_assistant_reply():
    assert format_chat_line("Assistant", "hi there") == "Assistant: hi there"


# ----------------------------------------------------------------------
# looks_like_action_request
# ----------------------------------------------------------------------
# Regression coverage for a real-usage bug: asking "What can you tell me
# about Honda Civics?" made the model hallucinate a nonexistent
# module_id and call open_module instead of answering "I don't know" —
# traced to tools being attached to every message unconditionally, even
# pure information questions with no relevant action. See this module's
# docstring and looks_like_action_request()'s docstring.

def test_honda_civics_question_is_not_an_action_request():
    assert looks_like_action_request("What can you tell me about Honda Civics?") is False


def test_plain_information_question_is_not_an_action_request():
    assert looks_like_action_request("What are the symptoms of hypothermia?") is False


def test_open_module_phrasing_is_an_action_request():
    assert looks_like_action_request("Open the notes module for me") is True


def test_set_an_alarm_phrasing_is_an_action_request():
    assert looks_like_action_request("Set an alarm called Wake Up for 07:00") is True


def test_remind_me_phrasing_is_an_action_request():
    assert looks_like_action_request("Remind me to take out the trash") is True


def test_add_a_note_phrasing_is_an_action_request():
    assert looks_like_action_request("Add a note that says buy milk") is True


def test_add_to_inventory_phrasing_is_an_action_request():
    assert looks_like_action_request("Add to inventory: 10 M3 bolts") is True


def test_recent_activity_phrasing_is_an_action_request():
    assert looks_like_action_request("What have I been doing recently?") is True


def test_notebook_word_does_not_false_positive_on_note_keyword():
    """Loose "note" would false-positive on unrelated words like "notebook" — must require the fuller phrase."""
    assert looks_like_action_request("What's a good notebook for taking handwritten notes?") is False
