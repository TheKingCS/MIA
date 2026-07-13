"""
gui.add_edit_journal_entry_dialog
====================================

Small dialog for creating or editing a single journal entry, used by
modules/notes/module.py. Same shape as gui/add_edit_event_dialog.py
(QDialog + the shared app-level theme + QDialogButtonBox, validate-then-expose-
via-properties on accept) — title/tags/body instead of
title/date/time/notes.

Tags are entered as one comma-separated line rather than a dedicated
tag-chip widget — this project has no rich text/tag-input component
yet, and a plain QLineEdit is enough for the "taggable" part of the
Notes/Journal Engine described in docs/ROADMAP.md without pulling in
new UI machinery for it.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.journal_manager import JournalEntry


def _parse_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


class AddEditJournalEntryDialog(QDialog):
    def __init__(self, parent=None, entry: Optional[JournalEntry] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Entry" if entry is not None else "New Entry")
        self.setFixedSize(420, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title")
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g. project-x, idea, todo")
        layout.addWidget(self.tags_edit)

        layout.addWidget(QLabel("Entry:"))
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("Write here...")
        layout.addWidget(self.body_edit, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(entry)

        self._title: str = ""
        self._body: str = ""
        self._tags: list[str] = []

    def _prefill(self, entry: Optional[JournalEntry]) -> None:
        if entry is not None:
            self.title_edit.setText(entry.title)
            self.tags_edit.setText(", ".join(entry.tags))
            self.body_edit.setPlainText(entry.body)

    def _on_accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setPlaceholderText("Title can't be empty!")
            return

        self._title = title
        self._body = self.body_edit.toPlainText()
        self._tags = _parse_tags(self.tags_edit.text())
        self.accept()

    @property
    def entered_title(self) -> str:
        return self._title

    @property
    def entered_body(self) -> str:
        return self._body

    @property
    def entered_tags(self) -> list[str]:
        return self._tags
