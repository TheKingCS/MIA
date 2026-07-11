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


# ----------------------------------------------------------------------
# Area
# ----------------------------------------------------------------------

def test_square_feet_to_square_meters():
    assert convert("Area", "Square Feet (ft²)", "Square Meters (m²)", 1.0) == pytest.approx(0.09290304)


def test_acres_to_square_meters():
    assert convert("Area", "Acres", "Square Meters (m²)", 1.0) == pytest.approx(4046.8564224)


def test_hectares_to_square_meters():
    assert convert("Area", "Hectares", "Square Meters (m²)", 1.0) == pytest.approx(10000.0)


def test_square_kilometers_to_hectares():
    assert convert("Area", "Square Kilometers (km²)", "Hectares", 1.0) == pytest.approx(100.0)


# ----------------------------------------------------------------------
# Speed
# ----------------------------------------------------------------------

def test_km_per_hour_to_m_per_s():
    assert convert("Speed", "Kilometers/Hour (km/h)", "Meters/Second (m/s)", 36.0) == pytest.approx(10.0)


def test_mph_to_m_per_s():
    assert convert("Speed", "Miles/Hour (mph)", "Meters/Second (m/s)", 1.0) == pytest.approx(0.44704)


def test_knots_to_km_per_hour():
    assert convert("Speed", "Knots (kn)", "Kilometers/Hour (km/h)", 1.0) == pytest.approx(1.852)


# ----------------------------------------------------------------------
# Pressure
# ----------------------------------------------------------------------

def test_bar_to_pascals():
    assert convert("Pressure", "Bar", "Pascals (Pa)", 1.0) == pytest.approx(100_000.0)


def test_kpa_to_pascals():
    assert convert("Pressure", "Kilopascals (kPa)", "Pascals (Pa)", 1.0) == pytest.approx(1000.0)


def test_atm_to_psi():
    assert convert("Pressure", "Atmospheres (atm)", "PSI", 1.0) == pytest.approx(14.6959, rel=1e-4)


# ----------------------------------------------------------------------
# Energy
# ----------------------------------------------------------------------

def test_kilocalories_to_joules():
    assert convert("Energy", "Kilocalories (kcal)", "Joules (J)", 1.0) == pytest.approx(4184.0)


def test_kwh_to_joules():
    assert convert("Energy", "Kilowatt-hours (kWh)", "Joules (J)", 1.0) == pytest.approx(3_600_000.0)


def test_btu_to_joules():
    assert convert("Energy", "BTU", "Joules (J)", 1.0) == pytest.approx(1055.05585262)


# ----------------------------------------------------------------------
# Power
# ----------------------------------------------------------------------

def test_horsepower_to_watts():
    assert convert("Power", "Horsepower (hp)", "Watts (W)", 1.0) == pytest.approx(745.6998716, rel=1e-6)


def test_kilowatts_to_watts():
    assert convert("Power", "Kilowatts (kW)", "Watts (W)", 1.0) == pytest.approx(1000.0)


# ----------------------------------------------------------------------
# Time
# ----------------------------------------------------------------------

def test_hours_to_minutes():
    assert convert("Time", "Hours (hr)", "Minutes (min)", 1.0) == pytest.approx(60.0)


def test_days_to_hours():
    assert convert("Time", "Days", "Hours (hr)", 1.0) == pytest.approx(24.0)


def test_weeks_to_days():
    assert convert("Time", "Weeks", "Days", 1.0) == pytest.approx(7.0)


# ----------------------------------------------------------------------
# Data Storage
# ----------------------------------------------------------------------

def test_kilobytes_to_bytes():
    assert convert("Data Storage", "Kilobytes (KB)", "Bytes (B)", 1.0) == pytest.approx(1024.0)


def test_megabytes_to_kilobytes():
    assert convert("Data Storage", "Megabytes (MB)", "Kilobytes (KB)", 1.0) == pytest.approx(1024.0)


def test_gigabytes_to_megabytes():
    assert convert("Data Storage", "Gigabytes (GB)", "Megabytes (MB)", 1.0) == pytest.approx(1024.0)


def test_terabytes_to_gigabytes():
    assert convert("Data Storage", "Terabytes (TB)", "Gigabytes (GB)", 1.0) == pytest.approx(1024.0)


# ----------------------------------------------------------------------
# Angle
# ----------------------------------------------------------------------

def test_degrees_to_radians():
    assert convert("Angle", "Degrees (°)", "Radians (rad)", 180.0) == pytest.approx(3.14159265358979, rel=1e-9)


def test_gradians_to_degrees():
    assert convert("Angle", "Gradians (grad)", "Degrees (°)", 100.0) == pytest.approx(90.0)


# ----------------------------------------------------------------------
# Fuel Economy (reciprocal relationship, not a linear ratio)
# ----------------------------------------------------------------------

def test_km_per_l_to_l_per_100km_self_reciprocal_at_10():
    # A clean case: at exactly 10 km/L, L/100km is also exactly 10 —
    # a convenient sanity check for the reciprocal math.
    assert convert("Fuel Economy", "Kilometers/Liter (km/L)", "Liters/100km (L/100km)", 10.0) == pytest.approx(10.0)


def test_l_per_100km_round_trip():
    km_per_l = convert("Fuel Economy", "Liters/100km (L/100km)", "Kilometers/Liter (km/L)", 7.5)
    back = convert("Fuel Economy", "Kilometers/Liter (km/L)", "Liters/100km (L/100km)", km_per_l)
    assert back == pytest.approx(7.5, rel=1e-9)


def test_mpg_to_km_per_l():
    # 1 mile / 1 US gallon, expressed in km / L.
    assert convert("Fuel Economy", "Miles/Gallon (mpg)", "Kilometers/Liter (km/L)", 1.0) == pytest.approx(
        1.609344 / 3.785411784, rel=1e-9
    )


def test_mpg_round_trip_through_l_per_100km():
    l_per_100km = convert("Fuel Economy", "Miles/Gallon (mpg)", "Liters/100km (L/100km)", 25.0)
    back_to_mpg = convert("Fuel Economy", "Liters/100km (L/100km)", "Miles/Gallon (mpg)", l_per_100km)
    assert back_to_mpg == pytest.approx(25.0, rel=1e-9)
