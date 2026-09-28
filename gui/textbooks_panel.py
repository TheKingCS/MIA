"""
gui.textbooks_panel
======================

The Textbooks page in Classroom (textbook tutor, 2026-09-28): add a book
(PDF or text), see what MIA found in it (pages, chapters), turn it into
a Classroom course, remove it. Studying happens in conversation with
MIA ("let's study <book>", "quiz me on chapter 3"); the page says so.
All data goes through self.context.textbooks (core/textbook_manager.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.textbook_manager import Textbook


def format_textbook_row(book: Textbook) -> str:
    """Pure formatting logic."""
    chapters = len(book.chapters)
    course = "  · course made" if book.course_id else ""
    return f"{book.title}  —  {book.page_count} pages, {chapters} chapter{'s' if chapters != 1 else ''}{course}"


def format_chapter_list(book: Textbook) -> str:
    """Pure formatting logic."""
    return "\n".join(f"• {c.title} (page {c.page})" for c in book.chapters)


class TextbooksPanel(QWidget):
    def __init__(self, context, on_back: Optional[Callable[[], None]] = None, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        if on_back is not None:
            back = QPushButton("← Back")
            back.clicked.connect(on_back)
            layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignLeft)

        header = QLabel("\U0001F4DA  Textbooks")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)
        hint = QLabel(
            "Add a textbook (PDF or text) and MIA can teach from it, citing pages. Then tell her: "
            "\"let's study\" and the book's name, \"quiz me on chapter 3\", or \"what does my book say about "
            "GFCI outlets?\". Scanned PDFs (pictures of pages) can't be read yet."
        )
        hint.setObjectName("SubtitleLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(lambda _c, _p: self._show_selected())
        layout.addWidget(self._list, stretch=1)
        self._details = QLabel("")
        self._details.setWordWrap(True)
        self._details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._details)

        buttons = QHBoxLayout()
        for text, handler in (("Add Textbook…", self._on_add), ("Make a Course", self._on_make_course),
                              ("Remove Selected", self._on_remove)):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh()

    @property
    def _library(self):
        return self.context.textbooks

    def refresh(self) -> None:
        selected = self._selected_id()
        self._list.clear()
        for book in self._library.all_books() if self._library else []:
            item = QListWidgetItem(format_textbook_row(book))
            item.setData(Qt.ItemDataRole.UserRole, book.book_id)
            self._list.addItem(item)
            if book.book_id == selected:
                self._list.setCurrentItem(item)
        if self._list.count() == 0:
            self._details.setText("No textbooks yet.")

    def _selected_id(self) -> Optional[str]:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _show_selected(self) -> None:
        book = self._library.get_book(self._selected_id()) if self._selected_id() else None
        self._details.setText(f"Chapters MIA found:\n{format_chapter_list(book)}" if book else "")

    def _on_add(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Add a Textbook", str(Path.home()), "Books (*.pdf *.txt *.md)")
        if not path:
            return
        try:
            book = self._library.add_book(Path(path))
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Add a Textbook", str(exc))
            return
        self.refresh()
        QMessageBox.information(
            self, "Add a Textbook",
            f"Added \"{book.title}\": {book.page_count} pages, {len(book.chapters)} chapter(s). "
            "Say \"let's study\" and its name to start.",
        )

    def _on_make_course(self) -> None:
        book_id = self._selected_id()
        if book_id is None:
            QMessageBox.information(self, "Make a Course", "Select a textbook first.")
            return
        if self.context.classroom is None or self._library.make_course(book_id) is None:
            QMessageBox.warning(self, "Make a Course", "Classroom isn't available.")
            return
        self.refresh()
        QMessageBox.information(self, "Make a Course", "Done: it's under the Textbooks subject in Classroom, one lesson per chapter.")

    def _on_remove(self) -> None:
        book_id = self._selected_id()
        if book_id is None:
            return
        book = self._library.get_book(book_id)
        confirm = QMessageBox.question(self, "Remove Textbook", f"Remove \"{book.title}\" from MIA? The original file isn't touched.")
        if confirm == QMessageBox.StandardButton.Yes:
            self._library.remove_book(book_id)
            self.refresh()
