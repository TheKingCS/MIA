"""
modules.workshop.module
=========================

Workshop & Electronics: Component DB — docs/ROADMAP.md milestone 8.3.
A dedicated electronics-parts inventory (name, category, value,
package, quantity, location, notes), backed by
core/component_manager.py (deliberately separate from the general
Inventory tool — see that manager's docstring for why).

This is the one slice of Workshop & Electronics's broad scope
(component DB, MCU flashing, PCB viewer, soldering notes, 3D
printer/CNC/laser, STL/CAD library) buildable with zero real hardware
or files right now; the rest waits for that hardware/tooling to exist.

format_component_row() is a free function (not a method), same
pure-formatting-logic shape as modules/notes/module.py's
format_entry_row() — testable without Qt, see
tests/test_workshop_module.py.
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

from core.component_manager import Component
from gui.add_edit_component_dialog import AddEditComponentDialog
from modules.module_base import ModuleBase


def format_component_row(component: Component) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_workshop_module.py)."""
    detail_parts = [part for part in (component.category, component.value, component.package) if part]
    detail = f"  [{', '.join(detail_parts)}]" if detail_parts else ""
    location = f"  ({component.location})" if component.location else ""
    return f"{component.name}{detail}  qty {component.quantity}{location}"


class WorkshopModule(ModuleBase):
    module_id = "workshop"
    display_name = "Workshop & Electronics"
    description = "Component inventory for electronics and workshop projects."
    icon = "\U0001F529"  # nut and bolt

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list: Optional[QListWidget] = None
        self._filter_edit: Optional[QLineEdit] = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter by name, category, value, package, or location…")
        self._filter_edit.textChanged.connect(lambda _text: self._refresh_list())
        layout.addWidget(self._filter_edit)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Component")
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

    def _refresh_list(self) -> None:
        query = self._filter_edit.text().strip()
        components = (
            self.context.components.search(query) if query else self.context.components.all_components()
        )

        self._list.clear()
        for component in components:
            item = QListWidgetItem(format_component_row(component))
            item.setData(Qt.ItemDataRole.UserRole, component.component_id)
            self._list.addItem(item)

    def _selected_component_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        dialog = AddEditComponentDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.components.add_component(
            name=dialog.entered_name,
            category=dialog.entered_category,
            value=dialog.entered_value,
            package=dialog.entered_package,
            quantity=dialog.entered_quantity,
            location=dialog.entered_location,
            notes=dialog.entered_notes,
        )
        self._refresh_list()

    def _on_edit(self) -> None:
        component_id = self._selected_component_id()
        if component_id is None:
            QMessageBox.information(None, "No Component Selected", "Select a component to edit.")
            return

        component = self.context.components.get_component(component_id)
        dialog = AddEditComponentDialog(component=component)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.components.update_component(
            component_id,
            name=dialog.entered_name,
            category=dialog.entered_category,
            value=dialog.entered_value,
            package=dialog.entered_package,
            quantity=dialog.entered_quantity,
            location=dialog.entered_location,
            notes=dialog.entered_notes,
        )
        self._refresh_list()

    def _on_delete(self) -> None:
        component_id = self._selected_component_id()
        if component_id is None:
            QMessageBox.information(None, "No Component Selected", "Select a component to delete.")
            return

        component = self.context.components.get_component(component_id)
        confirm = QMessageBox.question(
            None,
            "Delete Component",
            f"Delete '{component.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.components.delete_component(component_id)
        self._refresh_list()
