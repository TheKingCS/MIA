"""
gui.manage_business_entities_dialog
======================================

A single self-contained dialog for managing core.budget_manager's
BusinessEntity list (LLCs/sole props/etc.) — only ~3-5 entities are
expected, so this is one QDialog rather than a new module/tab, same
scale reasoning as gui/delete_confirm_dialog.py's own minimalism.

Add/Edit opens a small nested AddEditBusinessEntityDialog (Name/Type/
Notes). Every action (add/edit/delete) commits immediately via
BudgetManager's own CRUD — no staged batch — matching every other
list-management flow in this app (the Bills tab, the Income Sources
tab).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.budget_manager import BUSINESS_ENTITY_TYPES, BusinessEntity


class AddEditBusinessEntityDialog(QDialog):
    def __init__(self, parent=None, entity: Optional[BusinessEntity] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Entity" if entity is not None else "New Entity")
        self.setFixedSize(340, 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Sunrise Rentals LLC")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(BUSINESS_ENTITY_TYPES)
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(70)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(entity)

        self._name: str = ""
        self._entity_type: str = BUSINESS_ENTITY_TYPES[0]
        self._notes: str = ""

    def _prefill(self, entity: Optional[BusinessEntity]) -> None:
        if entity is not None:
            self.name_edit.setText(entity.name)
            if entity.entity_type in BUSINESS_ENTITY_TYPES:
                self.type_combo.setCurrentText(entity.entity_type)
            self.notes_edit.setPlainText(entity.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._entity_type = self.type_combo.currentText()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_entity_type(self) -> str:
        return self._entity_type

    @property
    def entered_notes(self) -> str:
        return self._notes


class ManageBusinessEntitiesDialog(QDialog):
    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Manage Entities")
        self.setFixedSize(400, 420)

        layout = QVBoxLayout(self)

        intro = QLabel("Business entities (LLCs, sole proprietorships, etc.) you can tag properties and Budget entries with.")
        intro.setWordWrap(True)
        intro.setObjectName("SubtitleLabel")
        layout.addWidget(intro)

        self._entity_list = QListWidget()
        layout.addWidget(self._entity_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._on_add)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._on_edit)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._on_delete)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)
        close_buttons.accepted.connect(self.accept)
        close_buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(close_buttons)

        self._refresh()

    def _refresh(self) -> None:
        self._entity_list.clear()
        for entity in self.context.budget.all_business_entities():
            item = QListWidgetItem(f"{entity.name}  [{entity.entity_type}]")
            item.setData(Qt.ItemDataRole.UserRole, entity.entity_id)
            self._entity_list.addItem(item)

    def _selected_entity_id(self) -> Optional[str]:
        item = self._entity_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add(self) -> None:
        dialog = AddEditBusinessEntityDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.budget.add_business_entity(
            name=dialog.entered_name, entity_type=dialog.entered_entity_type, notes=dialog.entered_notes,
        )
        self._refresh()

    def _on_edit(self) -> None:
        entity_id = self._selected_entity_id()
        if entity_id is None:
            QMessageBox.information(None, "No Entity Selected", "Select an entity to edit.")
            return

        entity = self.context.budget.get_business_entity(entity_id)
        dialog = AddEditBusinessEntityDialog(entity=entity)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.budget.update_business_entity(
            entity_id, name=dialog.entered_name, entity_type=dialog.entered_entity_type, notes=dialog.entered_notes,
        )
        self._refresh()

    def _on_delete(self) -> None:
        entity_id = self._selected_entity_id()
        if entity_id is None:
            QMessageBox.information(None, "No Entity Selected", "Select an entity to delete.")
            return

        entity = self.context.budget.get_business_entity(entity_id)
        confirm = QMessageBox.question(
            None,
            "Delete Entity",
            f"Delete '{entity.name}'? Properties and Budget entries already tagged with it will keep their tag, "
            "but it will show as unassigned until you retag them.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.budget.delete_business_entity(entity_id)
        self._refresh()
