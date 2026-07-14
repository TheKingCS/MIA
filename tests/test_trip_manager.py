"""
tests.test_trip_manager
==========================

Unit tests for core.trip_manager. Isolates _DATA_DIR/_TRIPS_FILE into a
tmp_path scratch area (same monkeypatch pattern as
test_waypoint_manager.py's isolated_paths). planned_route_distance_km()
is checked against the same known real-world distance
test_waypoint_manager.py already uses (New York <-> Los Angeles) so a
unit/sign mistake can't accidentally cancel out and still pass.

Only 12.1's surface (CRUD + route helpers + planned_route_distance_km)
is covered here — gear/split/photo methods land (and get their own
tests added to this file) in later milestones.
"""

from __future__ import annotations

from datetime import datetime

import pytest

import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.trip_manager import ACTIVITY_TYPES, TripManager
from core.waypoint_manager import WaypointManager

NEW_YORK = (40.7128, -74.0060)
LOS_ANGELES = (34.0522, -118.2437)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    trips_file = data_dir / "trips.json"
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", trips_file)
    # _make_context() below constructs a real WaypointManager (needed for
    # the route/distance tests) — without also isolating its data path
    # here, every test that adds a waypoint (New York/Los Angeles/A/B/C
    # fixtures below) was silently writing into the real, production
    # data/waypoints.json on every `pytest` run. This was the actual
    # source of this project's repeated waypoints.json pollution
    # (previously misattributed to ad hoc debugging scripts) — found by
    # tracing timestamps on a fresh round of leaked entries back to a
    # `pytest` invocation rather than any rendering/screenshot script.
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")
    return data_dir, trips_file


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.waypoints = WaypointManager(context)
    return context


def _make_manager(context: AppContext | None = None) -> TripManager:
    return TripManager(context or _make_context())


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_trips() == []


def test_add_trip_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    added = manager.add_trip(
        expedition_id="exp1",
        name="Hike In",
        start_date="2026-08-14",
        end_date="2026-08-14",
        notes="Start early.",
    )

    reloaded = TripManager(context)
    trips = reloaded.all_trips()
    assert len(trips) == 1
    assert trips[0].trip_id == added.trip_id
    assert trips[0].expedition_id == "exp1"
    assert trips[0].name == "Hike In"
    assert trips[0].start_date == "2026-08-14"
    assert trips[0].notes == "Start early."
    assert trips[0].status == "planned"
    assert trips[0].waypoint_ids == []
    assert trips[0].splits == []
    assert trips[0].gear == []
    assert trips[0].photo_filenames == []
    assert trips[0].created_at
    assert trips[0].updated_at == trips[0].created_at


def test_update_trip_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="Original")
    trip.created_at = "2020-01-01T00:00:00"
    trip.updated_at = "2020-01-01T00:00:00"

    manager.update_trip(trip.trip_id, name="Renamed", status="active")

    assert trip.name == "Renamed"
    assert trip.status == "active"
    assert trip.created_at == "2020-01-01T00:00:00"  # untouched
    assert trip.updated_at != "2020-01-01T00:00:00"  # bumped


def test_update_trip_rejects_created_at_and_expedition_id(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    with pytest.raises(ValueError):
        manager.update_trip(trip.trip_id, created_at="hacked")
    with pytest.raises(ValueError):
        manager.update_trip(trip.trip_id, expedition_id="exp2")


def test_update_trip_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_trip("does-not-exist", name="X")


def test_delete_trip_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="Gone soon")

    manager.delete_trip(trip.trip_id)
    assert manager.get_trip(trip.trip_id) is None

    manager.delete_trip(trip.trip_id)  # already gone — must not raise


def test_get_trip_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_trip("does-not-exist") is None


