"""
gui.mark_bill_paid_dialog
============================

Small dialog used when marking a bill paid — asks for the paid date
(defaults to today) and an optional amount override for a bill that
varies month to month (e.g. an energy bill), same shape as
gui/mark_complete_dialog.py's meter-value override for a completed
Maintenance task.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QVBoxLayout,
)

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class MarkBillPaidDialog(QDialog):
    def __init__(self, parent=None, default_amount: float = 0.0) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mark Bill Paid")
        self.setFixedSize(320, 220)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Paid on:"))
        self.paid_date_edit = QDateEdit()
        self.paid_date_edit.setCalendarPopup(True)
        self.paid_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.paid_date_edit.setDate(QDate.currentDate())
        layout.addWidget(self.paid_date_edit)

        self.override_checkbox = QCheckBox("Amount was different this time")
        self.override_checkbox.toggled.connect(self._on_override_toggle)
        layout.addWidget(self.override_checkbox)

        layout.addWidget(QLabel("Amount ($):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.0, 1_000_000.0)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(default_amount)
        self.amount_spin.setEnabled(False)
        layout.addWidget(self.amount_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._paid_date: str = ""
        self._amount: Optional[float] = None

    def _on_override_toggle(self, checked: bool) -> None:
        self.amount_spin.setEnabled(checked)

    def _on_accept(self) -> None:
        self._paid_date = self.paid_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._amount = self.amount_spin.value() if self.override_checkbox.isChecked() else None
        self.accept()

    @property
    def entered_paid_date(self) -> str:
        return self._paid_date

    @property
    def entered_amount(self) -> Optional[float]:
        return self._amount
