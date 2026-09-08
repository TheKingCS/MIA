"""
gui.add_edit_income_source_dialog
====================================

Small dialog for creating or editing a single recurring/expected income
source, used by modules/budget/module.py's Income Sources tab. Mirrors
gui/add_edit_bill_dialog.py's shape exactly — same Repeats combo built
from core.calendar_manager.RECURRENCE_TYPES, same validate-then-expose-
via-properties on accept.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
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

from core.budget_manager import INCOME_CATEGORIES, IncomeSource
from core.calendar_manager import RECURRENCE_TYPES

_ISO_DATE_FORMAT = "yyyy-MM-dd"
_RECURRENCE_LABELS = [("Never", None)] + [(r.capitalize(), r) for r in RECURRENCE_TYPES]


class AddEditIncomeSourceDialog(QDialog):
    def __init__(self, parent=None, income_source: Optional[IncomeSource] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Income Source" if income_source is not None else "New Income Source")
        self.setFixedSize(360, 460)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Paycheck, Rental — 123 Main St")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Expected Amount ($):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.0, 1_000_000.0)
        self.amount_spin.setDecimals(2)
        layout.addWidget(self.amount_spin)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(INCOME_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Next Date:"))
        self.next_date_edit = QDateEdit()
        self.next_date_edit.setCalendarPopup(True)
        self.next_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.next_date_edit)

        layout.addWidget(QLabel("Repeats:"))
        self.recurrence_combo = QComboBox()
        for label, _value in _RECURRENCE_LABELS:
            self.recurrence_combo.addItem(label)
        layout.addWidget(self.recurrence_combo)

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

        self._prefill(income_source)

        self._name: str = ""
        self._amount: float = 0.0
        self._category: str = INCOME_CATEGORIES[0]
        self._next_date: str = ""
        self._recurrence: Optional[str] = None
        self._notes: str = ""

    def _prefill(self, income_source: Optional[IncomeSource]) -> None:
        if income_source is not None:
            self.name_edit.setText(income_source.name)
            self.amount_spin.setValue(income_source.expected_amount)
            if income_source.category in INCOME_CATEGORIES:
                self.category_combo.setCurrentText(income_source.category)
            if income_source.next_date:
                self.next_date_edit.setDate(QDate.fromString(income_source.next_date, _ISO_DATE_FORMAT))
            recurrence_index = next(
                (i for i, (_label, value) in enumerate(_RECURRENCE_LABELS) if value == income_source.recurrence), 0
            )
            self.recurrence_combo.setCurrentIndex(recurrence_index)
            self.notes_edit.setPlainText(income_source.notes)
        else:
            self.next_date_edit.setDate(QDate.currentDate())

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._amount = self.amount_spin.value()
        self._category = self.category_combo.currentText()
        self._next_date = self.next_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._recurrence = _RECURRENCE_LABELS[self.recurrence_combo.currentIndex()][1]
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
    def entered_next_date(self) -> str:
        return self._next_date

    @property
    def entered_recurrence(self) -> Optional[str]:
        return self._recurrence

    @property
    def entered_notes(self) -> str:
        return self._notes
