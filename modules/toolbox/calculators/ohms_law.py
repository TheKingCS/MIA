"""
modules.toolbox.calculators.ohms_law
=======================================

Ohm's Law — the second CalculatorPlugin (core/calculator_engine.py),
proving the "solve for any one of several related values" shape of
calculator (as opposed to unit_converter.py's "convert A to B" shape).

solve() is a free function (not a method), unit-testable without a Qt
event loop — see tests/test_ohms_law.py. OhmsLawCalculator.build_widget()
is the Qt-facing wrapper around it.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.calculator_engine import CalculatorPlugin

_SOLVE_LABELS = {
    "voltage": "Voltage (V)",
    "current": "Current (A)",
    "resistance": "Resistance (Ω)",
}
_SOLVE_UNITS = {"voltage": "V", "current": "A", "resistance": "Ω"}


def solve(solve_for: str, voltage: float | None, current: float | None, resistance: float | None) -> float:
    """
    Solve V = I × R for whichever of the three `solve_for` names —
    the other two arguments must be provided (non-None).
    """
    if solve_for == "voltage":
        return current * resistance
    if solve_for == "current":
        return voltage / resistance
    if solve_for == "resistance":
        return voltage / current
    raise ValueError(f"Unknown solve_for: {solve_for!r}")


class OhmsLawCalculator(CalculatorPlugin):
    calculator_id = "ohms_law"
    display_name = "Ohm's Law"
    category = "Electronics"
    description = "Solve for voltage, current, or resistance given the other two (V = I × R)."

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(self.display_name)
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()

        self._solve_combo = QComboBox()
        self._solve_combo.addItems(list(_SOLVE_LABELS.values()))
        form.addRow("Solve for:", self._solve_combo)

        self._voltage_edit = QLineEdit()
        self._voltage_edit.setPlaceholderText("Volts")
        form.addRow("Voltage (V):", self._voltage_edit)

        self._current_edit = QLineEdit()
        self._current_edit.setPlaceholderText("Amps")
        form.addRow("Current (A):", self._current_edit)

        self._resistance_edit = QLineEdit()
        self._resistance_edit.setPlaceholderText("Ohms")
        form.addRow("Resistance (Ω):", self._resistance_edit)

        layout.addLayout(form)

        self._result_label = QLabel("Result: —")
        self._result_label.setObjectName("ReadoutLabel")
        layout.addWidget(self._result_label)

        calculate_button = QPushButton("Calculate")
        calculate_button.setObjectName("ModuleButton")
        calculate_button.clicked.connect(self._recompute)
        layout.addWidget(calculate_button)

        layout.addStretch()

        self._field_by_key = {
            "voltage": self._voltage_edit,
            "current": self._current_edit,
            "resistance": self._resistance_edit,
        }
        self._key_by_label = {label: key for key, label in _SOLVE_LABELS.items()}

        self._solve_combo.currentTextChanged.connect(self._on_solve_target_changed)
        self._on_solve_target_changed(self._solve_combo.currentText())
        return widget

    def _on_solve_target_changed(self, label: str) -> None:
        target_key = self._key_by_label[label]
        target_field = self._field_by_key[target_key]
        for key, edit in self._field_by_key.items():
            edit.setEnabled(key != target_key)
        target_field.clear()
        self._result_label.setText("Result: —")

    def _recompute(self) -> None:
        solve_for = self._key_by_label[self._solve_combo.currentText()]

        try:
            values = {}
            for key, edit in self._field_by_key.items():
                values[key] = None if key == solve_for else float(edit.text())
            result = solve(solve_for, values["voltage"], values["current"], values["resistance"])
        except (ValueError, ZeroDivisionError):
            self._result_label.setText("Result: enter valid numbers in the other two fields.")
            return

        self._field_by_key[solve_for].setText(f"{result:.4g}")
        self._result_label.setText(f"Result: {result:.4g} {_SOLVE_UNITS[solve_for]}")
