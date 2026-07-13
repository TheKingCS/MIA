"""
gui.add_edit_alarm_dialog
============================

Small dialog for creating or editing a single alarm, used by
modules/toolbox/tools/alarm_tool.py. Same shape as
gui/add_edit_event_dialog.py (QDialog + the shared app-level theme +
QDialogButtonBox, expose entered values via properties on accept).

No validation gate on accept, unlike the event dialog's non-empty-
title check — a QTimeEdit is always a valid time, and an alarm's label
is optional (core.alarm_manager.AlarmManager falls back to a plain
"Alarm" title when raising the notification), so there's nothing here
that can be entered wrong.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTimeEdit,
    QVBoxLayout,
)

from core.alarm_manager import Alarm

_TIME_FORMAT = "HH:mm"
_DAY_LABELS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")


class AddEditAlarmDialog(QDialog):
    def __init__(self, parent=None, alarm: Optional[Alarm] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Alarm" if alarm is not None else "New Alarm")
        self.setFixedSize(340, 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Label:"))
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Label (optional)")
        layout.addWidget(self.label_edit)

        layout.addWidget(QLabel("Time:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat(_TIME_FORMAT)
        layout.addWidget(self.time_edit)

        layout.addWidget(QLabel("Repeat:"))
        days_row = QHBoxLayout()
        self._day_checkboxes: list[QCheckBox] = []
        for day_label in _DAY_LABELS:
            checkbox = QCheckBox(day_label)
            self._day_checkboxes.append(checkbox)
            days_row.addWidget(checkbox)
        layout.addLayout(days_row)

        hint = QLabel("Leave all unchecked for a one-time alarm.")
        hint.setObjectName("SubtitleLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(alarm)

        self._label: str = ""
        self._time: str = ""
        self._days: list[int] = []

    def _prefill(self, alarm: Optional[Alarm]) -> None:
        if alarm is not None:
            self.label_edit.setText(alarm.label)
            self.time_edit.setTime(QTime.fromString(alarm.time, _TIME_FORMAT))
            for day in alarm.days:
                self._day_checkboxes[day].setChecked(True)
        else:
            self.time_edit.setTime(QTime.currentTime())

    def _on_accept(self) -> None:
        self._label = self.label_edit.text().strip()
        self._time = self.time_edit.time().toString(_TIME_FORMAT)
        self._days = [i for i, cb in enumerate(self._day_checkboxes) if cb.isChecked()]
        self.accept()

    @property
    def entered_label(self) -> str:
        return self._label

    @property
    def entered_time(self) -> str:
        return self._time

    @property
    def entered_days(self) -> list[int]:
        return self._days
