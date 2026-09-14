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

import core.config_manager as config_manager_module
import core.expedition_manager as expedition_manager_module
import core.kitchen_manager as kitchen_manager_module
import core.mission_manager as mission_manager_module
import core.skill_manager as skill_manager_module
import core.task_manager as task_manager_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.gamification import SkillWeight
from core.kitchen_manager import KitchenManager
from core.mission_manager import MissionManager
from core.profile_manager import ProfileManager
from core.skill_manager import SkillManager
from core.task_manager import TaskManager
from core.trip_manager import TripManager
from core.waypoint_manager import WaypointManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
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
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    monkeypatch.setattr(kitchen_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(kitchen_manager_module, "_RECIPES_FILE", data_dir / "kitchen_recipes.json")
    monkeypatch.setattr(kitchen_manager_module, "_PANTRY_FILE", data_dir / "kitchen_pantry.json")
    monkeypatch.setattr(kitchen_manager_module, "_GROCERY_LIST_FILE", data_dir / "kitchen_grocery_list.json")
    monkeypatch.setattr(kitchen_manager_module, "_MEAL_LOG_FILE", data_dir / "kitchen_meal_log.json")


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


def _make_context_with_profiles() -> AppContext:
    """_credit_mission_rewards() needs context.profiles — separate
    helper for the same reason _make_context_with_tasks() is, most
    existing tests here have no need for a ProfileManager at all."""
    context = _make_context()
    context.profiles = ProfileManager(context)
    return context


def _make_context_with_profiles_and_skills(skill_ids: list[str]) -> AppContext:
    """"My Hero's Path" skill_rewards tests need both context.profiles
    and a context.skills with real definitions for skill_ids (a
    skill_reward pointing to an unknown skill_id is silently dropped
    by SkillManager.add_skill_xp() by design, so a test proving XP
    actually lands needs the skill defined first)."""
    import json

    context = _make_context_with_profiles()
    skill_manager_module._DATA_DIR.mkdir(parents=True, exist_ok=True)
    skill_manager_module._SKILL_DEFINITIONS_FILE.write_text(
        json.dumps({"skills": [{"skill_id": sid, "name": sid, "category": "Test"} for sid in skill_ids]})
    )
    context.skills = SkillManager(context)
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


def test_add_mission_can_link_to_a_maintenance_task(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Inspect: Pump Filter", maintenance_task_id="task123")
    assert mission.maintenance_task_id == "task123"
    assert context.missions.missions_for_maintenance_task("task123") == [mission]
    assert context.missions.missions_for_maintenance_task("nonexistent") == []


def test_maintenance_task_id_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    context.missions.add_mission(name="Inspect: Pump Filter", maintenance_task_id="task123")

    reloaded = MissionManager(context)
    assert reloaded.all_missions()[0].maintenance_task_id == "task123"


def test_add_mission_without_maintenance_task_id_defaults_to_none(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    assert mission.maintenance_task_id is None


def test_add_mission_can_link_to_a_maintenance_asset(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Clean Out the Old House", maintenance_asset_id="asset123")
    assert mission.maintenance_asset_id == "asset123"
    assert context.missions.missions_for_maintenance_asset("asset123") == [mission]
    assert context.missions.missions_for_maintenance_asset("nonexistent") == []


def test_maintenance_asset_id_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    context.missions.add_mission(name="Clean Out the Old House", maintenance_asset_id="asset123")

    reloaded = MissionManager(context)
    assert reloaded.all_missions()[0].maintenance_asset_id == "asset123"


def test_add_mission_without_maintenance_asset_id_defaults_to_none(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    assert mission.maintenance_asset_id is None


def test_add_mission_can_set_recurring_fields(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(
        name="Push-ups", recurring_template_id="tmpl1", recurring_kind="daily", occurrence_key="2026-09-13",
    )
    assert mission.recurring_template_id == "tmpl1"
    assert mission.recurring_kind == "daily"
    assert mission.occurrence_key == "2026-09-13"


def test_recurring_fields_persist_across_a_fresh_load(isolated_paths):
    context = _make_context()
    context.missions.add_mission(
        name="Push-ups", recurring_template_id="tmpl1", recurring_kind="daily", occurrence_key="2026-09-13",
    )

    reloaded = MissionManager(context)
    mission = reloaded.all_missions()[0]
    assert mission.recurring_template_id == "tmpl1"
    assert mission.recurring_kind == "daily"
    assert mission.occurrence_key == "2026-09-13"


def test_add_mission_without_recurring_fields_defaults_to_none(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Master Angler")
    assert mission.recurring_template_id is None
    assert mission.recurring_kind is None
    assert mission.occurrence_key is None


def test_recurring_fields_settable_via_update_mission(isolated_paths):
    """Needed for retroactively linking an already-existing Mission to
    a template created afterward (see core/recurring_mission_manager.py)."""
    context = _make_context()
    mission = context.missions.add_mission(name="Push-ups")
    context.missions.update_mission(
        mission.mission_id, recurring_template_id="tmpl1", recurring_kind="daily", occurrence_key="2026-09-13",
    )
    updated = context.missions.get_mission(mission.mission_id)
    assert updated.recurring_template_id == "tmpl1"
    assert updated.recurring_kind == "daily"
    assert updated.occurrence_key == "2026-09-13"


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


def test_completing_a_mission_credits_xp_and_credits_to_active_profile(isolated_paths):
    context = _make_context_with_profiles()
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="Master Angler", reward_xp=160, reward_credits=25)

    context.missions.update_mission(mission.mission_id, status="completed")

    reloaded = context.profiles.list_profiles()[0]
    assert reloaded.total_xp == 160
    assert reloaded.total_credits == 25


def test_completing_a_mission_with_no_rewards_credits_nothing(isolated_paths):
    context = _make_context_with_profiles()
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="X")

    context.missions.update_mission(mission.mission_id, status="completed")

    reloaded = context.profiles.list_profiles()[0]
    assert reloaded.total_xp == 0
    assert reloaded.total_credits == 0


def test_completing_a_mission_with_no_active_profile_does_not_crash(isolated_paths):
    context = _make_context_with_profiles()
    mission = context.missions.add_mission(name="Master Angler", reward_xp=160, reward_credits=25)
    context.missions.update_mission(mission.mission_id, status="completed")  # should not raise


def test_completing_a_mission_auto_attributes_profile_id(isolated_paths):
    """Per-profile rewards (2026-09-14) — a Mission with no explicit
    owner becomes whoever's real accomplishment completed it."""
    context = _make_context_with_profiles()
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="Master Angler")

    context.missions.update_mission(mission.mission_id, status="completed")

    assert context.missions.get_mission(mission.mission_id).profile_id == profile.profile_id


def test_completing_a_mission_with_no_active_profile_leaves_profile_id_none(isolated_paths):
    context = _make_context_with_profiles()
    mission = context.missions.add_mission(name="Master Angler")

    context.missions.update_mission(mission.mission_id, status="completed")

    assert context.missions.get_mission(mission.mission_id).profile_id is None


def test_mission_created_with_explicit_profile_id_keeps_it_through_completion(isolated_paths):
    """Forward-planning ("assign this Mission to Faith") — explicit
    assignment at creation is never overwritten by auto-attribution."""
    context = _make_context_with_profiles()
    zac = context.profiles.create_profile(name="Zac", make_active=True)
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    mission = context.missions.add_mission(name="Faith's mission", profile_id=faith.profile_id)

    context.missions.update_mission(mission.mission_id, status="completed")  # completed while Zac is active

    assert context.missions.get_mission(mission.mission_id).profile_id == faith.profile_id


def test_recompleting_a_mission_does_not_reassign_profile_id(isolated_paths):
    context = _make_context_with_profiles()
    zac = context.profiles.create_profile(name="Zac", make_active=True)
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.update_mission(mission.mission_id, status="completed")  # attributed to Zac

    context.profiles.set_active_profile(faith.profile_id)
    context.missions.update_mission(mission.mission_id, status="active")
    context.missions.update_mission(mission.mission_id, status="completed")  # re-completed as Faith

    assert context.missions.get_mission(mission.mission_id).profile_id == zac.profile_id


def test_recompleting_a_mission_does_not_double_credit(isolated_paths):
    context = _make_context_with_profiles()
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="Master Angler", reward_xp=160, reward_credits=25)
    context.missions.update_mission(mission.mission_id, status="completed")
    context.missions.update_mission(mission.mission_id, status="completed")

    reloaded = context.profiles.list_profiles()[0]
    assert reloaded.total_xp == 160
    assert reloaded.total_credits == 25


# ----------------------------------------------------------------------
# "mission.completed" event — Mission Pathways (2026-09-11)
# ----------------------------------------------------------------------

def test_completing_a_mission_publishes_mission_completed(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    received = []
    context.events.subscribe("mission.completed", lambda **kwargs: received.append(kwargs))

    context.missions.update_mission(mission.mission_id, status="completed")

    assert received == [{"mission_id": mission.mission_id}]


def test_recompleting_a_mission_does_not_republish_mission_completed(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    received = []
    context.events.subscribe("mission.completed", lambda **kwargs: received.append(kwargs))

    context.missions.update_mission(mission.mission_id, status="completed")
    context.missions.update_mission(mission.mission_id, status="completed")

    assert len(received) == 1


def test_other_field_changes_do_not_publish_mission_completed(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    received = []
    context.events.subscribe("mission.completed", lambda **kwargs: received.append(kwargs))

    context.missions.update_mission(mission.mission_id, name="Renamed")

    assert received == []


# ----------------------------------------------------------------------
# abandon_reason / "mission.abandoned" event — mission failure/struggle
# signal (2026-09-11)
# ----------------------------------------------------------------------

def test_abandon_reason_defaults_to_empty_string(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")

    assert mission.abandon_reason == ""


def test_abandon_reason_round_trips_through_to_dict_from_dict(isolated_paths):
    from core.mission_manager import Mission

    mission = Mission(mission_id="m1", name="X", status="abandoned", abandon_reason="too_hard")

    reloaded = Mission.from_dict(mission.to_dict())

    assert reloaded.abandon_reason == "too_hard"


def test_old_missions_without_abandon_reason_deserialize_fine(isolated_paths):
    from core.mission_manager import Mission

    data = {"mission_id": "m1", "name": "X", "status": "abandoned"}  # no "abandon_reason" key at all

    reloaded = Mission.from_dict(data)

    assert reloaded.abandon_reason == ""


def test_abandoning_a_mission_publishes_mission_abandoned(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    received = []
    context.events.subscribe("mission.abandoned", lambda **kwargs: received.append(kwargs))

    context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason="too_hard")

    assert received == [{"mission_id": mission.mission_id, "reason": "too_hard"}]


def test_reabandoning_a_mission_does_not_republish_mission_abandoned(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    received = []
    context.events.subscribe("mission.abandoned", lambda **kwargs: received.append(kwargs))

    context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason="too_hard")
    context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason="too_hard")

    assert len(received) == 1


def test_reactivating_then_reabandoning_refires_mission_abandoned(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    received = []
    context.events.subscribe("mission.abandoned", lambda **kwargs: received.append(kwargs))

    context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason="too_hard")
    context.missions.update_mission(mission.mission_id, status="active")
    context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason="not_interested")

    assert received == [
        {"mission_id": mission.mission_id, "reason": "too_hard"},
        {"mission_id": mission.mission_id, "reason": "not_interested"},
    ]


def test_other_field_changes_do_not_publish_mission_abandoned(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    received = []
    context.events.subscribe("mission.abandoned", lambda **kwargs: received.append(kwargs))

    context.missions.update_mission(mission.mission_id, name="Renamed")

    assert received == []


def test_unrecognized_abandon_reason_is_stored_as_is(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")

    updated = context.missions.update_mission(mission.mission_id, status="abandoned", abandon_reason="weather")

    assert updated.abandon_reason == "weather"


# ----------------------------------------------------------------------
# skill_rewards — "My Hero's Path" (2026-09-11)
# ----------------------------------------------------------------------

def test_completing_a_mission_credits_skill_rewards(isolated_paths):
    context = _make_context_with_profiles_and_skills(["aquaponics", "fabrication"])
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(
        name="Aquaponics Pilot",
        skill_rewards=[SkillWeight("aquaponics", 120), SkillWeight("fabrication", 40)],
    )

    context.missions.update_mission(mission.mission_id, status="completed")

    active = context.profiles.get_active_profile()
    assert context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 120
    assert context.skills.get_progress(active.profile_id, "fabrication").total_xp == 40


def test_reactivating_and_recompleting_a_mission_does_not_double_credit(isolated_paths):
    """Regression test for a real, reachable bug found while building
    the "Manage Skills" UI: gui/add_edit_mission_dialog.py's own status
    combo lets a completed Mission go back to "active" — without
    Mission.rewards_credited, re-completing it would re-grant
    reward_xp/reward_credits/skill_rewards every time."""
    context = _make_context_with_profiles_and_skills(["aquaponics"])
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(
        name="Aquaponics Pilot", reward_xp=50, reward_credits=10,
        skill_rewards=[SkillWeight("aquaponics", 120)],
    )

    context.missions.update_mission(mission.mission_id, status="completed")
    context.missions.update_mission(mission.mission_id, status="active")
    context.missions.update_mission(mission.mission_id, status="completed")

    active = context.profiles.get_active_profile()
    assert active.total_xp == 50  # not 100
    assert active.total_credits == 10  # not 20
    assert context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 120  # not 240


def test_rewards_credited_cannot_be_set_through_update_mission(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    with pytest.raises(ValueError):
        context.missions.update_mission(mission.mission_id, rewards_credited=True)


def test_rewards_credited_persists_across_a_fresh_load(isolated_paths):
    context = _make_context_with_profiles()
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="X", reward_xp=10)
    context.missions.update_mission(mission.mission_id, status="completed")

    reloaded = MissionManager(context)
    assert reloaded.all_missions()[0].rewards_credited is True


def test_new_mission_defaults_to_rewards_not_credited(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    assert mission.rewards_credited is False


def test_add_skill_reward_appends_and_does_not_credit_before_completion(isolated_paths):
    context = _make_context_with_profiles_and_skills(["aquaponics"])
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="X")

    updated = context.missions.add_skill_reward(mission.mission_id, "aquaponics", 30)

    assert updated.skill_rewards == [SkillWeight("aquaponics", 30)]
    active = context.profiles.get_active_profile()
    assert context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 0


def test_add_skill_reward_credits_immediately_after_completion(isolated_paths):
    context = _make_context_with_profiles_and_skills(["aquaponics", "fabrication"])
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="X", skill_rewards=[SkillWeight("aquaponics", 120)])
    context.missions.update_mission(mission.mission_id, status="completed")

    context.missions.add_skill_reward(mission.mission_id, "fabrication", 40)

    active = context.profiles.get_active_profile()
    assert context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 120  # unchanged, no double-credit
    assert context.skills.get_progress(active.profile_id, "fabrication").total_xp == 40  # the new one, credited now


def test_add_skill_reward_unknown_mission_raises(isolated_paths):
    context = _make_context()
    with pytest.raises(ValueError):
        context.missions.add_skill_reward("nonexistent", "aquaponics", 10)


def test_completing_a_mission_with_no_skill_rewards_credits_no_skills(isolated_paths):
    context = _make_context_with_profiles_and_skills(["aquaponics"])
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="X")

    context.missions.update_mission(mission.mission_id, status="completed")

    active = context.profiles.get_active_profile()
    assert context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 0


def test_completing_a_mission_with_skill_rewards_and_no_skills_service_does_not_crash(isolated_paths):
    context = _make_context_with_profiles()
    context.profiles.create_profile(name="Alex", make_active=True)
    mission = context.missions.add_mission(name="X", skill_rewards=[SkillWeight("aquaponics", 120)])

    context.missions.update_mission(mission.mission_id, status="completed")  # should not raise


def test_mission_skill_rewards_persist_across_a_fresh_load(isolated_paths):
    context = _make_context_with_profiles_and_skills(["aquaponics"])
    context.missions.add_mission(name="Aquaponics Pilot", skill_rewards=[SkillWeight("aquaponics", 120)])

    reloaded = MissionManager(context)
    mission = reloaded.all_missions()[0]
    assert mission.skill_rewards == [SkillWeight("aquaponics", 120)]


def test_mission_with_no_skill_rewards_deserializes_to_empty_list(isolated_paths):
    """Backward compatibility: old missions.json rows with no
    skill_rewards key at all must still deserialize cleanly."""
    import json

    mission_manager_module._DATA_DIR.mkdir(parents=True, exist_ok=True)
    mission_manager_module._MISSIONS_FILE.write_text(
        json.dumps([{"mission_id": "m1", "name": "Old Mission", "reward_xp": 50}])
    )
    context = _make_context()
    mission = context.missions.get_mission("m1")
    assert mission.skill_rewards == []


# ----------------------------------------------------------------------
# recipe_unlocks — "Recipe Unlocked" (2026-09-12)
# ----------------------------------------------------------------------

def test_completing_a_mission_unlocks_named_recipes(isolated_paths):
    context = _make_context()
    context.kitchen = KitchenManager(context)
    recipe = context.kitchen.add_recipe(name="Homemade Ramen", locked=True)
    mission = context.missions.add_mission(name="Ramen Quest", recipe_unlocks=[recipe.recipe_id])

    context.missions.update_mission(mission.mission_id, status="completed")

    assert context.kitchen.get_recipe(recipe.recipe_id).locked is False


def test_completing_a_mission_with_recipe_unlocks_does_not_require_an_active_profile(isolated_paths):
    """Deliberately using plain _make_context() — no context.profiles
    at all — to prove recipe unlocking is independent of profile-XP
    crediting, unlike skill_rewards."""
    context = _make_context()
    context.kitchen = KitchenManager(context)
    recipe = context.kitchen.add_recipe(name="Homemade Ramen", locked=True)
    mission = context.missions.add_mission(name="Ramen Quest", recipe_unlocks=[recipe.recipe_id])

    context.missions.update_mission(mission.mission_id, status="completed")  # must not raise

    assert context.kitchen.get_recipe(recipe.recipe_id).locked is False


def test_completing_a_mission_with_no_recipe_unlocks_touches_no_recipes(isolated_paths):
    context = _make_context()
    context.kitchen = KitchenManager(context)
    recipe = context.kitchen.add_recipe(name="Homemade Ramen", locked=True)
    mission = context.missions.add_mission(name="X")

    context.missions.update_mission(mission.mission_id, status="completed")

    assert context.kitchen.get_recipe(recipe.recipe_id).locked is True


def test_completing_a_mission_with_recipe_unlocks_and_no_kitchen_service_does_not_crash(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Ramen Quest", recipe_unlocks=["some-recipe-id"])

    context.missions.update_mission(mission.mission_id, status="completed")  # must not raise


def test_mission_recipe_unlocks_persist_across_a_fresh_load(isolated_paths):
    context = _make_context()
    context.missions.add_mission(name="Ramen Quest", recipe_unlocks=["r1", "r2"])

    reloaded = MissionManager(context)
    mission = reloaded.all_missions()[0]
    assert mission.recipe_unlocks == ["r1", "r2"]


def test_mission_with_no_recipe_unlocks_deserializes_to_empty_list(isolated_paths):
    """Backward compatibility: old missions.json rows with no
    recipe_unlocks key at all must still deserialize cleanly."""
    import json

    mission_manager_module._DATA_DIR.mkdir(parents=True, exist_ok=True)
    mission_manager_module._MISSIONS_FILE.write_text(
        json.dumps([{"mission_id": "m1", "name": "Old Mission", "reward_xp": 50}])
    )
    context = _make_context()
    mission = context.missions.get_mission("m1")
    assert mission.recipe_unlocks == []


# ----------------------------------------------------------------------
# project_id — connective-infrastructure pass (2026-09-11)
# ----------------------------------------------------------------------

def test_add_mission_with_project_id_persists(isolated_paths):
    context = _make_context()
    added = context.missions.add_mission(name="Aquaponics Pilot", project_id="proj1")

    reloaded = MissionManager(context)
    assert reloaded.get_mission(added.mission_id).project_id == "proj1"


def test_add_mission_project_id_defaults_to_none(isolated_paths):
    context = _make_context()
    added = context.missions.add_mission(name="X")
    assert added.project_id is None


def test_update_mission_rejects_project_id(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="X")
    with pytest.raises(ValueError):
        context.missions.update_mission(mission.mission_id, project_id="different")


def test_mission_with_no_project_id_key_deserializes_to_none(isolated_paths):
    """Backward compatibility: old missions.json rows with no
    project_id key at all must still deserialize cleanly."""
    import json

    mission_manager_module._DATA_DIR.mkdir(parents=True, exist_ok=True)
    mission_manager_module._MISSIONS_FILE.write_text(
        json.dumps([{"mission_id": "m1", "name": "Old Mission"}])
    )
    context = _make_context()
    mission = context.missions.get_mission("m1")
    assert mission.project_id is None
    assert mission.skill_rewards == []


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


# ------------------------------------------------------------------
# Group quests (2026-09-14)
# ------------------------------------------------------------------

def test_new_mission_has_no_participants_by_default(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Solo Quest")
    assert mission.participant_profile_ids == []


def test_add_mission_with_real_participants(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Prepare the House for Fall", participant_profile_ids=["zac", "faith"])
    assert mission.participant_profile_ids == ["zac", "faith"]


def test_new_objective_has_no_assignee_by_default(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Prepare the House for Fall")
    context.missions.add_objective(mission.mission_id, "Clean garage", "tally", 1.0)
    assert context.missions.get_mission(mission.mission_id).objectives[0].assigned_profile_id is None


def test_add_objective_with_a_real_assignee(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Prepare the House for Fall")
    context.missions.add_objective(mission.mission_id, "Clean mower", "tally", 1.0, assigned_profile_id="zac")
    assert context.missions.get_mission(mission.mission_id).objectives[0].assigned_profile_id == "zac"


def test_participant_and_assignee_persist_across_a_fresh_load(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Prepare the House for Fall", participant_profile_ids=["zac", "faith"])
    context.missions.add_objective(mission.mission_id, "Clean mower", "tally", 1.0, assigned_profile_id="zac")

    reloaded = MissionManager(context)
    reloaded_mission = reloaded.get_mission(mission.mission_id)
    assert reloaded_mission.participant_profile_ids == ["zac", "faith"]
    assert reloaded_mission.objectives[0].assigned_profile_id == "zac"


def test_individual_objective_progress_counts_only_that_profiles_objectives(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Prepare the House for Fall", participant_profile_ids=["zac", "faith"])
    context.missions.add_objective(mission.mission_id, "Clean mower", "tally", 1.0, assigned_profile_id="zac")
    context.missions.add_objective(mission.mission_id, "Inspect equipment", "tally", 1.0, assigned_profile_id="zac")
    context.missions.add_objective(mission.mission_id, "Organize storage", "tally", 1.0, assigned_profile_id="faith")
    context.missions.add_objective(mission.mission_id, "Clean garage", "tally", 1.0)  # shared

    context.missions.increment_tally(mission.mission_id, 0)  # Zac's "Clean mower" done

    assert context.missions.individual_objective_progress(mission.mission_id, "zac") == (1, 2)
    assert context.missions.individual_objective_progress(mission.mission_id, "faith") == (0, 1)


def test_group_objective_progress_counts_every_objective(isolated_paths):
    context = _make_context()
    mission = context.missions.add_mission(name="Prepare the House for Fall", participant_profile_ids=["zac", "faith"])
    context.missions.add_objective(mission.mission_id, "Clean mower", "tally", 1.0, assigned_profile_id="zac")
    context.missions.add_objective(mission.mission_id, "Organize storage", "tally", 1.0, assigned_profile_id="faith")
    context.missions.add_objective(mission.mission_id, "Clean garage", "tally", 1.0)  # shared

    context.missions.increment_tally(mission.mission_id, 0)
    context.missions.increment_tally(mission.mission_id, 2)

    assert context.missions.group_objective_progress(mission.mission_id) == (2, 3)


def test_individual_objective_progress_unknown_mission_returns_zero(isolated_paths):
    context = _make_context()
    assert context.missions.individual_objective_progress("no-such-id", "zac") == (0, 0)


def test_group_objective_progress_unknown_mission_returns_zero(isolated_paths):
    context = _make_context()
    assert context.missions.group_objective_progress("no-such-id") == (0, 0)


def test_completing_a_group_mission_credits_every_real_participant(isolated_paths):
    """Group quests (2026-09-14) — "group rewards": every participant
    gets the same flat reward, not just whoever completed it."""
    context = _make_context_with_profiles()
    zac = context.profiles.create_profile(name="Zac", make_active=True)
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    mission = context.missions.add_mission(
        name="Prepare the House for Fall", reward_xp=100, reward_credits=20,
        participant_profile_ids=[zac.profile_id, faith.profile_id],
    )

    context.missions.update_mission(mission.mission_id, status="completed")  # completed while Zac active

    reloaded_zac = context.profiles.get_profile(zac.profile_id)
    reloaded_faith = context.profiles.get_profile(faith.profile_id)
    assert reloaded_zac.total_xp == 100
    assert reloaded_zac.total_credits == 20
    assert reloaded_faith.total_xp == 100
    assert reloaded_faith.total_credits == 20


def test_completing_a_solo_mission_still_only_credits_the_active_profile(isolated_paths):
    """No real participants (every ordinary Mission) keeps the old
    "just whoever's active" behavior, unchanged."""
    context = _make_context_with_profiles()
    zac = context.profiles.create_profile(name="Zac", make_active=True)
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    mission = context.missions.add_mission(name="Solo Quest", reward_xp=100)

    context.missions.update_mission(mission.mission_id, status="completed")

    assert context.profiles.get_profile(zac.profile_id).total_xp == 100
    assert context.profiles.get_profile(faith.profile_id).total_xp == 0
