"""
tests.test_dashboard_module
==============================

Unit tests for modules.dashboard.module's pure functions, same style as
tests/test_expeditions_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.activity_log_manager import ActivityLogEntry
from core.calendar_manager import CalendarEvent
from core.expedition_manager import Expedition
from core.memory_manager import ExpeditionRecap
from core.mission_manager import Mission
from core.project_manager import Project
from core.task_manager import Task
from modules.dashboard.module import (
    format_activity_line,
    format_mission_summary_line,
    format_open_task_line,
    format_project_line,
    format_recap_summary_line,
    format_upcoming_event_line,
)


def test_format_activity_line():
    entry = ActivityLogEntry(entry_id="a1", event_type="module_opened", summary="Opened Notes", timestamp="2026-08-14T09:00:00")
    assert format_activity_line(entry) == "2026-08-14T09:00:00  —  Opened Notes"


def test_format_mission_summary_line_with_objectives():
    mission = Mission(mission_id="m1", name="Master Angler")
    assert format_mission_summary_line(mission, completed_objectives=1, total_objectives=2) == "Master Angler  (1 of 2 objectives complete)"


def test_format_mission_summary_line_no_objectives_yet():
    mission = Mission(mission_id="m1", name="Master Angler")
    assert format_mission_summary_line(mission, completed_objectives=0, total_objectives=0) == "Master Angler  (no objectives yet)"


def test_format_recap_summary_line_full():
    recap = ExpeditionRecap(
        expedition=Expedition(expedition_id="e1", name="Field Season"),
        duration_days=4,
    )
    recap.activity_breakdown = {}
    recap.photo_filenames = [("t1", "a.jpg"), ("t1", "b.jpg")]
    # total_distance_km is a property derived from activity_breakdown; set via a fake stats entry
    from core.memory_manager import ActivityStats
    recap.activity_breakdown = {"Hiking": ActivityStats(activity_type="Hiking", distance_km=11.2)}

    assert format_recap_summary_line(recap) == "Field Season  —  4d  —  11.2 km  —  2 photos"


def test_format_recap_summary_line_minimal():
    recap = ExpeditionRecap(expedition=Expedition(expedition_id="e1", name="Undated Trip"), duration_days=None)
    assert format_recap_summary_line(recap) == "Undated Trip"


def test_format_upcoming_event_line_with_time():
    event = CalendarEvent(event_id="c1", title="Dentist", date="2026-09-01", time="14:00")
    assert format_upcoming_event_line(event) == "2026-09-01 14:00  —  Dentist"


def test_format_upcoming_event_line_all_day():
    event = CalendarEvent(event_id="c1", title="Anniversary", date="2026-09-01")
    assert format_upcoming_event_line(event) == "2026-09-01  —  Anniversary"


def test_format_project_line_with_due_date():
    project = Project(project_id="p1", name="Garage Rewire", status="Active", due_date="2026-08-14")
    assert format_project_line(project) == "Garage Rewire  [Active]  (due 2026-08-14)"


def test_format_project_line_no_due_date():
    project = Project(project_id="p1", name="Someday", status="Planning")
    assert format_project_line(project) == "Someday  [Planning]"


def test_format_open_task_line_with_due_date():
    task = Task(task_id="t1", project_id="p1", title="Buy fuse box", due_date="2026-08-10")
    assert format_open_task_line(task) == "Buy fuse box  (due 2026-08-10)"


def test_format_open_task_line_no_due_date():
    task = Task(task_id="t1", project_id="p1", title="Buy fuse box")
    assert format_open_task_line(task) == "Buy fuse box"
