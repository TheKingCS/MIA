"""
tests.test_home_dashboard
============================

Unit tests for gui.home_dashboard's pure formatting helpers. The
reactive widget/QTimer behavior itself is verified with a headless
offscreen-QPA smoke test (this project's convention for Qt widget
behavior), not pytest — see gui/character_panel.py's own test file for
the same split.
"""

from __future__ import annotations

from datetime import date, datetime

from core.mission_manager import Mission, Objective
from core.power_manager import PowerStatus
from core.volume_manager import VolumeStatus
from gui.home_dashboard import (
    format_active_mission_line,
    format_clock_date,
    format_clock_time,
    format_power_line,
    format_volume_line,
)


def test_format_clock_time():
    assert format_clock_time(datetime(2026, 7, 14, 9, 5, 3)) == "09:05:03"


def test_format_clock_date_has_no_leading_zero_and_no_platform_specific_codes():
    assert format_clock_date(date(2026, 7, 4)) == "Saturday, July 4"


def test_format_power_line_no_battery():
    assert format_power_line(None) == "No battery or UPS detected on this system."


def test_format_power_line_plugged_in():
    status = PowerStatus(percent=87.4, plugged_in=True, seconds_left=None)
    assert format_power_line(status) == "87%  —  Plugged in"


def test_format_power_line_on_battery():
    status = PowerStatus(percent=42.0, plugged_in=False, seconds_left=600)
    assert format_power_line(status) == "42%  —  On battery"


def test_format_active_mission_line_none():
    assert format_active_mission_line(None, 0, 0) == "No active mission."


def test_format_active_mission_line_no_objectives():
    mission = Mission(mission_id="m1", name="Scout the ridge")
    assert format_active_mission_line(mission, 0, 0) == "Scout the ridge  (no objectives yet)"


def test_format_active_mission_line_with_progress():
    mission = Mission(
        mission_id="m1",
        name="Scout the ridge",
        objectives=[
            Objective(description="Reach the summit", metric_type="tally", target=1),
            Objective(description="Take a photo", metric_type="tally", target=1),
        ],
    )
    assert format_active_mission_line(mission, 1, 2) == "Scout the ridge  —  1/2 objectives complete"


def test_format_volume_line_unavailable():
    assert format_volume_line(None) == "Not available on this device."


def test_format_volume_line_normal():
    assert format_volume_line(VolumeStatus(percent=62, muted=False)) == "62%"


def test_format_volume_line_muted():
    assert format_volume_line(VolumeStatus(percent=62, muted=True)) == "62%  —  Muted"
