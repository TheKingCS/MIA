"""
gui.conversation_history_dialog
==================================

A small popup listing every saved conversation, letting the user pick
one to make active again — the "way to access previous conversations"
`gui/character_panel.py`'s sidebar needs now that it starts fresh on
every app launch instead of showing whatever was last active (real
user ask, 2026-07-18: "I want the sidebar assistant to not display any
previous conversation but have a way to access previous conversations").

Reuses `gui/widgets/conversation_card.py`'s `ConversationCard` as-is —
same rows `modules/assistant/module.py`'s own left-hand history list
already uses, just presented as a standalone popup instead of a
permanent sidebar column (the character panel is too narrow for a
second, always-visible list alongside its own chat).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from core.app_context import AppContext
from gui.widgets.conversation_card import ConversationCard


class ConversationHistoryDialog(QDialog):
    """`.selected_conversation_id` is set only if the user actually picked a row (None if dismissed)."""

    def __init__(self, context: AppContext, current_conversation_id: Optional[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Previous Conversations")
        self.resize(360, 480)
        self.selected_conversation_id: Optional[str] = None

        layout = QVBoxLayout(self)

        conversations = context.conversations.all_conversations()
        if not conversations:
            empty_label = QLabel("No previous conversations yet.")
            empty_label.setObjectName("SubtitleLabel")
            layout.addWidget(empty_label)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(8)

        for conversation in conversations:
            card = ConversationCard(conversation)
            card.set_selected(conversation.conversation_id == current_conversation_id)
            card.activated.connect(self._on_selected)
            container_layout.addWidget(card)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_selected(self, conversation_id: str) -> None:
        self.selected_conversation_id = conversation_id
        self.accept()
