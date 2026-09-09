"""
tests.test_power_module
=========================

Unit tests for modules.power.module's pure formatting functions — no
Qt event loop needed. Same shape as tests/test_system_health.py's
format_system_health test.
"""

from __future__ import annotations

from core.data_logger_manager import Reading
from core.energy_manager import EnergySource
from core.power_manager import PowerStatus
from modules.power.module import format_energy_reading_row, format_energy_source_row, format_power_status


def test_formats_plugged_in_status():
    status = PowerStatus(percent=100.0, plugged_in=True, seconds_left=None)
    text = format_power_status(status)
    assert "Battery: 100%" in text
    assert "Power: Plugged in" in text
    assert "remaining" not in text


def test_formats_on_battery_with_time_remaining():
    status = PowerStatus(percent=42.0, plugged_in=False, seconds_left=1800)
    text = format_power_status(status)
    assert "Battery: 42%" in text
    assert "Power: On battery" in text
    assert "Estimated time remaining: 30 min" in text


def test_formats_on_battery_without_time_estimate():
    status = PowerStatus(percent=42.0, plugged_in=False, seconds_left=None)
    text = format_power_status(status)
    assert "remaining" not in text


def test_formats_no_battery_detected():
    assert format_power_status(None) == "No battery or UPS detected on this system."


def test_format_energy_source_row_includes_name_and_type():
    source = EnergySource(source_id="s1", name="Backup Generator", source_type="Generator")
    assert format_energy_source_row(source) == "Backup Generator   [Generator]"


def test_format_energy_reading_row_includes_value_unit_time_and_note():
    reading = Reading(reading_id="r1", series_id="x", value=12.4, unit="kWh", note="test run", timestamp="2026-09-09T08:00:00")
    row = format_energy_reading_row(reading)
    assert "12.4 kWh" in row
    assert "2026-09-09 08:00:00" in row
    assert "test run" in row


def test_format_energy_reading_row_omits_note_when_empty():
    reading = Reading(reading_id="r1", series_id="x", value=80.0, unit="%", timestamp="2026-09-09T08:00:00")
    row = format_energy_reading_row(reading)
    assert "—" not in row
