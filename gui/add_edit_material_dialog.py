"""
gui.add_edit_material_dialog
===============================

Small dialog for creating or editing a single fabrication material,
used by modules/workshop/module.py's Materials tab. Same shape as
gui/add_edit_component_dialog.py — name/unit/unit_cost/quantity_on_hand/
reorder_threshold/supplier/location/notes instead of
name/category/value/package/quantity/location/notes.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.material_manager import Material


class AddEditMaterialDialog(QDialog):
    def __init__(self, parent=None, material: Optional[Material] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Material" if material is not None else "New Material")
        self.setFixedSize(360, 560)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Unit:"))
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("e.g. sheet, kg, spool, ft")
        layout.addWidget(self.unit_edit)

        layout.addWidget(QLabel("Unit Cost ($):"))
        self.unit_cost_spin = QDoubleSpinBox()
        self.unit_cost_spin.setRange(0, 1_000_000)
        self.unit_cost_spin.setDecimals(2)
        layout.addWidget(self.unit_cost_spin)

        layout.addWidget(QLabel("Quantity on Hand:"))
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 1_000_000)
        self.quantity_spin.setDecimals(2)
        layout.addWidget(self.quantity_spin)

        layout.addWidget(QLabel("Reorder Threshold:"))
        self.reorder_spin = QDoubleSpinBox()
        self.reorder_spin.setRange(0, 1_000_000)
        self.reorder_spin.setDecimals(2)
        layout.addWidget(self.reorder_spin)

        layout.addWidget(QLabel("Supplier:"))
        self.supplier_edit = QLineEdit()
        self.supplier_edit.setPlaceholderText("Supplier (optional)")
        layout.addWidget(self.supplier_edit)

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

        self._prefill(material)

        self._name: str = ""
        self._unit: str = ""
        self._unit_cost: float = 0.0
        self._quantity_on_hand: float = 0.0
        self._reorder_threshold: float = 0.0
        self._supplier: str = ""
        self._location: str = ""
        self._notes: str = ""

    def _prefill(self, material: Optional[Material]) -> None:
        if material is not None:
            self.name_edit.setText(material.name)
            self.unit_edit.setText(material.unit)
            self.unit_cost_spin.setValue(material.unit_cost)
            self.quantity_spin.setValue(material.quantity_on_hand)
            self.reorder_spin.setValue(material.reorder_threshold)
            self.supplier_edit.setText(material.supplier)
            self.location_edit.setText(material.location)
            self.notes_edit.setPlainText(material.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._unit = self.unit_edit.text().strip()
        self._unit_cost = self.unit_cost_spin.value()
        self._quantity_on_hand = self.quantity_spin.value()
        self._reorder_threshold = self.reorder_spin.value()
        self._supplier = self.supplier_edit.text().strip()
        self._location = self.location_edit.text().strip()
        self._notes = self.notes_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_unit(self) -> str:
        return self._unit

    @property
    def entered_unit_cost(self) -> float:
        return self._unit_cost

    @property
    def entered_quantity_on_hand(self) -> float:
        return self._quantity_on_hand

    @property
    def entered_reorder_threshold(self) -> float:
        return self._reorder_threshold

    @property
    def entered_supplier(self) -> str:
        return self._supplier

    @property
    def entered_location(self) -> str:
        return self._location

    @property
    def entered_notes(self) -> str:
        return self._notes
