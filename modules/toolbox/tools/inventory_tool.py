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


def format_item_detail_line(
    added_by_name: Optional[str], times_used: int, last_used_by_name: Optional[str], last_used_date: Optional[str]
) -> str:
    """Pure formatting logic — testable without Qt. Multi-user pass
    (2026-09-14) — the same "shared object + user relationship" pattern
    core.kitchen_manager's own Recipe detail view already surfaces,
    scaled down to this tool's single-line-per-item list shape rather
    than a full HOUSEHOLD/YOUR STATS card pair (Inventory items don't
    have subjective opinions like a recipe rating/favorite to show a
    second card for)."""
    added_part = f"Added by {added_by_name}" if added_by_name else "Added by: unknown"
    if times_used:
        used_part = f"Used {times_used}x"
        if last_used_by_name and last_used_date:
            used_part += f" (last: {last_used_by_name} on {last_used_date})"
        elif last_used_date:
            used_part += f" (last: {last_used_date})"
    else:
        used_part = "Never used yet"
    return f"{added_part}  ·  {used_part}"


class InventoryTool(ToolboxTool):
    tool_id = "inventory"
    display_name = "Inventory"
    description = "Track items, quantities, categories, and locations."
    icon = "📦"  # package

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list: Optional[QListWidget] = None
        self._filter_edit: Optional[QLineEdit] = None
        self._detail_label: Optional[QLabel] = None

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
        self._list.currentItemChanged.connect(lambda *_: self._update_detail_label())
        layout.addWidget(self._list, stretch=1)

        # Multi-user pass (2026-09-14) — who added this item + real
        # usage history for the selected item, the same "shared object
        # + user relationship" pattern core.kitchen_manager's own Recipe
        # detail view surfaces, scaled to this tool's simpler list
        # shape (see format_item_detail_line()'s own docstring).
        self._detail_label = QLabel("")
        self._detail_label.setObjectName("SubtitleLabel")
        self._detail_label.setWordWrap(True)
        layout.addWidget(self._detail_label)

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
        self._update_detail_label()

    def _selected_item_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _profile_name(self, profile_id: Optional[str]) -> Optional[str]:
        if profile_id is None or self.context.profiles is None:
            return None
        match = next((p for p in self.context.profiles.list_profiles() if p.profile_id == profile_id), None)
        return match.name if match is not None else None

    def _update_detail_label(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            self._detail_label.setText("")
            return

        item = self.context.inventory.get_item(item_id)
        if item is None:
            self._detail_label.setText("")
            return

        added_by_name = self._profile_name(item.added_by_profile_id)
        times_used = self.context.inventory.times_used(item_id)
        last_used_entry = self.context.inventory.last_used(item_id)
        last_used_by_name = self._profile_name(last_used_entry.profile_id) if last_used_entry else None
        last_used_date = last_used_entry.timestamp[:10] if last_used_entry else None

        self._detail_label.setText(
            format_item_detail_line(added_by_name, times_used, last_used_by_name, last_used_date)
        )

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
