"""
gui.add_edit_pantry_item_dialog
==================================

Small dialog for creating or editing a single pantry item, used by
modules/kitchen/module.py. Same "checkbox toggles an optional field"
shape gui/add_edit_property_dialog.py's own Placed in Service Date
sync established — here a "Track expiration date" checkbox toggles
the date field, since an untracked expiration is a real, common case
(dry goods, spices) not every item has one.
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
    QVBoxLayout,
)

from core.kitchen_manager import PANTRY_CATEGORIES, PantryItem

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditPantryItemDialog(QDialog):
    def __init__(self, parent=None, item: Optional[PantryItem] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Pantry Item" if item is not None else "New Pantry Item")
        self.setFixedSize(360, 420)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Flour")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Quantity:"))
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.0, 10_000.0)
        self.quantity_spin.setDecimals(2)
        layout.addWidget(self.quantity_spin)

        layout.addWidget(QLabel("Unit:"))
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("e.g. lbs, cups, each (optional)")
        layout.addWidget(self.unit_edit)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(PANTRY_CATEGORIES)
        layout.addWidget(self.category_combo)

        self.expiration_checkbox = QCheckBox("Track expiration date")
        self.expiration_checkbox.toggled.connect(self._on_expiration_toggle)
        layout.addWidget(self.expiration_checkbox)

        self.expiration_date_edit = QDateEdit()
        self.expiration_date_edit.setCalendarPopup(True)
        self.expiration_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        self.expiration_date_edit.setDate(QDate.currentDate())
        self.expiration_date_edit.setEnabled(False)
        layout.addWidget(self.expiration_date_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(item)

        self._name: str = ""
        self._quantity: float = 0.0
        self._unit: str = ""
        self._category: str = PANTRY_CATEGORIES[0]
        self._expiration_date: str = ""
        self._notes: str = ""

    def _on_expiration_toggle(self, checked: bool) -> None:
        self.expiration_date_edit.setEnabled(checked)

    def _prefill(self, item: Optional[PantryItem]) -> None:
        if item is None:
            return
        self.name_edit.setText(item.name)
        self.quantity_spin.setValue(item.quantity)
        self.unit_edit.setText(item.unit)
        if item.category in PANTRY_CATEGORIES:
            self.category_combo.setCurrentText(item.category)
        if item.expiration_date:
            self.expiration_checkbox.setChecked(True)
            self.expiration_date_edit.setDate(QDate.fromString(item.expiration_date, _ISO_DATE_FORMAT))
        self.notes_edit.setText(item.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._quantity = self.quantity_spin.value()
        self._unit = self.unit_edit.text().strip()
        self._category = self.category_combo.currentText()
        self._expiration_date = (
            self.expiration_date_edit.date().toString(_ISO_DATE_FORMAT) if self.expiration_checkbox.isChecked() else ""
        )
        self._notes = self.notes_edit.text().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_quantity(self) -> float:
        return self._quantity

    @property
    def entered_unit(self) -> str:
        return self._unit

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_expiration_date(self) -> str:
        return self._expiration_date

    @property
    def entered_notes(self) -> str:
        return self._notes
