"""
gui.widgets.objective_card
=============================

One big, "bubbly" card representing one Objective within the selected
Mission in modules/missions/module.py — same redesign motivation as
gui/widgets/mission_card.py. Replaces the plain QListWidget row plus
the screen-level "+1 Tally"/"Delete Selected" buttons that used to
operate on whichever objective happened to be selected — each card now
carries its own inline "+1" (tally-type objectives only) and "✕"
delete button, so there's no separate "select an objective first"
step; same nested-button-click-isolation trick
gui/widgets/conversation_card.py's docstring documents (a child
button's own click doesn't also fire the parent QPushButton's
`clicked`).

A real QProgressBar (already globally themed in gui/styles.py, no new
QSS needed) gives the progress bar/target a genuine visual bar instead
of just text, matching the user's "bubbly" ask better than a plain
label.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from core.mission_manager import Objective


class ObjectiveCard(QPushButton):
    """A big card representing one Objective. `index` is this
    objective's position within its Mission's objectives list — the
    only stable identifier core/mission_manager.py's index-based API
    (increment_tally(mission_id, index), delete_objective(mission_id,
    index)) has to offer, same as the module's own previous
    QListWidgetItem.setData(..., index) approach."""

    increment_requested = Signal(int)  # emits this objective's index
    delete_requested = Signal(int)

    def __init__(self, index: int, objective: Objective, progress: float, is_complete: bool) -> None:
        super().__init__()
        self.setObjectName("ObjectiveCard")
        self.setToolTip(objective.description)
        self.setMinimumHeight(88)
        self._index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 12, 12)
        layout.setSpacing(10)

        text_column = QVBoxLayout()
        text_column.setSpacing(4)

        mark = "✓ " if is_complete else ""
        description_label = QLabel(f"{mark}{objective.description}")
        description_label.setObjectName("MissionCardTitle")
        description_label.setWordWrap(True)
        text_column.addWidget(description_label)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, max(1, int(objective.target)))
        progress_bar.setValue(min(int(progress), int(objective.target)))
        progress_bar.setFormat(f"{progress:g} of {objective.target:g}")
        progress_bar.setFixedHeight(18)
        text_column.addWidget(progress_bar)

        layout.addLayout(text_column, stretch=1)

        if objective.metric_type == "tally" and not is_complete:
            increment_button = QPushButton("+1")
            increment_button.setObjectName("HeaderButton")
            increment_button.setFixedWidth(40)
            increment_button.setToolTip("Add 1 to this objective's tally")
            increment_button.clicked.connect(lambda: self.increment_requested.emit(self._index))
            layout.addWidget(increment_button)

        delete_button = QPushButton("✕")
        delete_button.setObjectName("HeaderButton")
        delete_button.setFixedWidth(32)
        delete_button.setToolTip("Delete this objective")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._index))
        layout.addWidget(delete_button)
