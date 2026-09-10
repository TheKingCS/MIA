"""
gui.add_edit_exercise_dialog
===============================

Small dialog for creating or editing a single exercise-library entry,
used by modules/workout/module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.workout_manager import EXERCISE_CATEGORIES, Exercise


class AddEditExerciseDialog(QDialog):
    def __init__(self, parent=None, exercise: Optional[Exercise] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Exercise" if exercise is not None else "New Exercise")
        self.setFixedSize(340, 380)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Barbell Squat")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(EXERCISE_CATEGORIES)
        layout.addWidget(self.category_combo)

        layout.addWidget(QLabel("Equipment:"))
        self.equipment_edit = QLineEdit()
        self.equipment_edit.setPlaceholderText("e.g. Barbell, Dumbbell, Bodyweight (optional)")
        layout.addWidget(self.equipment_edit)

        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Form cues, etc. (optional)")
        self.notes_edit.setFixedHeight(90)
        layout.addWidget(self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prefill(exercise)

        self._name: str = ""
        self._category: str = EXERCISE_CATEGORIES[0]
        self._equipment: str = ""
        self._notes: str = ""

    def _prefill(self, exercise: Optional[Exercise]) -> None:
        if exercise is None:
            return
        self.name_edit.setText(exercise.name)
        if exercise.category in EXERCISE_CATEGORIES:
            self.category_combo.setCurrentText(exercise.category)
        self.equipment_edit.setText(exercise.equipment)
        self.notes_edit.setPlainText(exercise.notes)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return

        self._name = name
        self._category = self.category_combo.currentText()
        self._equipment = self.equipment_edit.text().strip()
        self._notes = self.notes_edit.toPlainText().strip()
        self.accept()

    @property
    def entered_name(self) -> str:
        return self._name

    @property
    def entered_category(self) -> str:
        return self._category

    @property
    def entered_equipment(self) -> str:
        return self._equipment

    @property
    def entered_notes(self) -> str:
        return self._notes
