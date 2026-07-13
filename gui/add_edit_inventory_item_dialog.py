"""
gui.add_edit_inventory_item_dialog
=====================================

Small dialog for creating or editing a single inventory item, used by
modules/toolbox/tools/inventory_tool.py. Same shape as
gui/add_edit_journal_entry_dialog.py (QDialog + the shared app-level theme +
QDialogButtonBox, validate-then-expose-via-properties on accept) —
name/quantity/category/location/notes instead of title/tags/body.
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

from core.inventory_manager import InventoryItem


class AddEditInventoryItemDialog(QDialog):
    def __init__(self, parent=None, item: Optional[InventoryItem] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Item" if item is not None else "New Item")
        self.setFixedSize(360, 460)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Quantity:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 1_000_000)
        layout.addWidget(self.quantity_spin)

        layout.addWidget(QLabel("Category:"))
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("Category (optional)")
        layout.addWidget(self.category_edit)

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

        self._prefill(item)

        self._name: str = ""
        self._quantity: int = 0
        self._category: str = ""
        self._location: str = ""
        self._notes: str = ""

    def _prefill(self, item: Optional[InventoryItem]) -> None:
        if item is not None:
            self.name_edit.setText(item.name)
            self.quantity_spin.setValue(item.quantity)
            self.category_edit.setText(item.category)
            self.location_edit.setText(item.location)
            self.notes_edit.setPlainText(item.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._quantity = self.quantity_spin.value()
        self._category = self.category_edit.text().strip()
        self._location = self.location_edit.text().strip()
        self._notes = self.notes_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_quantity(self) -> int:
        return self._quantity

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_location(self) -> str:
        return self._location

    @property
    def entered_notes(self) -> str:
        return self._notes
