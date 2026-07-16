"""
gui.widgets.mission_card
===========================

One big, "bubbly" card representing one Mission in
modules/missions/module.py — replacing the plain QListWidget rows the
Missions screen shipped with since v0.18, at the user's explicit
request for "bigger and more bubbly button-like choosing... and
interacting." Same shape as gui/widgets/conversation_card.py's
ConversationCard (a QPushButton with QLabel children in a custom
layout, a nested delete button that responds to its own clicks
independently of the card's own `clicked`, a `selected` dynamic
property toggled via set_selected() so the currently-active mission
gets a visibly different look via
QPushButton#MissionCard[selected="true"]) — just bigger (a taller
minimum height, larger title font) and rounder (a bigger border-radius
in the QSS, the actual "bubbly" part) than that card. Also gains an
inline edit (✎) button, since Missions (unlike Conversations) have a
real edit dialog worth reaching one click away rather than a separate
list-level "Edit Selected" button.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.mission_manager import Mission


class MissionCard(QPushButton):
    """A big clickable card representing one Mission."""

    activated = Signal(str)  # emits mission_id when the card body (not ✎/✕) is clicked
    edit_requested = Signal(str)  # emits mission_id when ✎ is clicked
    delete_requested = Signal(str)  # emits mission_id when ✕ is clicked

    def __init__(self, mission: Mission, trip_name: str = "") -> None:
        super().__init__()
        self.setObjectName("MissionCard")
        self.setToolTip(mission.name)
        # Explicit minimum height, same reasoning ConversationCard's own
        # docstring documents in detail (a custom QPushButton relying on
        # children's natural sizeHint can get a collapsed height before
        # painting on this platform) — taller than that card's 60px
        # since this one is deliberately the "bigger" bubble the user
        # asked for.
        self.setMinimumHeight(96)
        self._mission_id = mission.mission_id
        self.clicked.connect(lambda: self.activated.emit(self._mission_id))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 12, 14)
        layout.setSpacing(10)

        text_column = QVBoxLayout()
        text_column.setSpacing(4)

        name_label = QLabel(mission.name)
        name_label.setObjectName("MissionCardTitle")
        name_label.setWordWrap(True)
        text_column.addWidget(name_label)

        meta_parts = [mission.status]
        if trip_name:
            meta_parts.append(trip_name)
        meta_label = QLabel("  •  ".join(meta_parts))
        meta_label.setObjectName("MissionCardMeta")
        text_column.addWidget(meta_label)

        layout.addLayout(text_column, stretch=1)

        edit_button = QPushButton("✎")
        edit_button.setObjectName("HeaderButton")
        edit_button.setFixedWidth(32)
        edit_button.setToolTip("Edit this mission")
        edit_button.clicked.connect(lambda: self.edit_requested.emit(self._mission_id))
        layout.addWidget(edit_button)

        delete_button = QPushButton("✕")
        delete_button.setObjectName("HeaderButton")
        delete_button.setFixedWidth(32)
        delete_button.setToolTip("Delete this mission")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._mission_id))
        layout.addWidget(delete_button)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
