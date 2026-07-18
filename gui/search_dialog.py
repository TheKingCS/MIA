"""
gui.search_dialog
===================

The search-anywhere dialog, opened via Ctrl+K or the header search
button. Live search-as-you-type against core.search_manager.SearchManager.

This dialog only interprets SearchResult.action_type to decide what to
do when a result is clicked — it never reaches into a module's or
provider's internals, keeping the same core/gui separation as the rest
of the project.

Result rows are built as a QFrame containing separate QLabels for
title/description (the same pattern gui/notification_center.py uses),
not a QPushButton with embedded "\n" text. QPushButton's sizeHint isn't
reliable for multi-line text — with only a couple of rows there's
enough slack to hide the mismatch, but once several rows stack up in
the scroll area, the shortfall shows up as squished/cut-off text. A
QFrame with real QLabel children sizes correctly regardless of result
count.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext


class _ResultRow(QFrame):
    """A single clickable search result row."""

    clicked = Signal()

    def __init__(self, result) -> None:
        super().__init__()
        self.result = result
        self.setStyleSheet(
            "QFrame { background-color: #161b22; border: 1px solid #232b34; border-radius: 8px; }"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        title_label = QLabel(f"{result.title}   \u2022 {result.source}")
        title_label.setStyleSheet("font-weight: 600;")
        title_label.setWordWrap(True)

        desc_label = QLabel(result.description)
        desc_label.setObjectName("SubtitleLabel")
        desc_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class SearchDialog(QDialog):
    result_activated = Signal(object)  # emits a core.search_manager.SearchResult

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Search MIA")
        self.resize(440, 480)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Search")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Search modules, profiles, and more...")
        self.query_edit.textChanged.connect(self._on_query_changed)
        layout.addWidget(self.query_edit)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._results_container = QWidget()
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._results_layout.setSpacing(8)

        scroll.setWidget(self._results_container)
        layout.addWidget(scroll)

        self.query_edit.setFocus()

    def _on_query_changed(self, text: str) -> None:
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        text = text.strip()
        if not text:
            return

        results = self.context.search.search(text)
        if not results:
            empty_label = QLabel("No matches.")
            empty_label.setObjectName("SubtitleLabel")
            self._results_layout.addWidget(empty_label)
            return

        for result in results:
            row = _ResultRow(result)
            row.clicked.connect(lambda r=result: self._on_result_clicked(r))
            self._results_layout.addWidget(row)

    def _on_result_clicked(self, result) -> None:
        self.result_activated.emit(result)
        self.accept()
