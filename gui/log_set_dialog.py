"""
gui.log_set_dialog
=====================

Small dialog for logging one completed set (reps + weight) during a
live workout session, used by modules/workout/module.py's Log Session
tab. Opened once per set — the session itself accumulates logged sets
in memory (see core/workout_manager.py's own module docstring) and is
only ever saved as a whole WorkoutSession record on Finish.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class LogSetDialog(QDialog):
    def __init__(self, parent=None, exercise_name: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Log Set — {exercise_name}" if exercise_name else "Log Set")
        self.setFixedSize(320, 240)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Reps:"))
        self.reps_spin = QSpinBox()
        self.reps_spin.setRange(1, 200)
        self.reps_spin.setValue(10)
        layout.addWidget(self.reps_spin)

        layout.addWidget(QLabel("Weight:"))
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 2000.0)
        self.weight_spin.setDecimals(1)
        layout.addWidget(self.weight_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._reps: int = 10
        self._weight: float = 0.0

    def _on_accept(self) -> None:
        self._reps = self.reps_spin.value()
        self._weight = self.weight_spin.value()
        self.accept()

    @property
    def entered_reps(self) -> int:
        return self._reps

    @property
    def entered_weight(self) -> float:
        return self._weight
