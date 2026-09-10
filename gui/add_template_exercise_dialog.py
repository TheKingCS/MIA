"""
gui.add_template_exercise_dialog
===================================

Small dialog for adding one exercise (with a target sets/reps/weight)
to a workout template — opened from the template's own detail area in
modules/workout/module.py, one exercise at a time (the real
gui/pick_item_quantity_dialog.py precedent — see that dialog's own
docstring — not an embedded multi-row table editor). Picks from the
existing exercise library (context.workout.all_exercises()); the
caller is responsible for checking that list isn't empty first, same
"caller already validated there's something to pick from" convention
gui/pick_item_quantity_dialog.py's own docstring states.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class AddTemplateExerciseDialog(QDialog):
    def __init__(self, parent=None, exercises=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Exercise to Template")
        self.setFixedSize(340, 340)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Exercise:"))
        self.exercise_combo = QComboBox()
        for exercise in exercises or []:
            self.exercise_combo.addItem(exercise.name, exercise.exercise_id)
        layout.addWidget(self.exercise_combo)

        layout.addWidget(QLabel("Target Sets:"))
        self.target_sets_spin = QSpinBox()
        self.target_sets_spin.setRange(1, 20)
        self.target_sets_spin.setValue(3)
        layout.addWidget(self.target_sets_spin)

        layout.addWidget(QLabel("Target Reps:"))
        self.target_reps_spin = QSpinBox()
        self.target_reps_spin.setRange(1, 100)
        self.target_reps_spin.setValue(10)
        layout.addWidget(self.target_reps_spin)

        layout.addWidget(QLabel("Target Weight:"))
        self.target_weight_spin = QDoubleSpinBox()
        self.target_weight_spin.setRange(0.0, 2000.0)
        self.target_weight_spin.setDecimals(1)
        layout.addWidget(self.target_weight_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._exercise_id: str = ""
        self._target_sets: int = 3
        self._target_reps: int = 10
        self._target_weight: float = 0.0

    def _on_accept(self) -> None:
        self._exercise_id = self.exercise_combo.currentData()
        self._target_sets = self.target_sets_spin.value()
        self._target_reps = self.target_reps_spin.value()
        self._target_weight = self.target_weight_spin.value()
        self.accept()

    @property
    def entered_exercise_id(self) -> str:
        return self._exercise_id

    @property
    def entered_target_sets(self) -> int:
        return self._target_sets

    @property
    def entered_target_reps(self) -> int:
        return self._target_reps

    @property
    def entered_target_weight(self) -> float:
        return self._target_weight
