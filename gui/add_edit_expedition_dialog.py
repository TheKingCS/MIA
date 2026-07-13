"""
gui.add_edit_expedition_dialog
=================================

Small dialog for creating or editing a single Expedition (the top-level
outing container in modules/expeditions/module.py) — docs/ROADMAP.md
milestone 12.1, Expedition Mode. Same shape as
gui/add_edit_event_dialog.py (QDialog + the shared app-level theme +
QDialogButtonBox, validate-then-expose-via-properties on accept,
QDateEdit with a calendar popup for dates) — name/start_date/end_date/
location/notes instead of title/date/time/notes.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.expedition_manager import Expedition

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditExpeditionDialog(QDialog):
    def __init__(self, parent=None, expedition: Optional[Expedition] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Expedition" if expedition is not None else "New Expedition")
        self.setFixedSize(360, 520)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

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

        layout.addWidget(QLabel("Location:"))
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Region/area (optional)")
        layout.addWidget(self.location_edit)

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

        self._prefill(expedition)

        self._name: str = ""
        self._start_date: str = ""
        self._end_date: str = ""
        self._location: str = ""
        self._notes: str = ""

    def _prefill(self, expedition: Optional[Expedition]) -> None:
        today = QDate.currentDate()
        if expedition is not None:
            self.name_edit.setText(expedition.name)
            if expedition.start_date:
                self.start_date_edit.setDate(QDate.fromString(expedition.start_date, _ISO_DATE_FORMAT))
            else:
                self.start_date_edit.setDate(today)
            if expedition.end_date:
                self.end_date_edit.setDate(QDate.fromString(expedition.end_date, _ISO_DATE_FORMAT))
            else:
                self.end_date_edit.setDate(today)
            self.location_edit.setText(expedition.location)
            self.notes_edit.setPlainText(expedition.notes)
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
        self._location = self.location_edit.text().strip()
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
    def entered_location(self) -> str:
        return self._location

    @property
    def entered_notes(self) -> str:
        return self._notes
