"""
gui.add_edit_component_dialog
================================

Small dialog for creating or editing a single electronics component,
used by modules/workshop/module.py. Same shape as
gui/add_edit_inventory_item_dialog.py (QDialog + DARK_FIELD_THEME +
QDialogButtonBox, validate-then-expose-via-properties on accept) —
name/category/value/package/quantity/location/notes instead of
name/quantity/category/location/notes.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.component_manager import Component
from gui.styles import DARK_FIELD_THEME


class AddEditComponentDialog(QDialog):
    def __init__(self, parent=None, component: Optional[Component] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Component" if component is not None else "New Component")
        self.setStyleSheet(DARK_FIELD_THEME)
        self.setFixedSize(360, 560)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category:"))
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("e.g. Resistor, Capacitor, IC")
        layout.addWidget(self.category_edit)

        layout.addWidget(QLabel("Value:"))
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("e.g. 10k, 100nF")
        layout.addWidget(self.value_edit)

        layout.addWidget(QLabel("Package:"))
        self.package_edit = QLineEdit()
        self.package_edit.setPlaceholderText("e.g. THT, 0805")
        layout.addWidget(self.package_edit)

        layout.addWidget(QLabel("Quantity:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 1_000_000)
        layout.addWidget(self.quantity_spin)

        layout.addWidget(QLabel("Location:"))
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Location (optional)")
        layout.addWidget(self.location_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        layout.addWidget(self.notes_edit, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(component)

        self._name: str = ""
        self._category: str = ""
        self._value: str = ""
        self._package: str = ""
        self._quantity: int = 0
        self._location: str = ""
        self._notes: str = ""

    def _prefill(self, component: Optional[Component]) -> None:
        if component is not None:
            self.name_edit.setText(component.name)
            self.category_edit.setText(component.category)
            self.value_edit.setText(component.value)
            self.package_edit.setText(component.package)
            self.quantity_spin.setValue(component.quantity)
            self.location_edit.setText(component.location)
            self.notes_edit.setPlainText(component.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._category = self.category_edit.text().strip()
        self._value = self.value_edit.text().strip()
        self._package = self.package_edit.text().strip()
        self._quantity = self.quantity_spin.value()
        self._location = self.location_edit.text().strip()
        self._notes = self.notes_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_value(self) -> str:
        return self._value

    @property
    def entered_package(self) -> str:
        return self._package

    @property
    def entered_quantity(self) -> int:
        return self._quantity

    @property
    def entered_location(self) -> str:
        return self._location

    @property
    def entered_notes(self) -> str:
        return self._notes
