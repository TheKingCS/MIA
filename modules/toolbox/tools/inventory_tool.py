"""
modules.toolbox.tools.inventory_tool
=======================================

Inventory — a ToolboxTool (modules/toolbox/tool_base.py), milestone
3.5 in docs/ROADMAP.md, completing the v0.3 Toolbox breakdown. A
filterable list of items (name/quantity/category/location) with
Add/Edit/Delete plus quick +1/-1 buttons for the common case of
adjusting a count without opening the full edit dialog. Backed by
core.inventory_manager.InventoryManager for persistence.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.inventory_manager import InventoryItem
from gui.add_edit_inventory_item_dialog import AddEditInventoryItemDialog
from modules.toolbox.tool_base import ToolboxTool


def format_item_row(item: InventoryItem) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_inventory_tool.py)."""
    parts = [f"{item.name}  —  qty {item.quantity}"]
    if item.category:
        parts.append(f"[{item.category}]")
    if item.location:
        parts.append(f"@ {item.location}")
    return "  ".join(parts)


class InventoryTool(ToolboxTool):
    tool_id = "inventory"
    display_name = "Inventory"
    description = "Track items, quantities, categories, and locations."
    icon = "📦"  # package

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list: Optional[QListWidget] = None
        self._filter_edit: Optional[QLineEdit] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter by name, category, or location…")
        self._filter_edit.textChanged.connect(lambda _text: self._refresh_list())
        layout.addWidget(self._filter_edit)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)

        adjust_row = QHBoxLayout()
        adjust_row.addWidget(QLabel("Quantity:"))

        minus_button = QPushButton("−1")
        minus_button.clicked.connect(lambda: self._on_adjust(-1))
        adjust_row.addWidget(minus_button)

        plus_button = QPushButton("+1")
        plus_button.clicked.connect(lambda: self._on_adjust(1))
        adjust_row.addWidget(plus_button)

        adjust_row.addStretch()
        layout.addLayout(adjust_row)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Item")
        add_button.clicked.connect(self._on_add)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_list(self, select_item_id: Optional[str] = None) -> None:
        query = self._filter_edit.text().strip()
        items = self.context.inventory.search(query) if query else self.context.inventory.all_items()

        self._list.clear()
        for item in items:
            list_item = QListWidgetItem(format_item_row(item))
            list_item.setData(Qt.ItemDataRole.UserRole, item.item_id)
            self._list.addItem(list_item)
            if item.item_id == select_item_id:
                self._list.setCurrentItem(list_item)

    def _selected_item_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        dialog = AddEditInventoryItemDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        added = self.context.inventory.add_item(
            name=dialog.entered_name,
            quantity=dialog.entered_quantity,
            category=dialog.entered_category,
            location=dialog.entered_location,
            notes=dialog.entered_notes,
        )
        self._refresh_list(select_item_id=added.item_id)

    def _on_edit(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Item Selected", "Select an item to edit.")
            return

        item = self.context.inventory.get_item(item_id)
        dialog = AddEditInventoryItemDialog(item=item)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.inventory.update_item(
            item_id,
            name=dialog.entered_name,
            quantity=dialog.entered_quantity,
            category=dialog.entered_category,
            location=dialog.entered_location,
            notes=dialog.entered_notes,
        )
        self._refresh_list(select_item_id=item_id)

    def _on_delete(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Item Selected", "Select an item to delete.")
            return

        item = self.context.inventory.get_item(item_id)
        confirm = QMessageBox.question(
            None,
            "Delete Item",
            f"Delete '{item.name}' from inventory?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.inventory.delete_item(item_id)
        self._refresh_list()

    def _on_adjust(self, delta: int) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            QMessageBox.information(None, "No Item Selected", "Select an item to adjust.")
            return

        self.context.inventory.adjust_quantity(item_id, delta)
        self._refresh_list(select_item_id=item_id)
