"""
gui.add_edit_ingredient_dialog
=================================

Small dialog for adding one ingredient to a recipe — opened from the
recipe detail page in modules/kitchen/module.py, one ingredient at a
time (same real precedent gui/pick_item_quantity_dialog.py's own
docstring establishes: a small single-item dialog, not an embedded
multi-row table editor). Unit is a freeform QLineEdit — no unit-
conversion system exists in core/kitchen_manager.py, so this is
deliberately not a fixed-choice combo.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class AddEditIngredientDialog(QDialog):
    def __init__(self, parent=None, ingredient: Optional[dict] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Ingredient" if ingredient is not None else "Add Ingredient")
        self.setFixedSize(340, 320)

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
        self.unit_edit.setPlaceholderText("e.g. cups, oz, lbs, each (optional)")
        layout.addWidget(self.unit_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("e.g. sifted, room temperature (optional)")
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(ingredient)

        self._name: str = ""
        self._quantity: float = 0.0
        self._unit: str = ""
        self._notes: str = ""

    def _prefill(self, ingredient: Optional[dict]) -> None:
        if ingredient is None:
            return
        self.name_edit.setText(str(ingredient.get("name", "")))
        self.quantity_spin.setValue(ingredient.get("quantity") or 0.0)
        self.unit_edit.setText(str(ingredient.get("unit", "")))
        self.notes_edit.setText(str(ingredient.get("notes", "")))

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._quantity = self.quantity_spin.value()
        self._unit = self.unit_edit.text().strip()
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
    def entered_notes(self) -> str:
        return self._notes
