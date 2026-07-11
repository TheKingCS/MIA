"""
tests.test_notes_module
==========================

Unit test for modules.notes.module.format_entry_row — pure formatting
logic, no Qt event loop needed (importing the module only defines
widget classes; nothing here instantiates one).
"""

from __future__ import annotations

from core.journal_manager import JournalEntry
from modules.notes.module import format_entry_row


def test_formats_title_tags_and_date():
    entry = JournalEntry(
        entry_id="abc123",
        title="Greenhouse Notes",
        body="Watered the tomatoes.",
        tags=["greenhouse", "chores"],
        created_at="2026-07-11T09:30:00",
        updated_at="2026-07-11T09:30:00",
    )
    assert format_entry_row(entry) == "Greenhouse Notes  [greenhouse, chores]   (2026-07-11 09:30)"


def test_omits_tag_bracket_when_no_tags():
    entry = JournalEntry(
        entry_id="abc123",
        title="Untitled",
        updated_at="2026-07-11T09:30:00",
    )
    assert format_entry_row(entry) == "Untitled   (2026-07-11 09:30)"


def test_handles_missing_updated_at():
    entry = JournalEntry(entry_id="abc123", title="Draft")
    assert format_entry_row(entry) == "Draft   ()"
