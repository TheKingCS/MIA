"""
gui.add_edit_property_dialog
===============================

Small dialog for creating or editing a single real estate property,
used by modules/real_estate/module.py. Same shape as
gui/add_edit_bill_dialog.py (QDialog + shared app-level theme +
QDialogButtonBox, validate-then-expose-via-properties on accept).
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
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.real_estate_manager import PROPERTY_TYPES, Property

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditPropertyDialog(QDialog):
    def __init__(self, parent=None, property_: Optional[Property] = None, entities: Optional[list] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Property" if property_ is not None else "New Property")
        self.setFixedSize(360, 860)

        self._entities = entities or []
        self._is_new = property_ is None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 123 Main St, Lake Cabin")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(PROPERTY_TYPES)
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("Purchase Date:"))
        self.purchase_date_edit = QDateEdit()
        self.purchase_date_edit.setCalendarPopup(True)
        self.purchase_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.purchase_date_edit.dateChanged.connect(self._on_purchase_date_changed)
        layout.addWidget(self.purchase_date_edit)

        layout.addWidget(QLabel("Placed in Service Date:"))
        self.placed_in_service_date_edit = QDateEdit()
        self.placed_in_service_date_edit.setCalendarPopup(True)
        self.placed_in_service_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.placed_in_service_date_edit)

        layout.addWidget(QLabel("Purchase Price ($):"))
        self.purchase_price_spin = QDoubleSpinBox()
        self.purchase_price_spin.setRange(0.0, 100_000_000.0)
        self.purchase_price_spin.setDecimals(2)
        layout.addWidget(self.purchase_price_spin)

        layout.addWidget(QLabel("Land Value ($):"))
        self.land_value_spin = QDoubleSpinBox()
        self.land_value_spin.setRange(0.0, 100_000_000.0)
        self.land_value_spin.setDecimals(2)
        layout.addWidget(self.land_value_spin)

        layout.addWidget(QLabel("Current Value ($):"))
        self.current_value_spin = QDoubleSpinBox()
        self.current_value_spin.setRange(0.0, 100_000_000.0)
        self.current_value_spin.setDecimals(2)
        layout.addWidget(self.current_value_spin)

        layout.addWidget(QLabel("Mortgage Balance ($):"))
        self.mortgage_balance_spin = QDoubleSpinBox()
        self.mortgage_balance_spin.setRange(0.0, 100_000_000.0)
        self.mortgage_balance_spin.setDecimals(2)
        layout.addWidget(self.mortgage_balance_spin)

        layout.addWidget(QLabel("Original Loan Amount ($):"))
        self.original_loan_amount_spin = QDoubleSpinBox()
        self.original_loan_amount_spin.setRange(0.0, 100_000_000.0)
        self.original_loan_amount_spin.setDecimals(2)
        layout.addWidget(self.original_loan_amount_spin)

        layout.addWidget(QLabel("Interest Rate (% APR):"))
        self.interest_rate_spin = QDoubleSpinBox()
        self.interest_rate_spin.setRange(0.0, 25.0)
        self.interest_rate_spin.setDecimals(3)
        self.interest_rate_spin.setSingleStep(0.125)
        layout.addWidget(self.interest_rate_spin)

        layout.addWidget(QLabel("Loan Term (months, e.g. 360 for 30 years):"))
        self.loan_term_months_spin = QSpinBox()
        self.loan_term_months_spin.setRange(0, 600)
        layout.addWidget(self.loan_term_months_spin)

        layout.addWidget(QLabel("Loan Start Date:"))
        self.loan_start_date_edit = QDateEdit()
        self.loan_start_date_edit.setCalendarPopup(True)
        self.loan_start_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.loan_start_date_edit)

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

        self._prefill(property_)

        self._name: str = ""
        self._property_type: str = PROPERTY_TYPES[0]
        self._purchase_date: str = ""
        self._purchase_price: float = 0.0
        self._current_value: float = 0.0
        self._mortgage_balance: float = 0.0
        self._entity_id: str = ""
        self._land_value: float = 0.0
        self._placed_in_service_date: str = ""
        self._original_loan_amount: float = 0.0
        self._interest_rate_pct: float = 0.0
        self._loan_term_months: int = 0
        self._loan_start_date: str = ""
        self._notes: str = ""

    def _prefill(self, property_: Optional[Property]) -> None:
        if property_ is not None:
            self.name_edit.setText(property_.name)
            if property_.property_type in PROPERTY_TYPES:
                self.type_combo.setCurrentText(property_.property_type)
            if property_.purchase_date:
                self.purchase_date_edit.setDate(QDate.fromString(property_.purchase_date, _ISO_DATE_FORMAT))
            placed_in_service = property_.placed_in_service_date or property_.purchase_date
            if placed_in_service:
                self.placed_in_service_date_edit.setDate(QDate.fromString(placed_in_service, _ISO_DATE_FORMAT))
            self.purchase_price_spin.setValue(property_.purchase_price)
            self.land_value_spin.setValue(property_.land_value)
            self.current_value_spin.setValue(property_.current_value)
            self.mortgage_balance_spin.setValue(property_.mortgage_balance)
            self.original_loan_amount_spin.setValue(property_.original_loan_amount)
            self.interest_rate_spin.setValue(property_.interest_rate_pct)
            self.loan_term_months_spin.setValue(property_.loan_term_months)
            loan_start = property_.loan_start_date or property_.purchase_date
            if loan_start:
                self.loan_start_date_edit.setDate(QDate.fromString(loan_start, _ISO_DATE_FORMAT))
            if property_.entity_id:
                idx = self.entity_combo.findData(property_.entity_id)
                self.entity_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.notes_edit.setPlainText(property_.notes)
        else:
            self.purchase_date_edit.setDate(QDate.currentDate())
            self.placed_in_service_date_edit.setDate(QDate.currentDate())
            self.loan_start_date_edit.setDate(QDate.currentDate())

    def _on_purchase_date_changed(self, new_date: QDate) -> None:
        """Keeps Placed in Service Date AND Loan Start Date tracking
        Purchase Date for a brand-new property (no real value to
        override yet) — once the dialog is editing an existing
        property, all three are independent and this sync never fires
        again (see _is_new)."""
        if self._is_new:
            self.placed_in_service_date_edit.setDate(new_date)
            self.loan_start_date_edit.setDate(new_date)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._property_type = self.type_combo.currentText()
        self._purchase_date = self.purchase_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._purchase_price = self.purchase_price_spin.value()
        self._current_value = self.current_value_spin.value()
        self._mortgage_balance = self.mortgage_balance_spin.value()
        self._entity_id = self.entity_combo.currentData()
        self._land_value = self.land_value_spin.value()
        self._placed_in_service_date = self.placed_in_service_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._original_loan_amount = self.original_loan_amount_spin.value()
        self._interest_rate_pct = self.interest_rate_spin.value()
        self._loan_term_months = self.loan_term_months_spin.value()
        self._loan_start_date = self.loan_start_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_property_type(self) -> str:
        return self._property_type

    @property
    def entered_purchase_date(self) -> str:
        return self._purchase_date

    @property
    def entered_purchase_price(self) -> float:
        return self._purchase_price

    @property
    def entered_current_value(self) -> float:
        return self._current_value

    @property
    def entered_mortgage_balance(self) -> float:
        return self._mortgage_balance

    @property
    def entered_entity_id(self) -> str:
        return self._entity_id

    @property
    def entered_land_value(self) -> float:
        return self._land_value

    @property
    def entered_placed_in_service_date(self) -> str:
        return self._placed_in_service_date

    @property
    def entered_original_loan_amount(self) -> float:
        return self._original_loan_amount

    @property
    def entered_interest_rate_pct(self) -> float:
        return self._interest_rate_pct

    @property
    def entered_loan_term_months(self) -> int:
        return self._loan_term_months

    @property
    def entered_loan_start_date(self) -> str:
        return self._loan_start_date

    @property
    def entered_notes(self) -> str:
        return self._notes
