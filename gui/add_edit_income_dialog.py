"""
gui.add_edit_income_dialog
=============================

Small dialog for creating or editing a single income entry, used by
modules/budget/module.py. Same shape as gui/add_edit_journal_entry_dialog.py
(QDialog + shared app-level theme + QDialogButtonBox, validate-then-
expose-via-properties on accept).

The optional Entity combo (2026-09-08, LLC tagging) is populated from
whatever BusinessEntity list the caller passes in — this dialog never
reads context.budget itself, staying consistent with its existing
context-free shape.
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

from core.budget_manager import INCOME_CATEGORIES, IncomeEntry

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditIncomeDialog(QDialog):
    def __init__(self, parent=None, entry: Optional[IncomeEntry] = None, entities: Optional[list] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Income" if entry is not None else "New Income")
        self.setFixedSize(360, 480)

        self._entities = entities or []

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Amount ($):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.0, 1_000_000.0)
        self.amount_spin.setDecimals(2)
        layout.addWidget(self.amount_spin)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(INCOME_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g. September paycheck, 123 Main St rent")
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.date_edit)

        layout.addWidget(QLabel("Entity:"))
        self.entity_combo = QComboBox()
        self.entity_combo.addItem("(Unassigned)", "")
        for ent in self._entities:
            self.entity_combo.addItem(ent.name, ent.entity_id)
        layout.addWidget(self.entity_combo)

        self.tax_relevant_checkbox = QCheckBox("Tax relevant")
        self.tax_relevant_checkbox.setChecked(True)
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

        self._prefill(entry)

        self._amount: float = 0.0
        self._category: str = INCOME_CATEGORIES[0]
        self._description: str = ""
        self._date: str = ""
        self._entity_id: str = ""
        self._tax_relevant: bool = True
        self._notes: str = ""

    def _prefill(self, entry: Optional[IncomeEntry]) -> None:
        if entry is not None:
            self.amount_spin.setValue(entry.amount)
            if entry.category in INCOME_CATEGORIES:
                self.category_combo.setCurrentText(entry.category)
            self.description_edit.setText(entry.description)
            if entry.date:
                self.date_edit.setDate(QDate.fromString(entry.date, _ISO_DATE_FORMAT))
            if entry.entity_id:
                idx = self.entity_combo.findData(entry.entity_id)
                self.entity_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.tax_relevant_checkbox.setChecked(entry.tax_relevant)
            self.notes_edit.setPlainText(entry.notes)
        else:
            self.date_edit.setDate(QDate.currentDate())

    def _on_accept(self) -> None:
        self._amount = self.amount_spin.value()
        self._category = self.category_combo.currentText()
        self._description = self.description_edit.text().strip()
        self._date = self.date_edit.date().toString(_ISO_DATE_FORMAT)
        self._entity_id = self.entity_combo.currentData()
        self._tax_relevant = self.tax_relevant_checkbox.isChecked()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_amount(self) -> float:
        return self._amount

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_date(self) -> str:
        return self._date

    @property
    def entered_entity_id(self) -> str:
        return self._entity_id

    @property
    def entered_tax_relevant(self) -> bool:
        return self._tax_relevant

    @property
    def entered_notes(self) -> str:
        return self._notes
