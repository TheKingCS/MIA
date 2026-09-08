"""
gui.add_edit_event_dialog
============================

Small dialog for creating or editing a single calendar event, used by
modules/toolbox/tools/calendar_tool.py. Structured the same way as
gui/add_profile_dialog.py (QDialog + the shared app-level theme +
QDialogButtonBox, validate-then-expose-via-properties on accept) —
same shape, different fields.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
)

from core.calendar_manager import RECURRENCE_TYPES, CalendarEvent

_ISO_DATE_FORMAT = "yyyy-MM-dd"
_TIME_FORMAT = "HH:mm"
# Display label -> stored recurrence value, "None" first (not recurring).
_RECURRENCE_LABELS = [("Never", None)] + [(r.capitalize(), r) for r in RECURRENCE_TYPES]


class AddEditEventDialog(QDialog):
    def __init__(
        self,
        parent=None,
        default_date: Optional[str] = None,
        event: Optional[CalendarEvent] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Event" if event is not None else "New Event")
        self.setFixedSize(360, 440)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title")
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.date_edit)

        self.all_day_checkbox = QCheckBox("All day")
        self.all_day_checkbox.toggled.connect(self._on_all_day_toggle)
        layout.addWidget(self.all_day_checkbox)

        layout.addWidget(QLabel("Time:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat(_TIME_FORMAT)
        layout.addWidget(self.time_edit)

        layout.addWidget(QLabel("Repeats:"))
        self.recurrence_combo = QComboBox()
        for label, _value in _RECURRENCE_LABELS:
            self.recurrence_combo.addItem(label)
        layout.addWidget(self.recurrence_combo)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(90)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(default_date, event)

        self._title: str = ""
        self._date: str = ""
        self._time: Optional[str] = None
        self._notes: str = ""
        self._recurrence: Optional[str] = None

    def _prefill(self, default_date: Optional[str], event: Optional[CalendarEvent]) -> None:
        if event is not None:
            self.title_edit.setText(event.title)
            self.date_edit.setDate(QDate.fromString(event.date, _ISO_DATE_FORMAT))
            self.notes_edit.setPlainText(event.notes)
            if event.time:
                self.all_day_checkbox.setChecked(False)
                self.time_edit.setTime(QTime.fromString(event.time, _TIME_FORMAT))
            else:
                self.all_day_checkbox.setChecked(True)
            recurrence_index = next(
                (i for i, (_label, value) in enumerate(_RECURRENCE_LABELS) if value == event.recurrence), 0
            )
            self.recurrence_combo.setCurrentIndex(recurrence_index)
        else:
            date_str = default_date or QDate.currentDate().toString(_ISO_DATE_FORMAT)
            self.date_edit.setDate(QDate.fromString(date_str, _ISO_DATE_FORMAT))
            self.all_day_checkbox.setChecked(True)

        self._on_all_day_toggle(self.all_day_checkbox.isChecked())

    def _on_all_day_toggle(self, checked: bool) -> None:
        self.time_edit.setEnabled(not checked)

    def _on_accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setPlaceholderText("Title can't be empty!")
            return

        self._title = title
        self._date = self.date_edit.date().toString(_ISO_DATE_FORMAT)
        self._time = None if self.all_day_checkbox.isChecked() else self.time_edit.time().toString(_TIME_FORMAT)
        self._notes = self.notes_edit.toPlainText().strip()
        self._recurrence = _RECURRENCE_LABELS[self.recurrence_combo.currentIndex()][1]
        self.accept()

    @property
    def entered_title(self) -> str:
        return self._title

    @property
    def entered_date(self) -> str:
        return self._date

    @property
    def entered_time(self) -> Optional[str]:
        return self._time

    @property
    def entered_notes(self) -> str:
        return self._notes

    @property
    def entered_recurrence(self) -> Optional[str]:
        return self._recurrence
