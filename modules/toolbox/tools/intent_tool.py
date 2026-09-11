"""
modules.toolbox.tools.intent_tool
====================================

Intent Manager — a ToolboxTool (modules/toolbox/tool_base.py), the
connective-infrastructure pass that followed the "My Hero's Path"
architecture review (see docs/ROADMAP.md's dated entry). Single-panel
CRUD, same shape as the Project half of
modules/toolbox/tools/project_tool.py — Intent has no children of its
own the way a Project has Tasks, so there's no second list panel here.

format_intent_row() is a free function (not a method) — testable
without Qt, see tests/test_intent_tool.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.intent_manager import Intent
from gui.add_edit_intent_dialog import AddEditIntentDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from modules.toolbox.tool_base import ToolboxTool


def format_intent_row(intent: Intent) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_intent_tool.py)."""
    focus = "  ★ Current Focus" if intent.primary else ""
    return f"{intent.name}  ({intent.status}){focus}"


class IntentTool(ToolboxTool):
    tool_id = "intents"
    display_name = "Intent Manager"
    description = "Track long-term goals your projects serve."
    icon = "\U0001F9ED"  # compass

    def __init__(self, context) -> None:
        super().__init__(context)
        self._intent_list: Optional[QListWidget] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Intents")
        title.setObjectName("SubtitleLabel")
        layout.addWidget(title)

        self._intent_list = QListWidget()
        layout.addWidget(self._intent_list, stretch=1)

        buttons = QHBoxLayout()
        add_button = QPushButton("Add Intent")
        add_button.clicked.connect(self._on_add_intent)
        buttons.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_intent)
        buttons.addWidget(edit_button)

        focus_button = QPushButton("Make Current Focus")
        focus_button.clicked.connect(self._on_make_primary)
        buttons.addWidget(focus_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_intent)
        buttons.addWidget(delete_button)
        layout.addLayout(buttons)

        self._refresh_intent_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_intent_list(self) -> None:
        previously_selected = self._selected_intent_id()

        self._intent_list.clear()
        for intent in self.context.intents.all_intents():
            item = QListWidgetItem(format_intent_row(intent))
            item.setData(Qt.ItemDataRole.UserRole, intent.intent_id)
            self._intent_list.addItem(item)

        if previously_selected is not None:
            for row in range(self._intent_list.count()):
                item = self._intent_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == previously_selected:
                    self._intent_list.setCurrentItem(item)
                    break

    def _selected_intent_id(self) -> Optional[str]:
        item = self._intent_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add_intent(self) -> None:
        dialog = AddEditIntentDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        added = self.context.intents.add_intent(
            name=dialog.entered_name,
            status=dialog.entered_status,
            description=dialog.entered_description,
        )
        if dialog.entered_primary:
            self.context.intents.set_primary(added.intent_id)
        self._refresh_intent_list()

    def _on_edit_intent(self) -> None:
        intent_id = self._selected_intent_id()
        if intent_id is None:
            QMessageBox.information(None, "No Intent Selected", "Select an intent to edit.")
            return

        intent = self.context.intents.get_intent(intent_id)
        dialog = AddEditIntentDialog(intent=intent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.intents.update_intent(
            intent_id,
            name=dialog.entered_name,
            status=dialog.entered_status,
            description=dialog.entered_description,
        )
        if dialog.entered_primary:
            self.context.intents.set_primary(intent_id)
        self._refresh_intent_list()

    def _on_make_primary(self) -> None:
        intent_id = self._selected_intent_id()
        if intent_id is None:
            QMessageBox.information(None, "No Intent Selected", "Select an intent to make your current focus.")
            return

        self.context.intents.set_primary(intent_id)
        self._refresh_intent_list()

    def _on_delete_intent(self) -> None:
        intent_id = self._selected_intent_id()
        if intent_id is None:
            QMessageBox.information(None, "No Intent Selected", "Select an intent to delete.")
            return

        intent = self.context.intents.get_intent(intent_id)
        dialog = DeleteConfirmDialog(intent.name, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.intents.delete_intent(intent_id)
        self._refresh_intent_list()
