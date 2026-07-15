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

from core.activity_log_manager import ActivityLogEntry
from core.mission_manager import Mission, Objective
from core.power_manager import PowerStatus
from core.project_manager import Project
from core.volume_manager import VolumeStatus
from gui.home_dashboard import (
    format_active_mission_line,
    format_activity_log_line,
    format_clock_date,
    format_clock_time,
    format_current_project_line,
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


def test_format_current_project_line_none():
    assert format_current_project_line(None, 0) == "No active projects."


def test_format_current_project_line_single_active():
    project = Project(project_id="p1", name="Garage Rewire", status="Active")
    assert format_current_project_line(project, 1) == "Garage Rewire  [Active]"


def test_format_current_project_line_multiple_active():
    project = Project(project_id="p1", name="Garage Rewire", status="Active")
    assert format_current_project_line(project, 3) == "Garage Rewire  [Active]  (+2 more active)"


def test_format_activity_log_line_empty():
    assert format_activity_log_line([]) == "No recent activity."


def test_format_activity_log_line_single_entry():
    entries = [ActivityLogEntry(entry_id="e1", event_type="module_opened", summary="Opened Notes", timestamp="2026-07-15T14:02:00")]
    assert format_activity_log_line(entries) == "14:02 Opened Notes"


def test_format_activity_log_line_multiple_entries_joined():
    entries = [
        ActivityLogEntry(entry_id="e1", event_type="waypoint_added", summary="Waypoint added", timestamp="2026-07-15T14:02:00"),
        ActivityLogEntry(entry_id="e2", event_type="battery_check", summary="Battery check ok", timestamp="2026-07-15T14:00:00"),
    ]
    assert format_activity_log_line(entries) == "14:02 Waypoint added  //  14:00 Battery check ok"
