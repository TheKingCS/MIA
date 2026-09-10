"""
gui.add_edit_workout_template_dialog
=======================================

Small dialog for creating or editing a workout template's own name/
notes, used by modules/workout/module.py. Deliberately does NOT edit
which exercises belong to the template — those are added/removed one
at a time from the template's own detail area via
gui/add_template_exercise_dialog.py, same real "outer list + single-
item dialog, immediate commit" precedent gui/add_edit_recipe_dialog.py
(and, before it, gui/add_edit_job_dialog.py) already establishes for
the same shape of relationship.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.workout_manager import WorkoutTemplate


class AddEditWorkoutTemplateDialog(QDialog):
    def __init__(self, parent=None, template: Optional[WorkoutTemplate] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Template" if template is not None else "New Workout Template")
        self.setFixedSize(340, 260)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Push Day, Leg Day")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(90)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(template)

        self._name: str = ""
        self._notes: str = ""

    def _prefill(self, template: Optional[WorkoutTemplate]) -> None:
        if template is None:
            return
        self.name_edit.setText(template.name)
        self.notes_edit.setPlainText(template.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_notes(self) -> str:
        return self._notes
