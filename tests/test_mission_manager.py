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

from datetime import datetime, timedelta

import pytest

import core.expedition_manager as expedition_manager_module
import core.mission_manager as mission_manager_module
import core.task_manager as task_manager_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.mission_manager import MissionManager
from core.task_manager import TaskManager
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
    monkeypatch.setattr(task_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(task_manager_module, "_TASKS_FILE", data_dir / "tasks.json")


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.waypoints = WaypointManager(context)
    context.expeditions = ExpeditionManager(context)
    context.trips = TripManager(context)
    context.missions = MissionManager(context)
    return context


def _make_context_with_tasks() -> AppContext:
    """check_for_auto_assignment()'s "stale task" rule needs context.tasks
    — a separate helper (not folded into _make_context()) since most
    existing tests here have no need for a TaskManager at all."""
    context = _make_context()
    context.tasks = TaskManager(context)
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


# ----------------------------------------------------------------------
# task_done (computed live from a linked Task's `done` flag)
# ----------------------------------------------------------------------

def test_task_done_progress_reflects_incomplete_task(isolated_paths):
    context = _make_context_with_tasks()
    task = context.tasks.add_task(project_id="p1", title="Wire the garage")
    mission = context.missions.add_mission(name="Finally Finish: Wire the garage", task_id=task.task_id)
    context.missions.add_objective(mission.mission_id, 'Complete "Wire the garage"', "task_done", 1.0)

    assert context.missions.objective_progress(mission.mission_id, 0) == 0.0
    assert context.missions.is_objective_complete(mission.mission_id, 0) is False


def test_task_done_progress_reflects_completed_task(isolated_paths):
    context = _make_context_with_tasks()
    task = context.tasks.add_task(project_id="p1", title="Wire the garage")
    context.tasks.toggle_done(task.task_id)
    mission = context.missions.add_mission(name="Finally Finish: Wire the garage", task_id=task.task_id)
    context.missions.add_objective(mission.mission_id, 'Complete "Wire the garage"', "task_done", 1.0)

    assert context.missions.objective_progress(mission.mission_id, 0) == 1.0
    assert context.missions.is_objective_complete(mission.mission_id, 0) is True


def test_task_done_zero_when_mission_has_no_task(isolated_paths):
    context = _make_context_with_tasks()
    mission = context.missions.add_mission(name="General Goal")
    context.missions.add_objective(mission.mission_id, "Complete something", "task_done", 1.0)

    assert context.missions.objective_progress(mission.mission_id, 0) == 0.0


def test_task_done_zero_when_no_task_manager_available(isolated_paths):
    context = _make_context()  # no context.tasks
    mission = context.missions.add_mission(name="General Goal", task_id="nonexistent")
    context.missions.add_objective(mission.mission_id, "Complete something", "task_done", 1.0)

    assert context.missions.objective_progress(mission.mission_id, 0) == 0.0


# ----------------------------------------------------------------------
# assigned_by / task_id persistence round trip
# ----------------------------------------------------------------------

def test_assigned_by_and_task_id_persist_across_reload(isolated_paths):
    context = _make_context_with_tasks()
    task = context.tasks.add_task(project_id="p1", title="Wire the garage")
    context.missions.add_mission(name="MIA's Pick", task_id=task.task_id, assigned_by="mia")

    reloaded_context = _make_context_with_tasks()
    mission = reloaded_context.missions.all_missions()[0]
    assert mission.assigned_by == "mia"
    assert mission.task_id == task.task_id


def test_add_mission_defaults_assigned_by_to_user(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Self-Chosen Goal")
    assert mission.assigned_by == "user"
    assert mission.task_id is None


# ----------------------------------------------------------------------
# check_for_auto_assignment — idle rule
# ----------------------------------------------------------------------

def test_idle_rule_assigns_a_template_mission_when_no_missions_exist_at_all(isolated_paths):
    context = _make_context()
    mission = context.missions.check_for_auto_assignment()

    assert mission is not None
    assert mission.assigned_by == "mia"
    assert mission.status == "active"
    assert len(mission.objectives) >= 1
    assert context.missions.all_missions() == [mission]


def test_idle_rule_does_nothing_when_an_active_mission_already_exists(isolated_paths):
    context = _make_context()
    context.missions.add_mission(name="My Own Goal")

    assert context.missions.check_for_auto_assignment() is None
    assert len(context.missions.all_missions()) == 1


def test_idle_rule_fires_once_active_mission_is_abandoned(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="My Own Goal")
    context.missions.update_mission(mission.mission_id, status="abandoned")

    auto_mission = context.missions.check_for_auto_assignment()
    assert auto_mission is not None
    assert auto_mission.assigned_by == "mia"


def test_idle_rule_does_not_refire_within_the_idle_window(isolated_paths):
    context = _make_context()
    first = context.missions.check_for_auto_assignment()
    context.missions.update_mission(first.mission_id, status="abandoned")

    # Still well within _AUTO_ASSIGN_IDLE_DAYS of `first`'s created_at —
    # no second mission should be assigned yet.
    assert context.missions.check_for_auto_assignment() is None
    assert len(context.missions.all_missions()) == 1


def test_idle_rule_refires_after_the_idle_window_elapses(isolated_paths, monkeypatch):
    context = _make_context()
    first = context.missions.check_for_auto_assignment()
    context.missions.update_mission(first.mission_id, status="abandoned")

    real_datetime = mission_manager_module.datetime
    future = real_datetime.now() + timedelta(days=mission_manager_module._AUTO_ASSIGN_IDLE_DAYS + 1)

    class _FrozenDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return future

    monkeypatch.setattr(mission_manager_module, "datetime", _FrozenDatetime)

    second = context.missions.check_for_auto_assignment()
    assert second is not None
    assert second.mission_id != first.mission_id


def test_idle_rule_cycles_through_templates_without_immediate_repeats(isolated_paths):
    context = _make_context()
    seen_names = set()
    for _ in range(len(mission_manager_module._AUTO_MISSION_TEMPLATES)):
        mission = context.missions.check_for_auto_assignment()
        assert mission.name not in seen_names
        seen_names.add(mission.name)
        context.missions.update_mission(mission.mission_id, status="abandoned")
        # Bypass the idle window for this cycling test — jump each
        # mission's created_at far into the past so the next call's
        # "how long since the last mia-assigned mission" check always
        # passes, isolating just the "don't repeat a name" behavior.
        mission.created_at = "2000-01-01T00:00:00"


# ----------------------------------------------------------------------
# check_for_auto_assignment — stale task rule
# ----------------------------------------------------------------------

def test_stale_task_rule_wraps_the_least_recently_updated_incomplete_task(isolated_paths):
    context = _make_context_with_tasks()
    # Keep this one active — the idle rule's own guard skips its check
    # entirely while any mission is active, isolating this test to just
    # the stale-task rule's own behavior.
    context.missions.add_mission(name="Existing Goal")

    old_task = context.tasks.add_task(project_id="p1", title="Old Task")
    # update_task() always re-stamps updated_at to now() regardless of
    # what fields were passed (core/task_manager.py's own update_task())
    # — mutate the dataclass field directly to backdate it for this test.
    old_task.updated_at = "2000-01-01T00:00:00"
    recent_task = context.tasks.add_task(project_id="p1", title="Recent Task")

    mission = context.missions.check_for_auto_assignment()

    assert mission is not None
    assert mission.task_id == old_task.task_id
    assert mission.assigned_by == "mia"
    assert mission.objectives[0].metric_type == "task_done"


def test_stale_task_rule_skips_a_task_updated_recently(isolated_paths):
    context = _make_context_with_tasks()
    # Keep this one active — the idle rule's own guard skips its check
    # entirely while any mission is active, isolating this test to just
    # the stale-task rule's own behavior.
    context.missions.add_mission(name="Existing Goal")
    context.tasks.add_task(project_id="p1", title="Fresh Task")

    assert context.missions.check_for_auto_assignment() is None


def test_stale_task_rule_skips_a_task_already_wrapped_by_a_mission(isolated_paths):
    context = _make_context_with_tasks()
    # Keep this one active — the idle rule's own guard skips its check
    # entirely while any mission is active, isolating this test to just
    # the stale-task rule's own behavior.
    context.missions.add_mission(name="Existing Goal")

    task = context.tasks.add_task(project_id="p1", title="Old Task")
    task.updated_at = "2000-01-01T00:00:00"
    context.missions.add_mission(name="Already Wrapped", task_id=task.task_id, assigned_by="mia")

    assert context.missions.check_for_auto_assignment() is None


def test_stale_task_rule_skips_a_task_already_marked_done(isolated_paths):
    context = _make_context_with_tasks()
    # Keep this one active — the idle rule's own guard skips its check
    # entirely while any mission is active, isolating this test to just
    # the stale-task rule's own behavior.
    context.missions.add_mission(name="Existing Goal")

    task = context.tasks.add_task(project_id="p1", title="Old Done Task")
    context.tasks.toggle_done(task.task_id)
    task.updated_at = "2000-01-01T00:00:00"

    assert context.missions.check_for_auto_assignment() is None


def test_stale_task_rule_not_reached_when_idle_rule_already_fired(isolated_paths):
    """The idle rule takes priority — with no active mission and no
    prior mia-assigned mission, it fires first even if a stale task also
    qualifies, and only one Mission is created per call."""
    context = _make_context_with_tasks()
    task = context.tasks.add_task(project_id="p1", title="Old Task")
    task.updated_at = "2000-01-01T00:00:00"

    mission = context.missions.check_for_auto_assignment()
    assert mission.task_id is None  # the idle-rule template mission, not the stale-task one
