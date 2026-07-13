"""
tests.test_power_module
=========================

Unit test for modules.power.module.format_power_status — pure
formatting logic, no Qt event loop needed. Same shape as
tests/test_system_health.py's format_system_health test.
"""

from __future__ import annotations

from core.power_manager import PowerStatus
from modules.power.module import format_power_status


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
