"""
gui.add_edit_debt_dialog
===========================

Small dialog for creating or editing a single Debt, used by
modules/budget/module.py's Debts tab. Mirrors
gui/add_edit_income_source_dialog.py's shape — same validate-then-
expose-via-properties on accept — with one addition: an optional promo
APR + expiration date, disabled by a checkbox until the debt actually
has a promotional offer (a "0% for 12 months" card deal), matching
core.budget_manager.Debt's own "a promo needs a real end date to mean
anything" stance.
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

from core.budget_manager import DEBT_TYPES, Debt

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditDebtDialog(QDialog):
    def __init__(self, parent=None, debt: Optional[Debt] = None, entities: Optional[list] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Debt" if debt is not None else "New Debt")
        self.setFixedSize(360, 620)

        self._entities = entities or []

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Chase Freedom, Sallie Mae Student Loan")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Balance ($):"))
        self.balance_spin = QDoubleSpinBox()
        self.balance_spin.setRange(0.0, 10_000_000.0)
        self.balance_spin.setDecimals(2)
        layout.addWidget(self.balance_spin)

        layout.addWidget(QLabel("Standard Interest Rate (APR %):"))
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.0, 100.0)
        self.rate_spin.setDecimals(2)
        layout.addWidget(self.rate_spin)

        layout.addWidget(QLabel("Minimum Payment ($):"))
        self.minimum_payment_spin = QDoubleSpinBox()
        self.minimum_payment_spin.setRange(0.0, 100_000.0)
        self.minimum_payment_spin.setDecimals(2)
        layout.addWidget(self.minimum_payment_spin)

        layout.addWidget(QLabel("Debt Type:"))
        self.debt_type_combo = QComboBox()
        self.debt_type_combo.addItems(DEBT_TYPES)
        layout.addWidget(self.debt_type_combo)

        self.promo_checkbox = QCheckBox("Has a promotional APR")
        self.promo_checkbox.toggled.connect(self._on_promo_toggle)
        layout.addWidget(self.promo_checkbox)

        layout.addWidget(QLabel("Promo APR (%):"))
        self.promo_rate_spin = QDoubleSpinBox()
        self.promo_rate_spin.setRange(0.0, 100.0)
        self.promo_rate_spin.setDecimals(2)
        self.promo_rate_spin.setEnabled(False)
        layout.addWidget(self.promo_rate_spin)

        layout.addWidget(QLabel("Promo Expires:"))
        self.promo_expires_edit = QDateEdit()
        self.promo_expires_edit.setCalendarPopup(True)
        self.promo_expires_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.promo_expires_edit.setDate(QDate.currentDate())
        self.promo_expires_edit.setEnabled(False)
        layout.addWidget(self.promo_expires_edit)

        layout.addWidget(QLabel("Entity:"))
        self.entity_combo = QComboBox()
        self.entity_combo.addItem("(Unassigned)", "")
        for ent in self._entities:
            self.entity_combo.addItem(ent.name, ent.entity_id)
        layout.addWidget(self.entity_combo)

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

        self._prefill(debt)

        self._name: str = ""
        self._balance: float = 0.0
        self._interest_rate: float = 0.0
        self._minimum_payment: float = 0.0
        self._debt_type: str = DEBT_TYPES[0]
        self._promo_apr: Optional[float] = None
        self._promo_expires_date: Optional[str] = None
        self._entity_id: str = ""
        self._notes: str = ""

    def _on_promo_toggle(self, checked: bool) -> None:
        self.promo_rate_spin.setEnabled(checked)
        self.promo_expires_edit.setEnabled(checked)

    def _prefill(self, debt: Optional[Debt]) -> None:
        if debt is not None:
            self.name_edit.setText(debt.name)
            self.balance_spin.setValue(debt.balance)
            self.rate_spin.setValue(debt.interest_rate)
            self.minimum_payment_spin.setValue(debt.minimum_payment)
            if debt.debt_type in DEBT_TYPES:
                self.debt_type_combo.setCurrentText(debt.debt_type)
            if debt.promo_apr is not None and debt.promo_expires_date:
                self.promo_checkbox.setChecked(True)
                self.promo_rate_spin.setValue(debt.promo_apr)
                self.promo_expires_edit.setDate(QDate.fromString(debt.promo_expires_date, _ISO_DATE_FORMAT))
            if debt.entity_id:
                idx = self.entity_combo.findData(debt.entity_id)
                self.entity_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.notes_edit.setPlainText(debt.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._balance = self.balance_spin.value()
        self._interest_rate = self.rate_spin.value()
        self._minimum_payment = self.minimum_payment_spin.value()
        self._debt_type = self.debt_type_combo.currentText()
        if self.promo_checkbox.isChecked():
            self._promo_apr = self.promo_rate_spin.value()
            self._promo_expires_date = self.promo_expires_edit.date().toString(_ISO_DATE_FORMAT)
        else:
            self._promo_apr = None
            self._promo_expires_date = None
        self._entity_id = self.entity_combo.currentData()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_balance(self) -> float:
        return self._balance

    @property
    def entered_interest_rate(self) -> float:
        return self._interest_rate

    @property
    def entered_minimum_payment(self) -> float:
        return self._minimum_payment

    @property
    def entered_debt_type(self) -> str:
        return self._debt_type

    @property
    def entered_promo_apr(self) -> Optional[float]:
        return self._promo_apr

    @property
    def entered_promo_expires_date(self) -> Optional[str]:
        return self._promo_expires_date

    @property
    def entered_entity_id(self) -> str:
        return self._entity_id

    @property
    def entered_notes(self) -> str:
        return self._notes
