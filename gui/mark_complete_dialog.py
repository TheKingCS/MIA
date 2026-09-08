"""
gui.mark_complete_dialog
===========================

Small dialog used only when marking a meter-type maintenance task
(Runtime/Mileage/Cycles/Condition) complete — it asks for the meter
value at the moment of completion, which becomes the new
last_completed_meter_value baseline that future "used since last
service" calculations measure from. Prefilled with the latest logged
reading when one exists, but always editable — completing the actual
service and logging its odometer/hour reading don't always happen in
the same breath.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QVBoxLayout,
)


class MarkCompleteDialog(QDialog):
    def __init__(self, parent=None, unit: str = "", default_value: Optional[float] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mark Complete")
        self.setFixedSize(320, 160)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Meter value at completion{f' ({unit})' if unit else ''}:"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0.0, 10_000_000.0)
        self.value_spin.setDecimals(1)
        if default_value is not None:
            self.value_spin.setValue(default_value)
        layout.addWidget(self.value_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._value: float = default_value or 0.0

    def _on_accept(self) -> None:
        self._value = self.value_spin.value()
        self.accept()

    @property
    def entered_value(self) -> float:
        return self._value
