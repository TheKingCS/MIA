"""
gui.add_edit_mission_dialog
==============================

Small dialog for creating or editing a single Mission
(modules/missions/module.py) — name, an optional linked Trip (picked
from a QComboBox of all existing trips, "None" for a general goal not
tied to any outing), and status (edit only). The trip link can't be
changed after creation (mirrors `update_mission()`'s own rejection of a
`trip_id` field change, same reasoning as Trip's fixed `expedition_id`)
— editing an existing Mission shows name/status only, no trip picker.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from core.mission_manager import Mission

_STATUSES = ("active", "completed", "abandoned")


class AddEditMissionDialog(QDialog):
    def __init__(self, context, parent=None, mission: Optional[Mission] = None) -> None:
        super().__init__(parent)
        self.context = context
        self._editing = mission is not None
        self.setWindowTitle("Edit Mission" if self._editing else "New Mission")
        self.setFixedSize(360, 320 if self._editing else 380)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name, e.g. 'Master Angler'")
        layout.addWidget(self.name_edit)

        self.trip_combo: Optional[QComboBox] = None
        if not self._editing:
            layout.addWidget(QLabel("Linked Trip (optional):"))
            self.trip_combo = QComboBox()
            self.trip_combo.addItem("(None — general goal)", None)
            for trip in context.trips.all_trips():
                self.trip_combo.addItem(trip.name, trip.trip_id)
            layout.addWidget(self.trip_combo)

        self.status_combo: Optional[QComboBox] = None
        if self._editing:
            layout.addWidget(QLabel("Status:"))
            self.status_combo = QComboBox()
            for status in _STATUSES:
                self.status_combo.addItem(status.capitalize(), status)
            layout.addWidget(self.status_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(mission)

        self._name: str = ""
        self._trip_id = None
        self._status: str = "active"

    def _prefill(self, mission: Optional[Mission]) -> None:
        if mission is not None:
            self.name_edit.setText(mission.name)
            if self.status_combo is not None:
                index = self.status_combo.findData(mission.status)
                self.status_combo.setCurrentIndex(index if index != -1 else 0)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        if self.trip_combo is not None:
            self._trip_id = self.trip_combo.currentData()
        if self.status_combo is not None:
            self._status = self.status_combo.currentData()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_trip_id(self):
        return self._trip_id

    @property
    def entered_status(self) -> str:
        return self._status
