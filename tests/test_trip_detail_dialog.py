"""
tests.test_trip_detail_dialog
================================

Unit tests for gui.trip_detail_dialog's pure functions, same style as
tests/test_navigation_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.journal_manager import JournalEntry
from gui.trip_detail_dialog import format_journal_entry_row


def test_format_journal_entry_row_with_conditions():
    entry = JournalEntry(
        entry_id="e1",
        title="Reached Camp",
        conditions="Clear, ~15C, light wind",
        updated_at="2026-08-14T18:30:00",
    )
    assert (
        format_journal_entry_row(entry)
        == "Reached Camp  [Clear, ~15C, light wind]  (2026-08-14T18:30:00)"
    )


def test_format_journal_entry_row_without_conditions():
    entry = JournalEntry(entry_id="e1", title="Untitled Log", updated_at="2026-08-14T18:30:00")
    assert format_journal_entry_row(entry) == "Untitled Log  (2026-08-14T18:30:00)"
