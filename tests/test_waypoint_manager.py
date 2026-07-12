"""
tests.test_waypoint_manager
==============================

Unit tests for core.waypoint_manager. haversine_distance_km()/
initial_bearing_degrees() are checked against real, well-known
distances/bearings (New York <-> Los Angeles, London <-> Paris) rather
than only synthetic values, so a sign error or unit mistake can't
accidentally cancel out and still pass. Manager CRUD tests isolate
_DATA_DIR/_WAYPOINTS_FILE into a tmp_path scratch area (same
monkeypatch pattern as test_inventory_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.waypoint_manager import WaypointManager, haversine_distance_km, initial_bearing_degrees

NEW_YORK = (40.7128, -74.0060)
LOS_ANGELES = (34.0522, -118.2437)
LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    waypoints_file = data_dir / "waypoints.json"
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", waypoints_file)
    return data_dir, waypoints_file


def _make_manager() -> WaypointManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return WaypointManager(context)


# ----------------------------------------------------------------------
# haversine_distance_km / initial_bearing_degrees (pure math)
# ----------------------------------------------------------------------

def test_distance_matches_known_real_world_value_ny_to_la():
    distance = haversine_distance_km(*NEW_YORK, *LOS_ANGELES)
    assert distance == pytest.approx(3936, abs=15)


def test_distance_matches_known_real_world_value_london_to_paris():
    distance = haversine_distance_km(*LONDON, *PARIS)
    assert distance == pytest.approx(344, abs=5)


def test_distance_is_symmetric():
    forward = haversine_distance_km(*LONDON, *PARIS)
    backward = haversine_distance_km(*PARIS, *LONDON)
    assert forward == pytest.approx(backward, abs=0.01)


def test_distance_between_identical_points_is_zero():
    assert haversine_distance_km(*NEW_YORK, *NEW_YORK) == pytest.approx(0, abs=0.001)


def test_bearing_london_to_paris_is_roughly_southeast():
    # Paris is south-southeast of London — a real, checkable fact, not
    # an arbitrary tolerance band.
    bearing = initial_bearing_degrees(*LONDON, *PARIS)
    assert 100 < bearing < 170


def test_bearing_is_not_symmetric_reverse_is_roughly_opposite():
    forward = initial_bearing_degrees(*LONDON, *PARIS)
    backward = initial_bearing_degrees(*PARIS, *LONDON)
    # Reverse bearing isn't exactly forward+180 on a sphere, but should
    # be close for a short-ish hop like this. Wrap (backward - forward)
    # into [-180, 180] and compare to the expected 180 offset.
    diff = abs((backward - forward) % 360 - 180)
    assert diff < 10


# ----------------------------------------------------------------------
# WaypointManager CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_waypoints() == []


def test_add_waypoint_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_waypoint(name="Base Camp", latitude=40.0, longitude=-105.0, notes="Trailhead parking")

    reloaded = _make_manager()
    waypoints = reloaded.all_waypoints()
    assert len(waypoints) == 1
    assert waypoints[0].waypoint_id == added.waypoint_id
    assert waypoints[0].name == "Base Camp"
    assert waypoints[0].latitude == 40.0
    assert waypoints[0].longitude == -105.0
    assert waypoints[0].notes == "Trailhead parking"
    assert waypoints[0].created_at


def test_update_waypoint_changes_fields(isolated_paths):
    manager = _make_manager()
    waypoint = manager.add_waypoint(name="Original", latitude=1.0, longitude=2.0)
    manager.update_waypoint(waypoint.waypoint_id, name="Renamed", latitude=3.0)
    assert waypoint.name == "Renamed"
    assert waypoint.latitude == 3.0


def test_update_waypoint_rejects_created_at(isolated_paths):
    manager = _make_manager()
    waypoint = manager.add_waypoint(name="X", latitude=0.0, longitude=0.0)
    with pytest.raises(ValueError):
        manager.update_waypoint(waypoint.waypoint_id, created_at="hacked")


def test_update_waypoint_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_waypoint("does-not-exist", name="X")


def test_delete_waypoint_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    waypoint = manager.add_waypoint(name="Gone soon", latitude=0.0, longitude=0.0)

    manager.delete_waypoint(waypoint.waypoint_id)
    assert manager.get_waypoint(waypoint.waypoint_id) is None

    manager.delete_waypoint(waypoint.waypoint_id)  # already gone — must not raise


def test_all_waypoints_sorted_alphabetically(isolated_paths):
    manager = _make_manager()
    manager.add_waypoint(name="Zebra Point", latitude=0.0, longitude=0.0)
    manager.add_waypoint(name="alpha camp", latitude=0.0, longitude=0.0)

    ordered = [w.name for w in manager.all_waypoints()]
    assert ordered == ["alpha camp", "Zebra Point"]


def test_distance_and_bearing_between_real_waypoints(isolated_paths):
    manager = _make_manager()
    ny = manager.add_waypoint(name="New York", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
    la = manager.add_waypoint(name="Los Angeles", latitude=LOS_ANGELES[0], longitude=LOS_ANGELES[1])

    result = manager.distance_and_bearing(ny.waypoint_id, la.waypoint_id)
    assert result is not None
    distance, bearing = result
    assert distance == pytest.approx(3936, abs=15)
    assert 0 <= bearing < 360


def test_distance_and_bearing_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    waypoint = manager.add_waypoint(name="X", latitude=0.0, longitude=0.0)
    assert manager.distance_and_bearing(waypoint.waypoint_id, "does-not-exist") is None


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, waypoints_file = isolated_paths
    data_dir.mkdir(parents=True)
    waypoints_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_waypoints() == []
