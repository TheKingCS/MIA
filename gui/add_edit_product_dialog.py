"""
gui.add_edit_product_dialog
==============================

Small dialog for creating or editing a single finished-goods product,
used by modules/workshop/module.py's Products tab. Same shape as
gui/add_edit_component_dialog.py — name/description/quantity_in_stock/
base_price/notes. `job_id` (which job produced this batch) isn't
free-typed here — it's set naturally via core/job_manager.py's
produce_product(), not manual entry, same reasoning
gui/add_edit_job_dialog.py doesn't expose material_consumption/
products_produced for manual editing either. `listings` are managed
separately via gui/add_edit_listing_dialog.py's own "Add Listing"
action on the Products tab.
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

from core.product_manager import Product


class AddEditProductDialog(QDialog):
    def __init__(self, parent=None, product: Optional[Product] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Product" if product is not None else "New Product")
        self.setFixedSize(360, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Engraved Coaster Set")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Description (optional)")
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Quantity in Stock:"))
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 1_000_000)
        self.quantity_spin.setDecimals(2)
        layout.addWidget(self.quantity_spin)

        layout.addWidget(QLabel("Base Price ($):"))
        self.base_price_spin = QDoubleSpinBox()
        self.base_price_spin.setRange(0, 1_000_000)
        self.base_price_spin.setDecimals(2)
        layout.addWidget(self.base_price_spin)

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

        self._prefill(product)

        self._name: str = ""
        self._description: str = ""
        self._quantity_in_stock: float = 0.0
        self._base_price: float = 0.0
        self._notes: str = ""

    def _prefill(self, product: Optional[Product]) -> None:
        if product is not None:
            self.name_edit.setText(product.name)
            self.description_edit.setText(product.description)
            self.quantity_spin.setValue(product.quantity_in_stock)
            self.base_price_spin.setValue(product.base_price)
            self.notes_edit.setPlainText(product.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._description = self.description_edit.text().strip()
        self._quantity_in_stock = self.quantity_spin.value()
        self._base_price = self.base_price_spin.value()
        self._notes = self.notes_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_quantity_in_stock(self) -> float:
        return self._quantity_in_stock

    @property
    def entered_base_price(self) -> float:
        return self._base_price

    @property
    def entered_notes(self) -> str:
        return self._notes
