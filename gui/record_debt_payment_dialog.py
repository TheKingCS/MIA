"""
gui.record_debt_payment_dialog
=================================

Small dialog used when recording a payment against a Debt — asks for
the payment date (defaults to today) and an amount (defaulted to the
debt's minimum_payment, editable for an extra/payoff-focused payment).
Mirrors gui/mark_income_received_dialog.py's shape, minus the
override-checkbox pattern: unlike an income source's expected amount,
a debt payment amount is meant to be changed freely (paying more than
the minimum is the entire point of a payoff strategy), so the field
starts pre-filled and editable rather than disabled behind a checkbox.
"""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QVBoxLayout,
)

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class RecordDebtPaymentDialog(QDialog):
    def __init__(self, parent=None, default_amount: float = 0.0) -> None:
        super().__init__(parent)
        self.setWindowTitle("Record Debt Payment")
        self.setFixedSize(320, 220)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Paid on:"))
        self.paid_date_edit = QDateEdit()
        self.paid_date_edit.setCalendarPopup(True)
        self.paid_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.paid_date_edit.setDate(QDate.currentDate())
        layout.addWidget(self.paid_date_edit)

        layout.addWidget(QLabel("Amount ($):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.0, 1_000_000.0)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(default_amount)
        layout.addWidget(self.amount_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._paid_date: str = ""
        self._amount: float = 0.0

    def _on_accept(self) -> None:
        self._paid_date = self.paid_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._amount = self.amount_spin.value()
        self.accept()

    @property
    def entered_paid_date(self) -> str:
        return self._paid_date

    @property
    def entered_amount(self) -> float:
        return self._amount
