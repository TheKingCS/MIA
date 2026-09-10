"""
gui.user_memory_dialog
=========================

"What MIA remembers about you" — 2026-07-14 aesthetic pass part 5
(docs/ROADMAP.md), at the user's explicit request: "an ability to...
see the AI's stored memories about the user and keep or delete them."
Opened from `modules/assistant/module.py`'s "🧠 Memories" button.

Read-only list + per-row delete + "Clear All" — no add/edit UI, since
memories are meant to be learned by the Assistant through conversation
(`core.assistant_chat.parse_extracted_memories()`), not hand-authored;
same "no add/edit of its own" stance `modules/memories/module.py`
(Expedition recaps) already takes for a different reason (there,
because it's computed; here, because manually maintaining a memory
list defeats the point of the Assistant building it up on its own).

**2026-09-10 "Memory Palace"**: a category filter combo + a per-row
category tag — the real "categorized, not just a flat list" payoff, in
the one place a user actually browses these. Filtering happens
client-side over the small, already-loaded `all_memories()` list, same
as every other small filterable list in this app (e.g. Budget's own
filter edits) — no manager-level filtering method needed for a list
this size.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.user_memory_manager import MEMORY_CATEGORIES


class UserMemoryDialog(QDialog):
    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("What MIA Remembers About You")
        self.resize(480, 520)

        layout = QVBoxLayout(self)

        subtitle = QLabel(
            "MIA picks these up naturally as you chat. Delete anything you'd rather it forget."
        )
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        category_row = QHBoxLayout()
        category_row.addWidget(QLabel("Category:"))
        self._category_combo = QComboBox()
        self._category_combo.addItem("All Categories", None)
        for category in MEMORY_CATEGORIES:
            self._category_combo.addItem(category, category)
        self._category_combo.currentIndexChanged.connect(lambda _idx: self._refresh())
        category_row.addWidget(self._category_combo, stretch=1)
        layout.addLayout(category_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(8)
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, stretch=1)

        button_row = QHBoxLayout()
        clear_all_button = QPushButton("Clear All")
        clear_all_button.clicked.connect(self._on_clear_all)
        button_row.addWidget(clear_all_button)
        button_row.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        self._refresh()

    def _refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # See gui/character_panel.py's _refresh_suggestions() for
                # why hide()+setParent(None) is needed before
                # deleteLater() — deleteLater() alone doesn't remove the
                # widget from the screen immediately, which caused a
                # real ghosting bug there.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        all_memories = self.context.user_memories.all_memories() if self.context.user_memories is not None else []
        selected_category = self._category_combo.currentData()
        memories = (
            all_memories if selected_category is None
            else [m for m in all_memories if m.category == selected_category]
        )
        if not memories:
            message = (
                "Nothing stored yet — chat with the Assistant and it'll start learning."
                if not all_memories else f"Nothing in {selected_category} yet."
            )
            empty_label = QLabel(message)
            empty_label.setObjectName("SubtitleLabel")
            empty_label.setWordWrap(True)
            self._list_layout.addWidget(empty_label)
            return

        for memory in memories:
            self._list_layout.addWidget(self._build_row(memory))

    def _build_row(self, memory) -> QWidget:
        card = QFrame()
        card.setObjectName("DashboardCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)

        text_label = QLabel(f"[{memory.category}]  {memory.text}")
        text_label.setObjectName("DashboardSectionBody")
        text_label.setWordWrap(True)
        row.addWidget(text_label, stretch=1)

        delete_button = QPushButton("✕")
        delete_button.setObjectName("HeaderButton")
        delete_button.setToolTip("Forget this")
        delete_button.clicked.connect(lambda _checked=False, m=memory: self._on_delete(m))
        row.addWidget(delete_button)

        return card

    def _on_delete(self, memory) -> None:
        self.context.user_memories.delete_memory(memory.memory_id)
        self._refresh()

    def _on_clear_all(self) -> None:
        if not self.context.user_memories.all_memories():
            return
        reply = QMessageBox.question(
            self,
            "Clear All Memories",
            "Delete everything MIA remembers about you? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.context.user_memories.clear_all()
            self._refresh()
