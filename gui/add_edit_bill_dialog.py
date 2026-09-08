"""
gui.add_edit_bill_dialog
===========================

Small dialog for creating or editing a single recurring/one-time bill,
used by modules/budget/module.py. Same shape as
gui/add_edit_event_dialog.py (QDialog + shared app-level theme +
QDialogButtonBox, validate-then-expose-via-properties on accept) — the
Repeats combo is deliberately identical in shape (same
core.calendar_manager.RECURRENCE_TYPES vocabulary/option order) so the
two dialogs stay in lockstep if that vocabulary ever changes.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.budget_manager import EXPENSE_CATEGORIES, Bill
from core.calendar_manager import RECURRENCE_TYPES

_ISO_DATE_FORMAT = "yyyy-MM-dd"
_RECURRENCE_LABELS = [("Never", None)] + [(r.capitalize(), r) for r in RECURRENCE_TYPES]


class AddEditBillDialog(QDialog):
    def __init__(self, parent=None, bill: Optional[Bill] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Bill" if bill is not None else "New Bill")
        self.setFixedSize(360, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Electric, Mortgage, Internet")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Amount ($):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.0, 1_000_000.0)
        self.amount_spin.setDecimals(2)
        layout.addWidget(self.amount_spin)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(EXPENSE_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Due Date:"))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.due_date_edit)

        layout.addWidget(QLabel("Repeats:"))
        self.recurrence_combo = QComboBox()
        for label, _value in _RECURRENCE_LABELS:
            self.recurrence_combo.addItem(label)
        layout.addWidget(self.recurrence_combo)

        self.tax_relevant_checkbox = QCheckBox("Tax relevant")
        layout.addWidget(self.tax_relevant_checkbox)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(bill)

        self._name: str = ""
        self._amount: float = 0.0
        self._category: str = EXPENSE_CATEGORIES[0]
        self._due_date: str = ""
        self._recurrence: Optional[str] = None
        self._tax_relevant: bool = False
        self._notes: str = ""

    def _prefill(self, bill: Optional[Bill]) -> None:
        if bill is not None:
            self.name_edit.setText(bill.name)
            self.amount_spin.setValue(bill.amount)
            if bill.category in EXPENSE_CATEGORIES:
                self.category_combo.setCurrentText(bill.category)
            if bill.due_date:
                self.due_date_edit.setDate(QDate.fromString(bill.due_date, _ISO_DATE_FORMAT))
            recurrence_index = next(
                (i for i, (_label, value) in enumerate(_RECURRENCE_LABELS) if value == bill.recurrence), 0
            )
            self.recurrence_combo.setCurrentIndex(recurrence_index)
            self.tax_relevant_checkbox.setChecked(bill.tax_relevant)
            self.notes_edit.setPlainText(bill.notes)
        else:
            self.due_date_edit.setDate(QDate.currentDate())

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._amount = self.amount_spin.value()
        self._category = self.category_combo.currentText()
        self._due_date = self.due_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._recurrence = _RECURRENCE_LABELS[self.recurrence_combo.currentIndex()][1]
        self._tax_relevant = self.tax_relevant_checkbox.isChecked()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_amount(self) -> float:
        return self._amount

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_due_date(self) -> str:
        return self._due_date

    @property
    def entered_recurrence(self) -> Optional[str]:
        return self._recurrence

    @property
    def entered_tax_relevant(self) -> bool:
        return self._tax_relevant

    @property
    def entered_notes(self) -> str:
        return self._notes