def test_add_trip_activity_type_defaults_to_unspecified(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    assert trip.activity_type == ""


def test_add_trip_activity_type_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    added = manager.add_trip(expedition_id="exp1", name="Evening Cast", activity_type="Fishing")

    reloaded = TripManager(context)
    trip = reloaded.get_trip(added.trip_id)
    assert trip.activity_type == "Fishing"


def test_update_trip_activity_type(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.update_trip(trip.trip_id, activity_type="Kayaking")
    assert trip.activity_type == "Kayaking"


def test_activity_types_includes_expected_values():
    assert "Hiking" in ACTIVITY_TYPES
    assert "Fishing" in ACTIVITY_TYPES
    assert "Kayaking" in ACTIVITY_TYPES
    assert "Biking" in ACTIVITY_TYPES


def test_all_trips_sorted_by_start_date(isolated_paths):
    manager = _make_manager()
    manager.add_trip(expedition_id="exp1", name="Later Leg", start_date="2026-08-16")
    manager.add_trip(expedition_id="exp1", name="Earlier Leg", start_date="2026-08-14")

    ordered = [t.name for t in manager.all_trips()]
    assert ordered == ["Earlier Leg", "Later Leg"]


def test_trips_for_expedition_filters_and_sorts(isolated_paths):
    manager = _make_manager()
    manager.add_trip(expedition_id="exp1", name="Exp1 Later", start_date="2026-08-16")
    manager.add_trip(expedition_id="exp1", name="Exp1 Earlier", start_date="2026-08-14")
    manager.add_trip(expedition_id="exp2", name="Exp2 Only", start_date="2026-08-15")

    ordered = [t.name for t in manager.trips_for_expedition("exp1")]
    assert ordered == ["Exp1 Earlier", "Exp1 Later"]


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, trips_file = isolated_paths
    data_dir.mkdir(parents=True)
    trips_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_trips() == []


# ----------------------------------------------------------------------
# Route helpers + planned_route_distance_km
# ----------------------------------------------------------------------

def test_add_and_remove_waypoint_from_route(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")

    manager.add_waypoint_to_route(trip.trip_id, "wp1")
    manager.add_waypoint_to_route(trip.trip_id, "wp2")
    assert trip.waypoint_ids == ["wp1", "wp2"]

    manager.remove_waypoint_from_route(trip.trip_id, "wp1")
    assert trip.waypoint_ids == ["wp2"]


def test_remove_waypoint_from_route_removes_only_first_occurrence(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="Out and back")
    manager.add_waypoint_to_route(trip.trip_id, "wp1")
    manager.add_waypoint_to_route(trip.trip_id, "wp2")
    manager.add_waypoint_to_route(trip.trip_id, "wp1")  # revisits wp1 on the way back

    manager.remove_waypoint_from_route(trip.trip_id, "wp1")
    assert trip.waypoint_ids == ["wp2", "wp1"]


def test_remove_waypoint_not_in_route_is_a_no_op(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.add_waypoint_to_route(trip.trip_id, "wp1")

    manager.remove_waypoint_from_route(trip.trip_id, "does-not-exist")
    assert trip.waypoint_ids == ["wp1"]


def test_planned_route_distance_km_matches_known_real_world_value(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    ny = context.waypoints.add_waypoint(name="New York", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
    la = context.waypoints.add_waypoint(name="Los Angeles", latitude=LOS_ANGELES[0], longitude=LOS_ANGELES[1])
    trip = manager.add_trip(expedition_id="exp1", name="Cross Country")
    manager.add_waypoint_to_route(trip.trip_id, ny.waypoint_id)
    manager.add_waypoint_to_route(trip.trip_id, la.waypoint_id)

    distance = manager.planned_route_distance_km(trip.trip_id)
    assert distance == pytest.approx(3936, abs=15)


def test_planned_route_distance_km_sums_multiple_legs(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    c = context.waypoints.add_waypoint(name="C", latitude=0.0, longitude=2.0)
    trip = manager.add_trip(expedition_id="exp1", name="Three Points")
    for waypoint in (a, b, c):
        manager.add_waypoint_to_route(trip.trip_id, waypoint.waypoint_id)

    leg_ab = manager.context.waypoints.distance_and_bearing(a.waypoint_id, b.waypoint_id)[0]
    leg_bc = manager.context.waypoints.distance_and_bearing(b.waypoint_id, c.waypoint_id)[0]

    distance = manager.planned_route_distance_km(trip.trip_id)
    assert distance == pytest.approx(leg_ab + leg_bc, abs=0.01)


def test_planned_route_distance_km_none_for_fewer_than_two_waypoints(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")

    assert manager.planned_route_distance_km(trip.trip_id) is None

    manager.add_waypoint_to_route(trip.trip_id, a.waypoint_id)
    assert manager.planned_route_distance_km(trip.trip_id) is None


def test_planned_route_distance_km_skips_unresolvable_waypoints(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.add_waypoint_to_route(trip.trip_id, a.waypoint_id)
    manager.add_waypoint_to_route(trip.trip_id, "deleted-waypoint")
    manager.add_waypoint_to_route(trip.trip_id, b.waypoint_id)

    expected = manager.context.waypoints.distance_and_bearing(a.waypoint_id, b.waypoint_id)[0]
    distance = manager.planned_route_distance_km(trip.trip_id)
    assert distance == pytest.approx(expected, abs=0.01)


def test_planned_route_distance_km_unknown_trip_returns_none(isolated_paths):
    manager = _make_manager()
    assert manager.planned_route_distance_km("does-not-exist") is None


# ----------------------------------------------------------------------
# Gear checklist
# ----------------------------------------------------------------------

def test_add_gear_item_from_inventory_and_custom(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")

    manager.add_gear_item(trip.trip_id, label="Tent", item_id="inv1")
    manager.add_gear_item(trip.trip_id, label="Borrowed Stove")

    assert len(trip.gear) == 2
    assert trip.gear[0].label == "Tent"
    assert trip.gear[0].item_id == "inv1"
    assert trip.gear[0].packed is False
    assert trip.gear[1].label == "Borrowed Stove"
    assert trip.gear[1].item_id is None


def test_toggle_gear_packed(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.add_gear_item(trip.trip_id, label="Tent")

    manager.toggle_gear_packed(trip.trip_id, 0)
    assert trip.gear[0].packed is True

    manager.toggle_gear_packed(trip.trip_id, 0)
    assert trip.gear[0].packed is False


def test_toggle_gear_packed_out_of_range_raises(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    with pytest.raises(ValueError):
        manager.toggle_gear_packed(trip.trip_id, 0)


def test_remove_gear_item(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.add_gear_item(trip.trip_id, label="Tent")
    manager.add_gear_item(trip.trip_id, label="Stove")

    manager.remove_gear_item(trip.trip_id, 0)
    assert [g.label for g in trip.gear] == ["Stove"]


def test_remove_gear_item_out_of_range_raises(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    with pytest.raises(ValueError):
        manager.remove_gear_item(trip.trip_id, 0)


def test_gear_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.add_gear_item(trip.trip_id, label="Tent", item_id="inv1")
    manager.toggle_gear_packed(trip.trip_id, 0)

    reloaded = TripManager(context)
    reloaded_trip = reloaded.get_trip(trip.trip_id)
    assert len(reloaded_trip.gear) == 1
    assert reloaded_trip.gear[0].label == "Tent"
    assert reloaded_trip.gear[0].item_id == "inv1"
    assert reloaded_trip.gear[0].packed is True


# ----------------------------------------------------------------------
# Logged checkpoints: record_split / leg_summaries / total_distance_km /
# average_speed_kmh
# ----------------------------------------------------------------------

def test_record_split_defaults_timestamp_to_now(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.record_split(trip.trip_id, "wp1")
    assert len(trip.splits) == 1
    assert trip.splits[0].waypoint_id == "wp1"
    assert trip.splits[0].logged_at  # non-empty


def test_leg_summaries_matches_hand_computed_distance_and_speed(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    # 1 degree of longitude at the equator is ~111.32 km.
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")

    t0 = datetime(2026, 8, 14, 8, 0, 0)
    t1 = datetime(2026, 8, 14, 10, 0, 0)  # 2 hours later
    manager.record_split(trip.trip_id, a.waypoint_id, timestamp=t0)
    manager.record_split(trip.trip_id, b.waypoint_id, timestamp=t1)

    summaries = manager.leg_summaries(trip.trip_id)
    assert len(summaries) == 1
    leg = summaries[0]
    expected_distance = context.waypoints.distance_and_bearing(a.waypoint_id, b.waypoint_id)[0]
    assert leg.distance_km == pytest.approx(expected_distance, abs=0.01)
    assert leg.elapsed_hours == pytest.approx(2.0, abs=0.001)
    assert leg.speed_kmh == pytest.approx(expected_distance / 2.0, abs=0.01)


def test_leg_summaries_same_second_splits_give_none_speed(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")

    same_instant = datetime(2026, 8, 14, 8, 0, 0)
    manager.record_split(trip.trip_id, a.waypoint_id, timestamp=same_instant)
    manager.record_split(trip.trip_id, b.waypoint_id, timestamp=same_instant)

    summaries = manager.leg_summaries(trip.trip_id)
    assert len(summaries) == 1
    assert summaries[0].elapsed_hours == 0
    assert summaries[0].speed_kmh is None


def test_leg_summaries_fewer_than_two_splits_is_empty(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    assert manager.leg_summaries(trip.trip_id) == []

    manager.record_split(trip.trip_id, "wp1")
    assert manager.leg_summaries(trip.trip_id) == []


def test_leg_summaries_skips_unresolvable_waypoints(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.record_split(trip.trip_id, a.waypoint_id, timestamp=datetime(2026, 8, 14, 8, 0, 0))
    manager.record_split(trip.trip_id, "deleted-waypoint", timestamp=datetime(2026, 8, 14, 9, 0, 0))

    assert manager.leg_summaries(trip.trip_id) == []


def test_total_distance_km_sums_all_legs(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    c = context.waypoints.add_waypoint(name="C", latitude=0.0, longitude=2.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.record_split(trip.trip_id, a.waypoint_id, timestamp=datetime(2026, 8, 14, 8, 0, 0))
    manager.record_split(trip.trip_id, b.waypoint_id, timestamp=datetime(2026, 8, 14, 9, 0, 0))
    manager.record_split(trip.trip_id, c.waypoint_id, timestamp=datetime(2026, 8, 14, 10, 0, 0))

    leg_ab = context.waypoints.distance_and_bearing(a.waypoint_id, b.waypoint_id)[0]
    leg_bc = context.waypoints.distance_and_bearing(b.waypoint_id, c.waypoint_id)[0]
    assert manager.total_distance_km(trip.trip_id) == pytest.approx(leg_ab + leg_bc, abs=0.01)


def test_total_distance_km_none_with_no_legs(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    assert manager.total_distance_km(trip.trip_id) is None


def test_average_speed_kmh_over_multiple_legs(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    c = context.waypoints.add_waypoint(name="C", latitude=0.0, longitude=2.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.record_split(trip.trip_id, a.waypoint_id, timestamp=datetime(2026, 8, 14, 8, 0, 0))
    manager.record_split(trip.trip_id, b.waypoint_id, timestamp=datetime(2026, 8, 14, 9, 0, 0))
    manager.record_split(trip.trip_id, c.waypoint_id, timestamp=datetime(2026, 8, 14, 10, 0, 0))

    leg_ab = context.waypoints.distance_and_bearing(a.waypoint_id, b.waypoint_id)[0]
    leg_bc = context.waypoints.distance_and_bearing(b.waypoint_id, c.waypoint_id)[0]
    expected = (leg_ab + leg_bc) / 2.0  # 2 hours total elapsed
    assert manager.average_speed_kmh(trip.trip_id) == pytest.approx(expected, abs=0.01)


def test_average_speed_kmh_none_with_no_legs(isolated_paths):
    manager = _make_manager()
    trip = manager.add_trip(expedition_id="exp1", name="X")
    assert manager.average_speed_kmh(trip.trip_id) is None


# ----------------------------------------------------------------------
# Photos
# ----------------------------------------------------------------------

def test_add_photo_copies_file_and_records_filename(isolated_paths, tmp_path):
    context = _make_context()
    context.config.set("trips.photo_root_path", str(tmp_path / "photos"))
    manager = _make_manager(context)
    trip = manager.add_trip(expedition_id="exp1", name="X")

    source = tmp_path / "camp_view.jpg"
    source.write_bytes(b"fake image bytes")

    filename = manager.add_photo(trip.trip_id, source)

    assert filename == "camp_view.jpg"
    assert trip.photo_filenames == ["camp_view.jpg"]
    stored_path = manager.photo_path(trip.trip_id, "camp_view.jpg")
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"fake image bytes"
    # The original source file is untouched — add_photo copies, not moves.
    assert source.exists()


def test_add_photo_unknown_trip_raises(isolated_paths, tmp_path):
    context = _make_context()
    context.config.set("trips.photo_root_path", str(tmp_path / "photos"))
    manager = _make_manager(context)
    source = tmp_path / "x.jpg"
    source.write_bytes(b"x")
    with pytest.raises(ValueError):
        manager.add_photo("does-not-exist", source)


def test_remove_photo_deletes_stored_copy_and_unlists_it(isolated_paths, tmp_path):
    context = _make_context()
    context.config.set("trips.photo_root_path", str(tmp_path / "photos"))
    manager = _make_manager(context)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    source = tmp_path / "camp_view.jpg"
    source.write_bytes(b"fake image bytes")
    manager.add_photo(trip.trip_id, source)

    stored_path = manager.photo_path(trip.trip_id, "camp_view.jpg")
    manager.remove_photo(trip.trip_id, "camp_view.jpg")

    assert trip.photo_filenames == []
    assert not stored_path.exists()


def test_remove_photo_not_in_list_is_a_no_op(isolated_paths, tmp_path):
    context = _make_context()
    context.config.set("trips.photo_root_path", str(tmp_path / "photos"))
    manager = _make_manager(context)
    trip = manager.add_trip(expedition_id="exp1", name="X")

    manager.remove_photo(trip.trip_id, "does-not-exist.jpg")  # must not raise
    assert trip.photo_filenames == []


def test_photos_persist_across_a_fresh_load(isolated_paths, tmp_path):
    context = _make_context()
    context.config.set("trips.photo_root_path", str(tmp_path / "photos"))
    manager = _make_manager(context)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    source = tmp_path / "camp_view.jpg"
    source.write_bytes(b"fake image bytes")
    manager.add_photo(trip.trip_id, source)

    reloaded = TripManager(context)
    reloaded_trip = reloaded.get_trip(trip.trip_id)
    assert reloaded_trip.photo_filenames == ["camp_view.jpg"]


def test_splits_persist_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    trip = manager.add_trip(expedition_id="exp1", name="X")
    manager.record_split(trip.trip_id, a.waypoint_id, timestamp=datetime(2026, 8, 14, 8, 0, 0))

    reloaded = TripManager(context)
    reloaded_trip = reloaded.get_trip(trip.trip_id)
    assert len(reloaded_trip.splits) == 1
    assert reloaded_trip.splits[0].waypoint_id == a.waypoint_id


def test_reload_picks_up_changes_written_by_another_process(isolated_paths):
    """docs/ROADMAP.md milestone v0.19 — reload() lets an auto-import's changes show up without an app restart."""
    context = _make_context()
    manager = _make_manager(context)
    manager.add_trip(expedition_id="exp1", name="Original")
    assert len(manager.all_trips()) == 1

    other = TripManager(context)
    other.add_trip(expedition_id="exp1", name="Added Elsewhere")

    assert len(manager.all_trips()) == 1  # stale in-memory state
    manager.reload()
    assert len(manager.all_trips()) == 2
