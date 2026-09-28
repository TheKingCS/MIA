"""
gui.add_edit_project_dialog
==============================

Small dialog for creating or editing a single Project (the top-level
container in modules/toolbox/tools/project_tool.py) — same shape as
gui/add_edit_expedition_dialog.py: name/status/due_date/description,
with `status` as a QComboBox over core.project_manager.PROJECT_STATUSES
(same fixed-vocabulary pattern as gui/add_edit_trip_dialog.py's
activity_type field).

Connective-infrastructure pass (2026-09-11): takes `context` now (it
didn't before) so it can offer an optional Intent picker, same
"(None)" + real-list-of-records shape as
gui/add_edit_mission_dialog.py's own trip_combo.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.project_manager import PROJECT_STATUSES, Project

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditProjectDialog(QDialog):
    def __init__(self, context, parent=None, project: Optional[Project] = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Edit Project" if project is not None else "New Project")
        self.setFixedSize(360, 580)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        for status in PROJECT_STATUSES:
            self.status_combo.addItem(status, status)
        layout.addWidget(self.status_combo)

        layout.addWidget(QLabel("Intent (optional):"))
        self.intent_combo = QComboBox()
        self.intent_combo.addItem("(None)", None)
        if self.context is not None and self.context.intents is not None:
            for intent in self.context.intents.all_intents():
                self.intent_combo.addItem(intent.name, intent.intent_id)
        layout.addWidget(self.intent_combo)

        layout.addWidget(QLabel("Due Date:"))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.due_date_edit)

        # Finance #2: planned spend for a build (0 = no budget).
        layout.addWidget(QLabel("Budget ($, optional):"))
        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(0, 10_000_000)
        self.budget_spin.setDecimals(2)
        self.budget_spin.setSpecialValueText("No budget")
        layout.addWidget(self.budget_spin)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Description (optional)")
        layout.addWidget(self.description_edit, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(project)

        self._name: str = ""
        self._status: str = ""
        self._due_date: str = ""
        self._description: str = ""
        self._intent_id: Optional[str] = None
        self._budget: float = 0.0

    def _prefill(self, project: Optional[Project]) -> None:
        if project is not None:
            self.name_edit.setText(project.name)
            index = self.status_combo.findData(project.status)
            self.status_combo.setCurrentIndex(index if index != -1 else 0)
            intent_index = self.intent_combo.findData(project.intent_id)
            self.intent_combo.setCurrentIndex(intent_index if intent_index != -1 else 0)
            if project.due_date:
                self.due_date_edit.setDate(QDate.fromString(project.due_date, _ISO_DATE_FORMAT))
            else:
                self.due_date_edit.setDate(QDate.currentDate())
            self.description_edit.setPlainText(project.description)
            self.budget_spin.setValue(project.budget)
        else:
            self.due_date_edit.setDate(QDate.currentDate())

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._status = self.status_combo.currentData()
        self._intent_id = self.intent_combo.currentData()
        self._due_date = self.due_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._description = self.description_edit.toPlainText()
        self._budget = self.budget_spin.value()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_status(self) -> str:
        return self._status

    @property
    def entered_intent_id(self) -> Optional[str]:
        return self._intent_id

    @property
    def entered_due_date(self) -> str:
        return self._due_date

    @property
    def entered_description(self) -> str:
        return self._description

    @property
    def entered_budget(self) -> float:
        return self._budget
