"""
gui.add_edit_objective_dialog
================================

Small dialog for adding a single Objective to a Mission
(modules/missions/module.py) — description, metric type (QComboBox
over core.mission_manager.METRIC_TYPES, same fixed-vocabulary pattern
as gui/add_edit_trip_dialog.py's activity_type field), and target.
Add-only — this app has no "edit an objective" flow; delete and
re-add covers the rare correction case, same reasoning as gear items
in gui/trip_detail_dialog.py.

Group quests (2026-09-14) — when the mission being added to is a real
party quest (see gui.add_edit_mission_dialog.AddEditMissionDialog's
Party picker), gained an optional "Assign to" combo so an objective
can be personal to one participant
(core.mission_manager.Objective.assigned_profile_id) instead of always
shared. `participant_names_by_id` defaults to empty so a normal solo
mission's Add Objective flow is unchanged — no combo shown, assignee
always None.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from core.mission_manager import METRIC_TYPES

_METRIC_TYPE_LABELS = {
    "tally": "Tally (manually counted, e.g. fish caught)",
    "trip_duration_hours": "Time spent on linked trip (hours)",
}

_SHARED_ASSIGNEE_LABEL = "(Shared — anyone)"


class AddEditObjectiveDialog(QDialog):
    def __init__(self, parent=None, participant_names_by_id: Optional[dict[str, str]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Objective")
        self.setFixedSize(360, 260 if not participant_names_by_id else 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g. 'Catch 3 fish'")
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Metric:"))
        self.metric_combo = QComboBox()
        for metric_type in METRIC_TYPES:
            self.metric_combo.addItem(_METRIC_TYPE_LABELS.get(metric_type, metric_type), metric_type)
        layout.addWidget(self.metric_combo)

        layout.addWidget(QLabel("Target:"))
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(0.1, 100_000.0)
        self.target_spin.setValue(1.0)
        layout.addWidget(self.target_spin)

        self.assignee_combo: Optional[QComboBox] = None
        if participant_names_by_id:
            layout.addWidget(QLabel("Assign to:"))
            self.assignee_combo = QComboBox()
            self.assignee_combo.addItem(_SHARED_ASSIGNEE_LABEL, None)
            for profile_id, name in participant_names_by_id.items():
                self.assignee_combo.addItem(name, profile_id)
            layout.addWidget(self.assignee_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._description: str = ""
        self._metric_type: str = "tally"
        self._target: float = 1.0
        self._assignee_profile_id: Optional[str] = None

    def _on_accept(self) -> None:
        description = self.description_edit.text().strip()
        if not description:
            self.description_edit.setPlaceholderText("Description can't be empty!")
            return

        self._description = description
        self._metric_type = self.metric_combo.currentData()
        self._target = self.target_spin.value()
        if self.assignee_combo is not None:
            self._assignee_profile_id = self.assignee_combo.currentData()
        self.accept()

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_metric_type(self) -> str:
        return self._metric_type

    @property
    def entered_target(self) -> float:
        return self._target

    @property
    def entered_assignee_profile_id(self) -> Optional[str]:
        return self._assignee_profile_id
