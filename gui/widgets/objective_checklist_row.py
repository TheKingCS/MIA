"""
gui.widgets.objective_checklist_row

A single checklist-style row for one Objective, in the redesigned
Mission Log's detail panel (modules/missions/module.py) — 2026-07-18
design handoff (CCH.zip). Leaner than gui/widgets/objective_card.py's
ObjectiveCard (a filled/outlined checkbox glyph + description, no
progress bar) — a small ✕ (delete) sits at the row's end, same as
ObjectiveCard's, since there's no other screen-level way to remove one
objective from this mission.

**2026-07-18 real user report: "needs some way of adding to the
progression/tracking."** The first version of this row made the
checkbox itself double as the increment control (click it repeatedly
to tally up) — for a single-step objective (target 1) that reads fine
as a normal checkbox, but for a multi-step one ("Catch 3 fish") it gave
no visible hint that clicking an apparently-plain checkbox multiple
times was even a supported action. Now: the checkbox is purely a
completion indicator for multi-step objectives, and a separate, clearly
labeled "+1" button is the actual progress control — unambiguous at a
glance, regardless of how many steps the objective has.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class ObjectiveChecklistRow(QWidget):
    increment_requested = Signal(int)  # emits this objective's index
    delete_requested = Signal(int)

    def __init__(self, index: int, description: str, is_complete: bool, can_increment: bool, is_multi_step: bool = False) -> None:
        super().__init__()
        self._index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._checkbox = QPushButton("✓" if is_complete else "")
        self._checkbox.setObjectName("ObjectiveChecklistBox")
        self._checkbox.setProperty("checked", is_complete)
        self._checkbox.setFixedSize(20, 20)
        # A single-step objective (target 1) can still be completed by
        # clicking the checkbox itself, same as a real checkbox. A
        # multi-step one relies on the explicit "+1" button below
        # instead — clicking a plain-looking checkbox repeatedly isn't
        # a discoverable way to log partial progress.
        self._checkbox.setEnabled(can_increment and not is_complete and not is_multi_step)
        self._checkbox.setToolTip("Mark done" if can_increment and not is_multi_step else "Tracked automatically")
        self._checkbox.clicked.connect(lambda: self.increment_requested.emit(self._index))
        layout.addWidget(self._checkbox)

        label = QLabel(description)
        label.setObjectName("ObjectiveChecklistTextDone" if is_complete else "ObjectiveChecklistText")
        label.setWordWrap(True)
        layout.addWidget(label, stretch=1)

        if can_increment and is_multi_step and not is_complete:
            progress_button = QPushButton("+1")
            progress_button.setObjectName("ObjectiveProgressButton")
            progress_button.setToolTip("Log 1 toward this objective")
            progress_button.clicked.connect(lambda: self.increment_requested.emit(self._index))
            layout.addWidget(progress_button)

        delete_button = QPushButton("✕")
        delete_button.setObjectName("HeaderButton")
        delete_button.setFixedWidth(26)
        delete_button.setToolTip("Delete this objective")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._index))
        layout.addWidget(delete_button)
