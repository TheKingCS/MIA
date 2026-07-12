"""
tests.test_assistant_module
=============================

Unit test for modules.assistant.module.format_chat_line — pure
formatting logic, no Qt event loop needed. Same shape as
tests/test_notes_module.py's format_entry_row test: the widget-building
and worker-thread wiring in AssistantModule needs a real Qt event loop
to exercise meaningfully, so that was verified with a manual headless
smoke test instead (offscreen QPA platform) rather than unit-tested
here.
"""

from __future__ import annotations

from modules.assistant.module import format_chat_line


def test_formats_speaker_and_text():
    assert format_chat_line("You", "hello") == "You: hello"


def test_formats_assistant_reply():
    assert format_chat_line("Assistant", "hi there") == "Assistant: hi there"
