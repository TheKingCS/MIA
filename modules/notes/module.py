"""
modules.notes.module
======================

Notes: the Notes/Journal Engine's UI (docs/ROADMAP.md milestone 3.4),
replacing the earlier placeholder. Dated, searchable, taggable entries
— a filterable list (title/tags/last-updated), Add/Edit/Delete via
gui/add_edit_journal_entry_dialog.py. All persistence/query logic
lives in core/journal_manager.py (self.context.journal); this module
is the Qt-facing wrapper around it, same split as every other
data-backed tool in this app (Calendar, Alarm).

Registers a Global Search provider in on_load() — the first module to
actually use that documented-but-previously-unused extension point
(see docs/ADDING_MODULES.md's "Making your module searchable" section,
and core/search_manager.py's own module docstring, which calls out
Notes by name as an example of "real content-bearing modules" that
should register one). Uses action_type="open_module" rather than a
deep-link into a specific entry — see ADDING_MODULES.md's note that a
more specific action would need a new action_type and a branch in
gui/main_window.py; landing on the Notes list (where the matched entry
is right there) is enough for this milestone without that extra
plumbing. Because on_load() only runs the first time this module is
opened (lazy, per modules.module_base.ModuleBase), journal entries
aren't searchable until the user has visited Notes at least once in
the session — an existing framework tradeoff, not new to this module.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.journal_manager import JournalEntry
from core.search_manager import SearchResult
from gui.add_edit_journal_entry_dialog import AddEditJournalEntryDialog
from gui.private_journal_panel import PrivateJournalPanel
from modules.module_base import ModuleBase


def format_entry_row(entry: JournalEntry) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_notes_module.py)."""
    tags_part = f"  [{', '.join(entry.tags)}]" if entry.tags else ""
    date_part = entry.updated_at.replace("T", " ")[:16] if entry.updated_at else ""
    return f"{entry.title}{tags_part}   ({date_part})"


class NotesModule(ModuleBase):
    module_id = "notes"
    display_name = "Notes"
    description = "Dated, searchable, taggable journal entries."
    icon = "\U0001F4DD"  # memo

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list: Optional[QListWidget] = None
        self._filter_edit: Optional[QLineEdit] = None

    def on_load(self) -> None:
        super().on_load()
        self.context.search.register_provider("notes", self._search)

    def refresh(self) -> None:
        """Re-read every list (ModuleBase.refresh: records changed elsewhere, e.g. by voice)."""
        self._refresh_list()

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        # Two tabs (2026-09-27): the plain Notes list, and the encrypted
        # Private Journal MIA fills from journaling conversations.
        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)
        notes_tab = QWidget()
        tabs.addTab(notes_tab, "Notes")
        tabs.addTab(PrivateJournalPanel(self.context), "🔒 Private Journal")
        layout = QVBoxLayout(notes_tab)  # the Notes list below goes in its tab
        layout.setContentsMargins(0, 8, 0, 0)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter entries by title, tag, or text…")
        self._filter_edit.textChanged.connect(lambda _text: self._refresh_list())
        layout.addWidget(self._filter_edit)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Entry")
        add_button.clicked.connect(self._on_add)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        query = self._filter_edit.text().strip()
        entries = self.context.journal.search(query) if query else self.context.journal.all_entries()

        self._list.clear()
        for entry in entries:
            item = QListWidgetItem(format_entry_row(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            self._list.addItem(item)

    def _selected_entry_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        dialog = AddEditJournalEntryDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.journal.add_entry(
            title=dialog.entered_title,
            body=dialog.entered_body,
            tags=dialog.entered_tags,
        )
        self._refresh_list()

    def _on_edit(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            QMessageBox.information(None, "No Entry Selected", "Select an entry to edit.")
            return

        entry = self.context.journal.get_entry(entry_id)
        dialog = AddEditJournalEntryDialog(entry=entry)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.journal.update_entry(
            entry_id,
            title=dialog.entered_title,
            body=dialog.entered_body,
            tags=dialog.entered_tags,
        )
        self._refresh_list()

    def _on_delete(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            QMessageBox.information(None, "No Entry Selected", "Select an entry to delete.")
            return

        entry = self.context.journal.get_entry(entry_id)
        confirm = QMessageBox.question(
            None,
            "Delete Entry",
            f"Delete '{entry.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.journal.delete_entry(entry_id)
        self._refresh_list()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search(self, query: str) -> list[SearchResult]:
        results = []
        for entry in self.context.journal.search(query):
            results.append(SearchResult(
                title=entry.title,
                description=", ".join(entry.tags) if entry.tags else "Journal entry",
                source=self.display_name,
                action_type="open_module",
                action_target=self.module_id,
            ))
        return results
