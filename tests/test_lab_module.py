"""
tests.test_lab_module
========================

Unit test for modules.lab.module.format_reading_row — pure formatting
logic, no Qt event loop needed. Same shape as
tests/test_notes_module.py's format_entry_row test.
"""

from __future__ import annotations

from core.data_logger_manager import Reading
from modules.lab.module import format_reading_row


def test_formats_value_unit_and_note():
    reading = Reading(
        reading_id="abc123",
        series_id="multimeter_voltage",
        value=3.3,
        unit="V",
        note="bench PSU",
        timestamp="2026-07-12T14:00:00",
    )
    assert format_reading_row(reading) == "2026-07-12 14:00:00   3.3 V  — bench PSU"


def test_omits_unit_and_note_when_absent():
    reading = Reading(
        reading_id="abc123",
        series_id="soil_moisture",
        value=42.0,
        timestamp="2026-07-12T14:00:00",
    )
    assert format_reading_row(reading) == "2026-07-12 14:00:00   42"


def test_handles_missing_timestamp():
    reading = Reading(reading_id="abc123", series_id="x", value=1.5)
    assert format_reading_row(reading) == "   1.5"
