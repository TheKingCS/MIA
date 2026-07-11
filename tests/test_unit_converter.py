"""
tests.test_unit_converter
============================

Unit tests for modules.toolbox.calculators.unit_converter.convert().
"""

from __future__ import annotations

import pytest

from modules.toolbox.calculators.unit_converter import convert


def test_meters_to_feet():
    assert convert("Length", "Meters (m)", "Feet (ft)", 1.0) == pytest.approx(3.28084, rel=1e-4)


def test_same_unit_is_identity():
    assert convert("Length", "Meters (m)", "Meters (m)", 42.0) == pytest.approx(42.0)


def test_kilometers_to_miles():
    assert convert("Length", "Kilometers (km)", "Miles (mi)", 1.0) == pytest.approx(0.621371, rel=1e-4)


def test_yards_to_feet():
    assert convert("Length", "Yards (yd)", "Feet (ft)", 1.0) == pytest.approx(3.0)


def test_yards_to_meters():
    assert convert("Length", "Yards (yd)", "Meters (m)", 1.0) == pytest.approx(0.9144)


def test_cups_to_fluid_ounces():
    assert convert("Volume", "US Cups (cup)", "US Fluid Ounces (fl oz)", 1.0) == pytest.approx(8.0)


def test_tablespoons_to_teaspoons():
    assert convert("Volume", "US Tablespoons (tbsp)", "US Teaspoons (tsp)", 1.0) == pytest.approx(3.0)


def test_quart_to_pints():
    assert convert("Volume", "US Quarts (qt)", "US Pints (pt)", 1.0) == pytest.approx(2.0)


def test_gallon_to_quarts():
    assert convert("Volume", "US Gallons (gal)", "US Quarts (qt)", 1.0) == pytest.approx(4.0)


def test_gallon_to_cups():
    assert convert("Volume", "US Gallons (gal)", "US Cups (cup)", 1.0) == pytest.approx(16.0)


def test_teaspoons_to_milliliters():
    assert convert("Volume", "US Teaspoons (tsp)", "Milliliters (mL)", 1.0) == pytest.approx(4.92892159375)


def test_liters_to_gallons():
    assert convert("Volume", "Liters (L)", "US Gallons (gal)", 3.785411784) == pytest.approx(1.0)


def test_kilograms_to_pounds():
    assert convert("Weight", "Kilograms (kg)", "Pounds (lb)", 1.0) == pytest.approx(2.20462, rel=1e-4)


def test_celsius_to_fahrenheit():
    assert convert("Temperature", "Celsius (°C)", "Fahrenheit (°F)", 0.0) == pytest.approx(32.0)
    assert convert("Temperature", "Celsius (°C)", "Fahrenheit (°F)", 100.0) == pytest.approx(212.0)


def test_fahrenheit_to_celsius():
    assert convert("Temperature", "Fahrenheit (°F)", "Celsius (°C)", 32.0) == pytest.approx(0.0)


def test_celsius_to_kelvin():
    assert convert("Temperature", "Celsius (°C)", "Kelvin (K)", 0.0) == pytest.approx(273.15)


def test_fahrenheit_to_kelvin_round_trip():
    # Through the base unit (Celsius) and back — exercises both hops at once.
    kelvin = convert("Temperature", "Fahrenheit (°F)", "Kelvin (K)", 98.6)
    back_to_fahrenheit = convert("Temperature", "Kelvin (K)", "Fahrenheit (°F)", kelvin)
    assert back_to_fahrenheit == pytest.approx(98.6, rel=1e-6)


def test_negative_value_converts_correctly():
    assert convert("Length", "Meters (m)", "Feet (ft)", -10.0) == pytest.approx(-32.8084, rel=1e-4)
