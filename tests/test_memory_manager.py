"""
tests.test_memory_manager
============================

Unit tests for core.memory_manager.MemoryManager — docs/ROADMAP.md
milestone v0.17, Memories. Isolates every underlying manager's data
dir into a tmp_path scratch area, same monkeypatch pattern as
test_trip_manager.py's isolated_paths, since MemoryManager aggregates
across Expedition/Trip/Waypoint/Journal.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

import core.expedition_manager as expedition_manager_module
import core.journal_manager as journal_manager_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.journal_manager import JournalManager
from core.memory_manager import MemoryManager
from core.trip_manager import TripManager
from core.waypoint_manager import WaypointManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", data_dir / "expeditions.json")
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", data_dir / "trips.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", data_dir / "journal_entries.json")


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.waypoints = WaypointManager(context)
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.journal = JournalManager(context)
    context.memories = MemoryManager(context)
    return context


def test_recap_for_unknown_expedition_returns_none(isolated_paths):
    context = _make_context()
    assert context.memories.recap_for_expedition("does-not-exist") is None


def test_recap_with_no_trips_has_empty_breakdown(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Solo Trip", start_date="2026-08-14")

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.expedition.name == "Solo Trip"
    assert recap.activity_breakdown == {}
    assert recap.waypoint_categories_visited == {}
    assert recap.journal_highlights == []
    assert recap.photo_filenames == []
    assert recap.total_distance_km == 0.0


def test_duration_days_from_expedition_start_and_end_dates(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(
        name="Field Season", start_date="2026-08-14", end_date="2026-08-17"
    )
    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.duration_days == 4


def test_duration_days_single_day_when_only_start_date_set(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Day Trip", start_date="2026-08-14")
    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.duration_days == 1


def test_duration_days_falls_back_to_trip_date_span(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")  # no dates
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", start_date="2026-08-14")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 3", start_date="2026-08-16")

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.duration_days == 3


def test_duration_days_none_when_nothing_dated(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Undated")
    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.duration_days is None


def test_activity_breakdown_aggregates_distance_and_speed(isolated_paths):
    context = _make_context()
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="Hiking")

    context.trips.record_split(trip.trip_id, a.waypoint_id, timestamp=datetime(2026, 8, 14, 8, 0, 0))
    context.trips.record_split(trip.trip_id, b.waypoint_id, timestamp=datetime(2026, 8, 14, 10, 0, 0))

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    stats = recap.activity_breakdown["Hiking"]
    assert stats.trip_count == 1
    expected_distance = context.trips.total_distance_km(trip.trip_id)
    assert stats.distance_km == pytest.approx(expected_distance, abs=0.01)
    assert stats.total_hours == pytest.approx(2.0, abs=0.01)
    assert stats.average_speed_kmh == pytest.approx(expected_distance / 2.0, abs=0.01)


def test_activity_breakdown_groups_multiple_trips_by_activity_type(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="Hiking")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 2", activity_type="Hiking")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 3", activity_type="Kayaking")

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.activity_breakdown["Hiking"].trip_count == 2
    assert recap.activity_breakdown["Kayaking"].trip_count == 1


def test_activity_breakdown_unspecified_activity_type_groups_as_other(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="")

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.activity_breakdown["Other"].trip_count == 1


def test_no_distance_when_fewer_than_two_splits(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="Hiking")

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    stats = recap.activity_breakdown["Hiking"]
    assert stats.distance_km == 0.0
    assert stats.average_speed_kmh is None


def test_waypoint_categories_visited_counts_planned_route_waypoints(isolated_paths):
    context = _make_context()
    camp = context.waypoints.add_waypoint(name="Ridge Camp", latitude=0.0, longitude=0.0, category="Campsite")
    trailhead = context.waypoints.add_waypoint(name="Trailhead", latitude=0.1, longitude=0.1, category="Trailhead")
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    context.trips.add_waypoint_to_route(trip.trip_id, camp.waypoint_id)
    context.trips.add_waypoint_to_route(trip.trip_id, trailhead.waypoint_id)

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.waypoint_categories_visited == {"Campsite": 1, "Trailhead": 1}


def test_waypoint_categories_visited_skips_unresolvable_waypoints(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    context.trips.add_waypoint_to_route(trip.trip_id, "deleted-waypoint")

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.waypoint_categories_visited == {}


def test_journal_highlights_pulls_entries_linked_to_trips_in_expedition(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    context.journal.add_entry(title="Arrived", body="Made camp", trip_id=trip.trip_id, conditions="Clear, 15C")
    context.journal.add_entry(title="Unrelated note")  # no trip_id — must not appear

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    titles = [e.title for e in recap.journal_highlights]
    assert titles == ["Arrived"]


def test_photo_filenames_collected_across_trips(isolated_paths, tmp_path):
    context = _make_context()
    context.config.set("trips.photo_root_path", str(tmp_path / "trip_photos"))
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")

    photo_source = tmp_path / "sunrise.jpg"
    photo_source.write_bytes(b"fake image data")
    context.trips.add_photo(trip.trip_id, photo_source)

    recap = context.memories.recap_for_expedition(expedition.expedition_id)
    assert recap.photo_filenames == [(trip.trip_id, "sunrise.jpg")]
    assert recap.photo_count == 1


def test_all_recaps_sorted_most_recent_first(isolated_paths):
    context = _make_context()
    context.expeditions.add_expedition(name="Earlier", start_date="2026-07-01")
    context.expeditions.add_expedition(name="Later", start_date="2026-09-01")

    names = [r.expedition.name for r in context.memories.all_recaps()]
    assert names == ["Later", "Earlier"]


def test_on_this_day_matches_month_and_day_in_a_prior_year(isolated_paths):
    context = _make_context()
    context.expeditions.add_expedition(name="Last Year's Trip", start_date="2025-07-14")
    context.expeditions.add_expedition(name="Unrelated Trip", start_date="2025-03-01")

    matches = context.memories.on_this_day(today=date(2026, 7, 14))
    names = [r.expedition.name for r in matches]
    assert names == ["Last Year's Trip"]


def test_on_this_day_excludes_the_current_year_itself(isolated_paths):
    context = _make_context()
    context.expeditions.add_expedition(name="Today's Trip", start_date="2026-07-14")

    matches = context.memories.on_this_day(today=date(2026, 7, 14))
    assert matches == []
