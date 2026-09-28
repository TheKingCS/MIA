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

from PySide6.QtCore import Qt, QTimer
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


_SECONDS_PER_SCANNED_PAGE_ON_PI = 4  # rough, for the "about N minutes" estimate


def format_textbook_row(book: Textbook, progress: Optional[tuple[int, int]] = None) -> str:
    """Pure formatting logic. `progress`: (pages read, total) for a scan
    being read."""
    if book.reading:
        if progress and progress[1]:
            return f"{book.title}  —  reading the scan… page {progress[0]} of {progress[1]}"
        return f"{book.title}  —  a scan, waiting to be read"
    if book.reading_error:
        return f"{book.title}  —  couldn't be read: {book.reading_error}"
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

        self._reading_timer = QTimer(self)
        self._reading_timer.timeout.connect(self._on_reading_tick)
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
        books = self._library.all_books() if self._library else []
        for book in books:
            item = QListWidgetItem(format_textbook_row(book, self._library.reading_progress(book.book_id) if book.reading else None))
            item.setData(Qt.ItemDataRole.UserRole, book.book_id)
            self._list.addItem(item)
            if book.book_id == selected:
                self._list.setCurrentItem(item)
        if self._list.count() == 0:
            self._details.setText("No textbooks yet.")
        # While a scanned book is being read, show its progress and index
        # it as soon as it's done (the app's own check also does, every 30 s).
        if any(b.reading for b in books):
            if not self._reading_timer.isActive():
                self._reading_timer.start(3000)
        else:
            self._reading_timer.stop()

    def _on_reading_tick(self) -> None:
        if not self.isVisible():
            return
        self._library.finish_reading()
        self.refresh()

    def _selected_id(self) -> Optional[str]:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _show_selected(self) -> None:
        book = self._library.get_book(self._selected_id()) if self._selected_id() else None
        if book is not None and book.reading:
            self._details.setText("MIA is reading this scanned book's pages (OCR). Chapters appear when it's done.")
        else:
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
        if book.reading:
            minutes = max(1, round(book.page_count * _SECONDS_PER_SCANNED_PAGE_ON_PI / 60))
            QMessageBox.information(
                self, "Add a Textbook",
                f"\"{book.title}\" is a scan, so MIA is reading its {book.page_count} pages in the background "
                f"(roughly {minutes} minute{'s' if minutes != 1 else ''} on the Pi). Keep using MIA meanwhile; "
                "it's ready to study when this list says so.",
            )
            return
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
        if self._library.get_book(book_id).reading:
            QMessageBox.information(self, "Make a Course", "MIA is still reading that book; try again when it's done.")
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
