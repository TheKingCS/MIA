"""
gui.add_edit_task_dialog
===========================

Small dialog for creating or editing a single Task (one to-do item
under a Project in modules/toolbox/tools/project_tool.py) —
title/done/due_date/notes. `project_id` is not editable here: a Task's
parent Project is fixed by whichever one is selected in the tool when
"Add Task"/"Edit Task" is invoked, not a field a user picks inside this
dialog (same rationale as gui/add_edit_trip_dialog.py's expedition_id).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.task_manager import Task

_ISO_DATE_FORMAT = "yyyy-MM-dd"


class AddEditTaskDialog(QDialog):
    def __init__(self, parent=None, task: Optional[Task] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Task" if task is not None else "New Task")
        self.setFixedSize(360, 460)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title")
        layout.addWidget(self.title_edit)

        self.done_check = QCheckBox("Done")
        layout.addWidget(self.done_check)

        layout.addWidget(QLabel("Due Date:"))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat(_ISO_DATE_FORMAT)
        layout.addWidget(self.due_date_edit)

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

        self._prefill(task)

        self._title: str = ""
        self._done: bool = False
        self._due_date: str = ""
        self._notes: str = ""

    def _prefill(self, task: Optional[Task]) -> None:
        if task is not None:
            self.title_edit.setText(task.title)
            self.done_check.setChecked(task.done)
            if task.due_date:
                self.due_date_edit.setDate(QDate.fromString(task.due_date, _ISO_DATE_FORMAT))
            else:
                self.due_date_edit.setDate(QDate.currentDate())
            self.notes_edit.setPlainText(task.notes)
        else:
            self.due_date_edit.setDate(QDate.currentDate())

    def _on_accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setPlaceholderText("Title can't be empty!")
            return

        self._title = title
        self._done = self.done_check.isChecked()
        self._due_date = self.due_date_edit.date().toString(_ISO_DATE_FORMAT)
        self._notes = self.notes_edit.toPlainText()
        self.accept()

    @property
    def entered_title(self) -> str:
        return self._title

    @property
    def entered_done(self) -> bool:
        return self._done

    @property
    def entered_due_date(self) -> str:
        return self._due_date

    @property
    def entered_notes(self) -> str:
        return self._notes
