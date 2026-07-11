"""
modules.toolbox.calculators.unit_converter
=============================================

Unit Converter — the first CalculatorPlugin (core/calculator_engine.py),
proving the "convert value from A to B" shape of calculator.

convert() and the unit tables are free functions/module-level data
(not methods), so they're unit-testable without a Qt event loop — see
tests/test_unit_converter.py. UnitConverterCalculator.build_widget()
is the Qt-facing wrapper around them.

Each unit maps to a (to_base, from_base) function pair, where "base"
is that category's reference unit (meters for length, kilograms for
weight, Celsius for temperature). Converting A -> B goes through the
base unit: to_base(value_in_A), then from_base(that) for B. This
handles both pure-ratio units (length, weight) and offset units
(temperature) with the same conversion logic.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from core.calculator_engine import CalculatorPlugin


def _linear(factor: float):
    return (lambda v: v * factor, lambda v: v / factor)


LENGTH_UNITS = {
    "Meters (m)": _linear(1.0),
    "Feet (ft)": _linear(0.3048),
    "Yards (yd)": _linear(0.9144),
    "Inches (in)": _linear(0.0254),
    "Kilometers (km)": _linear(1000.0),
    "Miles (mi)": _linear(1609.344),
}

WEIGHT_UNITS = {
    "Kilograms (kg)": _linear(1.0),
    "Pounds (lb)": _linear(0.45359237),
    "Grams (g)": _linear(0.001),
    "Ounces (oz)": _linear(0.028349523125),
}

# US customary volume/cooking measurements. Base unit is liters. All
# factors derive from the exact US gallon <-> liter conversion (1 gal
# = 3.785411784 L, NIST Handbook 44) down through the standard US
# liquid-volume hierarchy (1 gal = 4 qt = 8 pt = 16 cup = 128 fl oz =
# 256 tbsp = 768 tsp), so every unit here stays exactly consistent
# with every other, not just with liters.
VOLUME_UNITS = {
    "Liters (L)": _linear(1.0),
    "Milliliters (mL)": _linear(0.001),
    "US Gallons (gal)": _linear(3.785411784),
    "US Quarts (qt)": _linear(0.946352946),
    "US Pints (pt)": _linear(0.473176473),
    "US Cups (cup)": _linear(0.2365882365),
    "US Fluid Ounces (fl oz)": _linear(0.0295735295625),
    "US Tablespoons (tbsp)": _linear(0.01478676478125),
    "US Teaspoons (tsp)": _linear(0.00492892159375),
}

TEMPERATURE_UNITS = {
    "Celsius (°C)": (lambda c: c, lambda c: c),
    "Fahrenheit (°F)": (lambda f: (f - 32) * 5 / 9, lambda c: c * 9 / 5 + 32),
    "Kelvin (K)": (lambda k: k - 273.15, lambda c: c + 273.15),
}

UNIT_CATEGORIES = {
    "Length": LENGTH_UNITS,
    "Volume": VOLUME_UNITS,
    "Weight": WEIGHT_UNITS,
    "Temperature": TEMPERATURE_UNITS,
}


def convert(category: str, from_unit: str, to_unit: str, value: float) -> float:
    """Convert `value` in `from_unit` to `to_unit`, both within `category`."""
    units = UNIT_CATEGORIES[category]
    to_base, _ = units[from_unit]
    _, from_base = units[to_unit]
    return from_base(to_base(value))


class UnitConverterCalculator(CalculatorPlugin):
    calculator_id = "unit_converter"
    display_name = "Unit Converter"
    category = "General"
    description = "Convert between common length, weight, and temperature units."

    def build_widget(self) -> QWidget:
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
