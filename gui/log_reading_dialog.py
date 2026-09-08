"""
gui.log_reading_dialog
=========================

Small dialog for manually logging one meter/sensor reading (odometer,
engine hours, start count, battery voltage, ...) against a Runtime/
Mileage/Cycles/Condition/Sensor maintenance task — used by
modules/maintenance/module.py's "Log Reading…" action. This is the
honest v2 stand-in for real hardware telemetry: it writes through
core.maintenance_manager.MaintenanceManager.log_reading(), which itself
is a thin wrapper around the shared core.data_logger_manager
.DataLoggerManager.add_reading() — a future real sensor/OBD integration
is just another caller of that same method, not a different dialog.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class LogReadingDialog(QDialog):
    def __init__(self, parent=None, unit: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Log Reading")
        self.setFixedSize(320, 200)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Current value{f' ({unit})' if unit else ''}:"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0.0, 10_000_000.0)
        self.value_spin.setDecimals(1)
        layout.addWidget(self.value_spin)

        layout.addWidget(QLabel("Note (optional):"))
        self.note_edit = QLineEdit()
        layout.addWidget(self.note_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._value: float = 0.0
        self._note: str = ""

    def _on_accept(self) -> None:
        self._value = self.value_spin.value()
        self._note = self.note_edit.text().strip()
        self.accept()

    @property
    def entered_value(self) -> float:
        return self._value

    @property
    def entered_note(self) -> str:
        return self._note
