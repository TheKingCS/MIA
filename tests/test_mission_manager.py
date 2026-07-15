"""
tests.test_mission_manager
=============================

Unit tests for core.mission_manager. Isolates _DATA_DIR/_MISSIONS_FILE
into a tmp_path scratch area, same monkeypatch pattern as
test_expedition_manager.py's isolated_paths. objective_progress()'s
trip_duration_hours resolution also needs core.trip_manager isolated,
same pattern as test_memory_manager.py's combined-manager fixture.
"""

from __future__ import annotations

from datetime import datetime

import pytest

import core.expedition_manager as expedition_manager_module
import core.mission_manager as mission_manager_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.mission_manager import MissionManager
from core.trip_manager import TripManager
from core.waypoint_manager import WaypointManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", data_dir / "expeditions.json")
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", data_dir / "trips.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.waypoints = WaypointManager(context)
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.missions = MissionManager(context)
    return context


# ----------------------------------------------------------------------
# Mission CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    context = _make_context()
    assert context.missions.all_missions() == []


def test_add_mission_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    added = context.missions.add_mission(name="Master Angler")

    reloaded = MissionManager(context)
    missions = reloaded.all_missions()
    assert len(missions) == 1
    assert missions[0].mission_id == added.mission_id
    assert missions[0].name == "Master Angler"
    assert missions[0].trip_id is None
    assert missions[0].status == "active"
    assert missions[0].objectives == []
    assert missions[0].created_at
    assert missions[0].updated_at == missions[0].created_at


