"""
gui.add_edit_trip_dialog
===========================

Small dialog for creating or editing a single Trip (one activity/leg —
hike, paddle, ride, fishing trip, etc. — under an Expedition in
modules/expeditions/module.py) — docs/ROADMAP.md milestone 12.1,
Expedition Mode. Same shape as gui/add_edit_expedition_dialog.py —
name/start_date/end_date/activity_type/notes. `expedition_id` is not
editable here: a Trip's parent Expedition is fixed by whichever one is
selected in the module when "Add Trip"/"Edit Trip" is invoked, not a
field a user picks inside this dialog.

`activity_type` uses a QComboBox over `ACTIVITY_TYPES` plus a blank
"Unspecified" option, same pattern as
gui/add_edit_waypoint_dialog.py's category field.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.trip_manager import ACTIVITY_TYPES, Trip

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditTripDialog(QDialog):
    def __init__(self, parent=None, trip: Optional[Trip] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Trip" if trip is not None else "New Trip")
        self.setFixedSize(360, 520)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Activity Type:"))
        self.activity_type_combo = QComboBox()
        self.activity_type_combo.addItem("Unspecified", "")
        for activity_type in ACTIVITY_TYPES:
            self.activity_type_combo.addItem(activity_type, activity_type)
        layout.addWidget(self.activity_type_combo)

        layout.addWidget(QLabel("Start Date:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.start_date_edit)

        layout.addWidget(QLabel("End Date:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.end_date_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        layout.addWidget(self.notes_edit, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(trip)

        self._name: str = ""
        self._start_date: str = ""
        self._end_date: str = ""
        self._activity_type: str = ""
        self._notes: str = ""

    def _prefill(self, trip: Optional[Trip]) -> None:
        today = QDate.currentDate()
        if trip is not None:
            self.name_edit.setText(trip.name)
            self.start_date_edit.setDate(
                QDate.fromString(trip.start_date, _ISO_DATE_FORMAT) if trip.start_date else today
            )
            self.end_date_edit.setDate(
                QDate.fromString(trip.end_date, _ISO_DATE_FORMAT) if trip.end_date else today
            )
            index = self.activity_type_combo.findData(trip.activity_type)
            self.activity_type_combo.setCurrentIndex(index if index != -1 else 0)
            self.notes_edit.setPlainText(trip.notes)
        else:
            self.start_date_edit.setDate(today)
            self.end_date_edit.setDate(today)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._start_date = self.start_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._end_date = self.end_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._activity_type = self.activity_type_combo.currentData()
        self._notes = self.notes_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_start_date(self) -> str:
        return self._start_date

    @property
    def entered_end_date(self) -> str:
        return self._end_date

    @property
    def entered_activity_type(self) -> str:
        return self._activity_type

    @property
    def entered_notes(self) -> str:
        return self._notes
