"""
tests.test_navigation_module
===============================

Unit tests for modules.navigation.module's pure functions.
format_sun_moon_summary() is tested against real coordinates (not
mocked) since astral itself is the "real dependency" here (offline,
deterministic, no network) — same reasoning as
test_system_health.py mocking psutil but this module
having no external state to fake in the first place.
"""

from __future__ import annotations

from datetime import date

from core.waypoint_manager import Waypoint
from modules.navigation.module import format_moon_phase_name, format_sun_moon_summary, format_waypoint_row

NEW_YORK = (40.7128, -74.0060)


def test_format_waypoint_row():
    waypoint = Waypoint(waypoint_id="abc123", name="Base Camp", latitude=40.12349, longitude=-105.6789)
    assert format_waypoint_row(waypoint) == "Base Camp  (40.1235, -105.6789)"


def test_format_waypoint_row_with_category():
    waypoint = Waypoint(
        waypoint_id="abc123",
        name="Ridge Camp",
        latitude=40.12349,
        longitude=-105.6789,
        category="Campsite",
    )
    assert format_waypoint_row(waypoint) == "[Campsite] Ridge Camp  (40.1235, -105.6789)"


def test_moon_phase_name_boundaries():
    # Exact boundaries per astral's own documented scale.
    assert format_moon_phase_name(0.0) == "New Moon"
    assert format_moon_phase_name(6.99) == "New Moon"
    assert format_moon_phase_name(7.0) == "First Quarter"
    assert format_moon_phase_name(13.99) == "First Quarter"
    assert format_moon_phase_name(14.0) == "Full Moon"
    assert format_moon_phase_name(20.99) == "Full Moon"
    assert format_moon_phase_name(21.0) == "Last Quarter"
    assert format_moon_phase_name(27.99) == "Last Quarter"


def test_sun_moon_summary_for_real_coordinates_has_sensible_shape():
    summary = format_sun_moon_summary(*NEW_YORK, date(2026, 7, 12))
    lines = summary.splitlines()
    assert lines[0].startswith("Sunrise: ")
    assert lines[1].startswith("Sunset: ")
    assert lines[2].startswith("Moon phase: ")

    sunrise_hour = int(lines[0].split(": ")[1].split(":")[0])
    sunset_hour = int(lines[1].split(": ")[1].split(":")[0])
    # Mid-July in New York: sunrise well before noon, sunset well after.
    assert 4 <= sunrise_hour <= 7
    assert 18 <= sunset_hour <= 22


def test_sun_moon_summary_moon_phase_is_a_known_name():
    summary = format_sun_moon_summary(*NEW_YORK, date(2026, 7, 12))
    moon_line = [line for line in summary.splitlines() if line.startswith("Moon phase:")][0]
    phase_name = moon_line.split(": ")[1]
    assert phase_name in {"New Moon", "First Quarter", "Full Moon", "Last Quarter"}


def test_sun_moon_summary_handles_polar_no_sunrise_gracefully():
    # Deep into the polar circle in summer — real ValueError case from
    # astral (perpetual daylight), not a hypothetical.
    summary = format_sun_moon_summary(89.9, 0.0, date(2026, 6, 21))
    assert "unavailable" in summary.lower()
