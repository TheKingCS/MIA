"""
gui.add_edit_grocery_item_dialog
===================================

Small dialog for manually adding one item to the grocery list, used by
modules/kitchen/module.py. Items added automatically from a recipe's
missing ingredients (KitchenManager.add_missing_ingredients_to_grocery_list())
never go through this dialog — it's for a manual add only.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class AddEditGroceryItemDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Grocery Item")
        self.setFixedSize(340, 260)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Milk")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Quantity:"))
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.0, 10_000.0)
        self.quantity_spin.setDecimals(2)
        layout.addWidget(self.quantity_spin)

        layout.addWidget(QLabel("Unit:"))
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("e.g. gallon, lbs, each (optional)")
        layout.addWidget(self.unit_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._name: str = ""
        self._quantity: float = 0.0
        self._unit: str = ""

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._quantity = self.quantity_spin.value()
        self._unit = self.unit_edit.text().strip()
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