def test_add_mission_can_link_to_a_trip(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")

    mission = context.missions.add_mission(name="Master Angler", trip_id=trip.trip_id)
    assert mission.trip_id == trip.trip_id
    assert context.missions.missions_for_trip(trip.trip_id) == [mission]


def test_update_mission_changes_fields_and_bumps_updated_at(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Original")
    mission.created_at = "2020-01-01T00:00:00"
    mission.updated_at = "2020-01-01T00:00:00"

    context.missions.update_mission(mission.mission_id, name="Renamed", status="completed")

    assert mission.name == "Renamed"
    assert mission.status == "completed"
    assert mission.created_at == "2020-01-01T00:00:00"  # untouched
    assert mission.updated_at != "2020-01-01T00:00:00"  # bumped


def test_update_mission_rejects_created_at(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    with pytest.raises(ValueError):
        context.missions.update_mission(mission.mission_id, created_at="hacked")


def test_update_mission_rejects_trip_id(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    with pytest.raises(ValueError):
        context.missions.update_mission(mission.mission_id, trip_id="sneaky")


def test_update_mission_unknown_id_raises(isolated_paths):
    context = _make_context()
    with pytest.raises(ValueError):
        context.missions.update_mission("does-not-exist", name="X")


def test_delete_mission_removes_it_and_is_idempotent(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Gone soon")

    context.missions.delete_mission(mission.mission_id)
    assert context.missions.get_mission(mission.mission_id) is None

    context.missions.delete_mission(mission.mission_id)  # already gone — must not raise


def test_all_missions_sorted_most_recently_created_first(isolated_paths):
    context = _make_context()
    first = context.missions.add_mission(name="First")
    first.created_at = "2020-01-01T00:00:00"
    second = context.missions.add_mission(name="Second")
    second.created_at = "2020-06-01T00:00:00"
    context.missions._save()

    ordered = [m.name for m in context.missions.all_missions()]
    assert ordered == ["Second", "First"]


def test_load_handles_corrupt_json_gracefully(isolated_paths, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "missions.json").write_text("{not valid json", encoding="utf-8")

    context = _make_context()
    assert context.missions.all_missions() == []


# ----------------------------------------------------------------------
# Objectives
# ----------------------------------------------------------------------

def test_add_objective_appends_to_mission(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    reloaded = context.missions.get_mission(mission.mission_id)
    assert len(reloaded.objectives) == 1
    assert reloaded.objectives[0].description == "Catch 3 fish"
    assert reloaded.objectives[0].metric_type == "tally"
    assert reloaded.objectives[0].target == 3.0
    assert reloaded.objectives[0].progress == 0.0


def test_add_objective_rejects_unknown_metric_type(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    with pytest.raises(ValueError):
        context.missions.add_objective(mission.mission_id, "Bogus", "bogus_metric", 1.0)


def test_delete_objective_removes_it(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    context.missions.delete_objective(mission.mission_id, 0)
    assert context.missions.get_mission(mission.mission_id).objectives == []


def test_delete_objective_out_of_range_raises(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    with pytest.raises(ValueError):
        context.missions.delete_objective(mission.mission_id, 0)


def test_increment_tally_increases_progress(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    context.missions.increment_tally(mission.mission_id, 0)
    context.missions.increment_tally(mission.mission_id, 0)

    assert context.missions.get_mission(mission.mission_id).objectives[0].progress == 2.0


def test_increment_tally_custom_delta(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    context.missions.increment_tally(mission.mission_id, 0, delta=3.0)

    assert context.missions.get_mission(mission.mission_id).objectives[0].progress == 3.0


def test_increment_tally_rejects_non_tally_objective(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    context.missions.add_objective(mission.mission_id, "Spend 2 hours fishing", "trip_duration_hours", 2.0)

    with pytest.raises(ValueError):
        context.missions.increment_tally(mission.mission_id, 0)


# ----------------------------------------------------------------------
# Celebration notifications — 2026-07-14 aesthetic pass part 5, at the
# user's explicit request ("celebrating their objective wins"). Fires
# uniformly from the manager itself (not the Missions module UI or the
# Assistant's own action handlers) so neither call site needs its own
# copy of "did this just newly become complete."
# ----------------------------------------------------------------------

class _FakeNotifications:
    def __init__(self) -> None:
        self.notified: list[dict] = []

    def notify(self, title, message, level="info", source="system"):
        self.notified.append({"title": title, "message": message, "level": level, "source": source})


def _make_context_with_notifications() -> tuple[AppContext, _FakeNotifications]:
    context = _make_context()
    notifications = _FakeNotifications()
    context.notifications = notifications
    return context, notifications


def test_increment_tally_celebrates_objective_completion(isolated_paths):
    context, notifications = _make_context_with_notifications()
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    context.missions.increment_tally(mission.mission_id, 0)
    context.missions.increment_tally(mission.mission_id, 0)
    assert notifications.notified == []  # not complete yet — no celebration

    # A single-objective mission completes both "this objective" and
    # "all objectives" at once — both notifications are expected here.
    context.missions.increment_tally(mission.mission_id, 0)
    assert len(notifications.notified) == 2
    assert "Objective complete" in notifications.notified[0]["title"]
    assert "Master Angler" in notifications.notified[0]["message"]
    assert "All objectives" in notifications.notified[1]["title"]


def test_increment_tally_does_not_recelebrate_already_complete_objective(isolated_paths):
    context, notifications = _make_context_with_notifications()
    mission = context.missions.add_mission(name="X")
    context.missions.add_objective(mission.mission_id, "Catch 1 fish", "tally", 1.0)

    context.missions.increment_tally(mission.mission_id, 0)
    context.missions.increment_tally(mission.mission_id, 0)  # already complete, incrementing further

    objective_celebrations = [n for n in notifications.notified if "Objective complete" in n["title"]]
    assert len(objective_celebrations) == 1


def test_increment_tally_celebrates_all_objectives_complete(isolated_paths):
    context, notifications = _make_context_with_notifications()
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 1 fish", "tally", 1.0)
    context.missions.add_objective(mission.mission_id, "Catch 1 more fish", "tally", 1.0)

    context.missions.increment_tally(mission.mission_id, 0)
    all_complete_celebrations = [n for n in notifications.notified if "All objectives" in n["title"]]
    assert all_complete_celebrations == []  # only one of two objectives done

    context.missions.increment_tally(mission.mission_id, 1)
    all_complete_celebrations = [n for n in notifications.notified if "All objectives" in n["title"]]
    assert len(all_complete_celebrations) == 1


def test_update_mission_celebrates_completion(isolated_paths):
    context, notifications = _make_context_with_notifications()
    mission = context.missions.add_mission(name="Master Angler")

    context.missions.update_mission(mission.mission_id, status="completed")

    assert len(notifications.notified) == 1
    assert "Mission complete" in notifications.notified[0]["title"]
    assert "Master Angler" in notifications.notified[0]["message"]


def test_update_mission_does_not_recelebrate_already_completed_mission(isolated_paths):
    context, notifications = _make_context_with_notifications()
    mission = context.missions.add_mission(name="X")
    context.missions.update_mission(mission.mission_id, status="completed")
    context.missions.update_mission(mission.mission_id, status="completed")

    assert len(notifications.notified) == 1


def test_update_mission_other_field_changes_do_not_celebrate(isolated_paths):
    context, notifications = _make_context_with_notifications()
    mission = context.missions.add_mission(name="X")
    context.missions.update_mission(mission.mission_id, name="Renamed")
    assert notifications.notified == []


def test_objective_progress_tally_returns_stored_value(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)
    context.missions.increment_tally(mission.mission_id, 0, delta=2.0)

    assert context.missions.objective_progress(mission.mission_id, 0) == 2.0


def test_objective_progress_unknown_mission_or_index_returns_none(isolated_paths):
    context = _make_context()
    assert context.missions.objective_progress("does-not-exist", 0) is None

    mission = context.missions.add_mission(name="X")
    assert context.missions.objective_progress(mission.mission_id, 0) is None


def test_is_objective_complete_true_once_target_reached(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    assert context.missions.is_objective_complete(mission.mission_id, 0) is False
    context.missions.increment_tally(mission.mission_id, 0, delta=3.0)
    assert context.missions.is_objective_complete(mission.mission_id, 0) is True


# ----------------------------------------------------------------------
# trip_duration_hours (computed live from a linked Trip's logged splits)
# ----------------------------------------------------------------------

def test_trip_duration_hours_progress_computed_from_splits(isolated_paths):
    context = _make_context()
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Fishing", activity_type="Fishing")
    context.trips.record_split(trip.trip_id, a.waypoint_id, timestamp=datetime(2026, 8, 14, 8, 0, 0))
    context.trips.record_split(trip.trip_id, b.waypoint_id, timestamp=datetime(2026, 8, 14, 10, 30, 0))

    mission = context.missions.add_mission(name="Master Angler", trip_id=trip.trip_id)
    context.missions.add_objective(mission.mission_id, "Spend 2 hours fishing", "trip_duration_hours", 2.0)

    progress = context.missions.objective_progress(mission.mission_id, 0)
    assert progress == pytest.approx(2.5, abs=0.01)
    assert context.missions.is_objective_complete(mission.mission_id, 0) is True


def test_trip_duration_hours_zero_when_fewer_than_two_splits(isolated_paths):
    context = _make_context()
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Fishing")
    mission = context.missions.add_mission(name="Master Angler", trip_id=trip.trip_id)
    context.missions.add_objective(mission.mission_id, "Spend 2 hours fishing", "trip_duration_hours", 2.0)

    assert context.missions.objective_progress(mission.mission_id, 0) == 0.0
    assert context.missions.is_objective_complete(mission.mission_id, 0) is False


def test_trip_duration_hours_zero_when_mission_has_no_trip(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="General Goal")
    context.missions.add_objective(mission.mission_id, "Spend 2 hours fishing", "trip_duration_hours", 2.0)

    assert context.missions.objective_progress(mission.mission_id, 0) == 0.0
