"""
gui.widgets.conversation_card
================================

One row in the Assistant's conversation history list — 2026-07-14
aesthetic pass part 5 (docs/ROADMAP.md). Same shape as
`gui/widgets/module_button.py`'s `ModuleButton`: a `QPushButton` with no
text of its own (its title/timestamp are plain `QLabel` children in a
custom layout, avoiding that same file's documented `&`-mnemonic
parsing bug for free) plus a small nested delete `QPushButton` — a
child button inside a parent button responds to its own clicks
independently in Qt (the parent's own `clicked` only fires for a
press+release directly on itself, not one a child widget already
handled), so "click the card to open it" and "click ✕ to delete it"
coexist without extra event-filtering code.

`selected` is a dynamic Qt property (same `hasUnread`-on-the-
notification-bell pattern from part 2), toggled via `set_selected()`
rather than a second object name, so the currently-active conversation
gets a visibly different look via
`QPushButton#ConversationCard[selected="true"]` in each theme's QSS.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.conversation_manager import Conversation


def format_conversation_timestamp(iso_timestamp: str) -> str:
    """
    Pure formatting logic — testable without Qt (see
    tests/test_conversation_card.py). Avoids strftime's platform-
    specific no-leading-zero day codes (%-d/%#d), same reasoning as
    gui/home_dashboard.py's format_clock_date().
    """
    try:
        parsed = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return iso_timestamp
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.strftime('%H:%M')}"


class ConversationCard(QPushButton):
    """A clickable card representing one saved conversation."""

    activated = Signal(str)  # emits conversation_id when the card itself (not delete) is clicked
    delete_requested = Signal(str)  # emits conversation_id when ✕ is clicked

    def __init__(self, conversation: Conversation) -> None:
        super().__init__()
        self.setObjectName("ConversationCard")
        self.setToolTip(conversation.title)
        # Without an explicit minimum height, this card's QLabel children
        # (title/meta) silently fail to paint once nested inside a
        # parent layout (the left-hand conversation list's QVBoxLayout)
        # — found by bisecting against gui/widgets/module_button.py's
        # ModuleButton, which has never shown this bug and turned out to
        # be the one thing different: its own setMinimumHeight(72) call.
        # Every offscreen-QPA render in this session's history also logs
        # "This plugin does not support propagateSizeHints()" — almost
        # certainly the same root cause: a custom QPushButton relying on
        # its children's natural sizeHint (rather than an explicit
        # minimum size) can get laid out with a collapsed height on this
        # platform before its content can paint. Re-verify on real
        # display hardware before assuming an explicit minimum height is
        # unnecessary for any *other* future custom QPushButton card.
        self.setMinimumHeight(60)
        self._conversation_id = conversation.conversation_id
        self.clicked.connect(lambda: self.activated.emit(self._conversation_id))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 8, 10)
        layout.setSpacing(8)

        text_column = QVBoxLayout()
        text_column.setSpacing(2)

        title_label = QLabel(conversation.title)
        title_label.setObjectName("ConversationCardTitle")
        text_column.addWidget(title_label)

        meta_label = QLabel(format_conversation_timestamp(conversation.updated_at))
        meta_label.setObjectName("ConversationCardMeta")
        text_column.addWidget(meta_label)

        layout.addLayout(text_column, stretch=1)

        delete_button = QPushButton("✕")
        delete_button.setObjectName("HeaderButton")
        delete_button.setFixedWidth(28)
        delete_button.setToolTip("Delete this conversation")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._conversation_id))
        layout.addWidget(delete_button)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
