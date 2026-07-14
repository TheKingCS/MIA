"""
tests.test_memories_module
=============================

Unit tests for modules.memories.module's pure functions, same style as
tests/test_expeditions_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.expedition_manager import Expedition
from core.memory_manager import ActivityStats, ExpeditionRecap
from modules.memories.module import (
    format_activity_stats_line,
    format_recap_header,
    format_waypoint_categories_line,
)


def _make_recap(**expedition_kwargs) -> ExpeditionRecap:
    defaults = {"expedition_id": "exp1", "name": "Field Season"}
    defaults.update(expedition_kwargs)
    return ExpeditionRecap(expedition=Expedition(**defaults), duration_days=None)


def test_format_recap_header_with_location_and_date_range_and_duration():
    recap = _make_recap(start_date="2026-08-14", end_date="2026-08-17", location="Land Between the Lakes")
    recap.duration_days = 4
    assert format_recap_header(recap) == (
        "Field Season  (Land Between the Lakes)  2026-08-14 - 2026-08-17  [4 days]"
    )


def test_format_recap_header_single_day_no_location():
    recap = _make_recap(start_date="2026-08-14", end_date="2026-08-14")
    recap.duration_days = 1
    assert format_recap_header(recap) == "Field Season  2026-08-14  [1 day]"


def test_format_recap_header_no_dates_no_duration():
    recap = _make_recap()
    assert format_recap_header(recap) == "Field Season"


def test_format_activity_stats_line_with_distance_and_speed():
    stats = ActivityStats(activity_type="Hiking", trip_count=2, distance_km=11.2, total_hours=2.3)
    assert format_activity_stats_line(stats) == "Hiking: 2 trips, 11.2 km, avg 4.9 km/h"


def test_format_activity_stats_line_singular_trip_no_distance():
    stats = ActivityStats(activity_type="Fishing", trip_count=1)
    assert format_activity_stats_line(stats) == "Fishing: 1 trip"


def test_format_waypoint_categories_line_multiple_sorted():
    assert format_waypoint_categories_line({"Trailhead": 1, "Campsite": 2}) == "Visited: 2 Campsite, 1 Trailhead"


def test_format_waypoint_categories_line_empty():
    assert format_waypoint_categories_line({}) == ""
