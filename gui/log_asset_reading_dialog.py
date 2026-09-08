"""
gui.log_asset_reading_dialog
===============================

Small dialog for logging a general per-asset usage stat — fuel
consumption, odometer, engine hours, whatever the user wants to track
— independent of any specific maintenance task's due-date calculation.
Used by modules/maintenance/module.py's Assets tab "Log Usage…" action,
backed by core.maintenance_manager.MaintenanceManager.log_asset_reading()
(itself a thin wrapper around the shared DataLoggerManager, same as
gui/log_reading_dialog.py's task-scoped version — this one just isn't
tied to a task_id, since "how much fuel does the mower use" is a
question worth answering even when no task currently tracks it).

Meter name is free text (e.g. "Fuel", "Odometer") rather than a fixed
list — asset_meter_names() derives the known set from whatever's
actually been logged, so a combo box here is pre-populated with those
past names for convenience but never restricts to them.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class LogAssetReadingDialog(QDialog):
    def __init__(self, parent=None, known_meter_names: Optional[list[str]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Log Usage")
        self.setFixedSize(320, 260)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Meter (e.g. Fuel, Odometer, Engine Hours):"))
        self.meter_name_combo = QComboBox()
        self.meter_name_combo.setEditable(True)
        self.meter_name_combo.addItems(known_meter_names or [])
        self.meter_name_combo.setCurrentText("")
        layout.addWidget(self.meter_name_combo)

        layout.addWidget(QLabel("Value:"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0.0, 10_000_000.0)
        self.value_spin.setDecimals(2)
        layout.addWidget(self.value_spin)

        layout.addWidget(QLabel("Unit (optional):"))
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("e.g. gal, mi, hrs")
        layout.addWidget(self.unit_edit)

        layout.addWidget(QLabel("Note (optional):"))
        self.note_edit = QLineEdit()
        layout.addWidget(self.note_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._meter_name: str = ""
        self._value: float = 0.0
        self._unit: str = ""
        self._note: str = ""

    def _on_accept(self) -> None:
        meter_name = self.meter_name_combo.currentText().strip()
        if not meter_name:
            return
        self._meter_name = meter_name
        self._value = self.value_spin.value()
        self._unit = self.unit_edit.text().strip()
        self._note = self.note_edit.text().strip()
        self.accept()

    @property
    def entered_meter_name(self) -> str:
        return self._meter_name

    @property
    def entered_value(self) -> float:
        return self._value

    @property
    def entered_unit(self) -> str:
        return self._unit

    @property
    def entered_note(self) -> str:
        return self._note
