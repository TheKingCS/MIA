"""
gui.widgets.mission_list_row

A single compact row in the redesigned Mission Log's right-hand list
(modules/missions/module.py) — 2026-07-18 design handoff (CCH.zip).
Deliberately much leaner than gui/widgets/mission_card.py's MissionCard
(icon + title only, no inline edit/delete/progress bar) — the design's
list is a dense navigation list, not a set of big interactive cards;
editing/deleting a mission still happens from the detail panel this row
selects into. Same "QPushButton with QLabel children, no text of its
own" shape as ConversationCard/ModuleButton, for the same reason: a QSS
`:hover` on a descendant QLabel makes its text vanish on this platform.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton


class MissionListRow(QPushButton):
    activated = Signal(str)  # emits mission_id when clicked

    def __init__(self, mission_id: str, icon: str, title: str, completed: bool = False) -> None:
        super().__init__()
        self.setObjectName("MissionListRow")
        self.setToolTip(f"View '{title}'")
        self.setMinimumHeight(36)
        # 2026-07-18 real user report ("needs to allow you to select
        # the mission to view it") — clicking a row already worked
        # mechanically, but nothing about a plain text row visually
        # signaled it was clickable at all. A pointing-hand cursor plus
        # the trailing "›" chevron below (the same "tap to go deeper"
        # convention the design's own Assistant Profile rows use) makes
        # the affordance obvious instead of just mechanically present.
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mission_id = mission_id
        self.clicked.connect(lambda: self.activated.emit(self._mission_id))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        icon_label = QLabel("✓" if completed else icon)
        icon_label.setObjectName("MissionListRowCompletedIcon" if completed else "MissionListRowIcon")
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setObjectName("MissionListRowCompletedTitle" if completed else "MissionListRowTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label, stretch=1)

        if not completed:
            chevron = QLabel("›")
            chevron.setObjectName("MissionListRowChevron")
            layout.addWidget(chevron)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
