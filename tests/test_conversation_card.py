"""
tests.test_conversation_card
===============================

Unit test for gui.widgets.conversation_card's pure formatting helper —
no Qt event loop needed. The card widget itself (click-to-select,
delete button, selected-state property toggling) needs a real Qt event
loop to exercise meaningfully, so that was verified with a manual
headless smoke test instead (offscreen QPA platform).
"""

from __future__ import annotations

from gui.widgets.conversation_card import format_conversation_timestamp


def test_format_conversation_timestamp_no_leading_zero_on_day():
    assert format_conversation_timestamp("2026-07-04T09:05:00") == "Jul 4, 09:05"


def test_format_conversation_timestamp_invalid_input_returned_as_is():
    assert format_conversation_timestamp("not-a-timestamp") == "not-a-timestamp"
