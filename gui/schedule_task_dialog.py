"""
gui.schedule_task_dialog
===========================

Small dialog for picking a date to schedule a maintenance task onto
MIA's real Calendar (core.calendar_manager.CalendarManager), used by
modules/maintenance/module.py. Same QDateEdit pattern as
gui/add_edit_event_dialog.py.

The real "calendar-aware" piece: as the date changes, a live warning
label shows whatever's already on core.calendar_manager.CalendarManager
for that day via events_for_date() — a real query against the actual
calendar data, not a static hint. This dialog never blocks scheduling
on a conflict, only informs — same "inform, don't prevent" stance
every other action in this app takes; the user decides whether a busy
day is still fine.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from core.calendar_manager import CalendarManager

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class ScheduleTaskDialog(QDialog):
    def __init__(self, parent=None, calendar: Optional[CalendarManager] = None, default_date: Optional[str] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Schedule Maintenance")
        self.setFixedSize(340, 220)
        self._calendar = calendar

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        date_str = default_date or QDate.currentDate().toString(_ISO_DATE_FORMAT)
        self.date_edit.setDate(QDate.fromString(date_str, _ISO_DATE_FORMAT))
        self.date_edit.dateChanged.connect(self._refresh_conflict_warning)
        layout.addWidget(self.date_edit)

        self.conflict_label = QLabel()
        self.conflict_label.setWordWrap(True)
        layout.addWidget(self.conflict_label, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._date: str = ""
        self._refresh_conflict_warning(self.date_edit.date())

    def _refresh_conflict_warning(self, qdate: QDate) -> None:
        if self._calendar is None:
            self.conflict_label.setText("")
            return
        date_str = qdate.toString(_ISO_DATE_FORMAT)
        events = self._calendar.events_for_date(date_str)
        if not events:
            self.conflict_label.setText("Nothing else on the calendar that day.")
        else:
            titles = ", ".join(e.title for e in events)
            noun = "thing" if len(events) == 1 else "things"
            self.conflict_label.setText(f"Already {len(events)} {noun} scheduled that day: {titles}")

    def _on_accept(self) -> None:
        self._date = self.date_edit.date().toString(_ISO_DATE_FORMAT)
        self.accept()

    @property
    def entered_date(self) -> str:
        return self._date
