"""
modules.toolbox.calculators.unit_converter
=============================================

Unit Converter — the first CalculatorPlugin (core/calculator_engine.py),
proving the "convert value from A to B" shape of calculator.

convert() and the unit tables live in core/unit_conversion.py (pure,
no Qt, shared with the web Toolbox and the convert_units voice tool) and
are re-exported here — see tests/test_unit_converter.py. UnitConverterCalculator.build_widget()
is the Qt-facing wrapper around them.

Each unit maps to a (to_base, from_base) function pair, where "base"
is that category's reference unit (meters for length, kilograms for
weight, Celsius for temperature, ...). Converting A -> B goes through
the base unit: to_base(value_in_A), then from_base(that) for B. This
handles pure-ratio units (length, weight, ...) and offset units
(temperature) the same way — and since the pair is just two functions,
not necessarily a linear factor, it also covers a genuinely
non-linear/reciprocal relationship (Fuel Economy's mpg vs L/100km)
with no special-casing anywhere else in this file.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from core.calculator_engine import CalculatorPlugin
from core.unit_conversion import (  # noqa: F401  (re-exported: the tables and math live in core)
    ANGLE_UNITS, AREA_UNITS, DATA_STORAGE_UNITS, ENERGY_UNITS, FUEL_ECONOMY_UNITS, LENGTH_UNITS, POWER_UNITS,
    PRESSURE_UNITS, SPEED_UNITS, TEMPERATURE_UNITS, TIME_UNITS, UNIT_CATEGORIES, VOLUME_UNITS, WEIGHT_UNITS, convert,
    resolve_unit_key,
)


class UnitConverterCalculator(CalculatorPlugin):
    """The unit converter: a category (length, temperature, fuel economy...), from and to units, and the answer as you type."""
    calculator_id = "unit_converter"
    display_name = "Unit Converter"
    category = "General"
    description = (
        "Convert between length, area, volume, weight, temperature, "
        "speed, pressure, energy, power, time, data storage, angle, "
        "and fuel economy units."
    )

    def build_widget(self) -> QWidget:
        """The screen: category, value, from and to units, and the result."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(self.display_name)
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        form = QFormLayout()

        self._category_combo = QComboBox()
        self._category_combo.addItems(list(UNIT_CATEGORIES.keys()))
        form.addRow("Category:", self._category_combo)

        self._from_combo = QComboBox()
        form.addRow("From:", self._from_combo)

        self._to_combo = QComboBox()
        form.addRow("To:", self._to_combo)

        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("Enter a value")
        form.addRow("Value:", self._value_edit)

        layout.addLayout(form)

        self._result_label = QLabel("Result: —")
        self._result_label.setObjectName("ReadoutLabel")
        layout.addWidget(self._result_label)

        layout.addStretch()

        self._category_combo.currentTextChanged.connect(self._on_category_changed)
        self._from_combo.currentTextChanged.connect(self._recompute)
        self._to_combo.currentTextChanged.connect(self._recompute)
        self._value_edit.textChanged.connect(self._recompute)

        self._on_category_changed(self._category_combo.currentText())
        return widget

    def _on_category_changed(self, category: str) -> None:
        """Fills both unit lists with the category's units (two different ones picked to start), without converting halfway, then converts."""
        units = list(UNIT_CATEGORIES[category].keys())
        self._from_combo.blockSignals(True)
        self._to_combo.blockSignals(True)
        self._from_combo.clear()
        self._to_combo.clear()
        self._from_combo.addItems(units)
        self._to_combo.addItems(units)
        if len(units) > 1:
            self._to_combo.setCurrentIndex(1)
        self._from_combo.blockSignals(False)
        self._to_combo.blockSignals(False)
        self._recompute()

    def _recompute(self) -> None:
        """Converts the value through the category's base unit and shows it, or asks for a number."""
        from_unit = self._from_combo.currentText()
        to_unit = self._to_combo.currentText()
        if not from_unit or not to_unit:
            return

        try:
            value = float(self._value_edit.text())
        except ValueError:
            self._result_label.setText("Result: —")
            return

        result = convert(self._category_combo.currentText(), from_unit, to_unit, value)
        self._result_label.setText(f"Result: {result:.4g} {to_unit}")
