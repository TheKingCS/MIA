"""
gui.add_edit_classroom_course_dialog
========================================

Small dialog for creating or editing a Course within a Subject
(modules/classroom/module.py) — name and a description. `subject_id`
is fixed at creation (the dialog is always opened from inside one
Subject's own drill-down page) — same "picked by context, not by a
combo" reasoning as gui/add_edit_mission_dialog.py's trip/project
pickers being creation-only.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QTextEdit, QVBoxLayout

from core.classroom_manager import Course


class AddEditCourseDialog(QDialog):
    def __init__(self, context, parent=None, course: Optional[Course] = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Edit Course" if course is not None else "New Course")
        self.setFixedSize(360, 320)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. 'Introduction to DC Circuits'")
        layout.addWidget(self.name_edit)

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

        self._prefill(course)

        self._name: str = ""
        self._description: str = ""

    def _prefill(self, course: Optional[Course]) -> None:
        if course is None:
            return
        self.name_edit.setText(course.name)
        self.description_edit.setPlainText(course.description)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._description = self.description_edit.toPlainText()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_description(self) -> str:
        return self._description
