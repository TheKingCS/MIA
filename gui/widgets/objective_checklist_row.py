"""
gui.widgets.objective_checklist_row

A single checklist-style row for one Objective, in the redesigned
Mission Log's detail panel (modules/missions/module.py) — 2026-07-18
design handoff (CCH.zip). Leaner than gui/widgets/objective_card.py's
ObjectiveCard (a filled/outlined checkbox glyph + description, no
progress bar) — clicking the checkbox increments a tally-type
objective by one, matching a real checklist's own interaction, rather
than a separate "+1" button. A small ✕ (delete) sits at the row's end,
same as ObjectiveCard's, since there's no other screen-level way to
remove one objective from this mission.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class ObjectiveChecklistRow(QWidget):
    increment_requested = Signal(int)  # emits this objective's index
    delete_requested = Signal(int)

    def __init__(self, index: int, description: str, is_complete: bool, can_increment: bool) -> None:
        super().__init__()
        self._index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._checkbox = QPushButton("✓" if is_complete else "")
        self._checkbox.setObjectName("ObjectiveChecklistBox")
        self._checkbox.setProperty("checked", is_complete)
        self._checkbox.setFixedSize(20, 20)
        self._checkbox.setEnabled(can_increment and not is_complete)
        self._checkbox.setToolTip("Log progress" if can_increment else "Tracked automatically")
        self._checkbox.clicked.connect(lambda: self.increment_requested.emit(self._index))
        layout.addWidget(self._checkbox)

        label = QLabel(description)
        label.setObjectName("ObjectiveChecklistTextDone" if is_complete else "ObjectiveChecklistText")
        label.setWordWrap(True)
        layout.addWidget(label, stretch=1)

        delete_button = QPushButton("✕")
        delete_button.setObjectName("HeaderButton")
        delete_button.setFixedWidth(26)
        delete_button.setToolTip("Delete this objective")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._index))
        layout.addWidget(delete_button)
