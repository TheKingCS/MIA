"""
tests.test_rewards_manager
=============================

Unit tests for core.rewards_manager. Isolates every real manager's own
file constants into a tmp_path scratch area, same monkeypatch pattern
as tests/test_kitchen_manager.py's own isolated_paths.
"""

from __future__ import annotations

import pytest

import core.config_manager as config_manager_module
import core.data_logger_manager as data_logger_manager_module
import core.kitchen_manager as kitchen_manager_module
import core.maintenance_manager as maintenance_manager_module
import core.mission_manager as mission_manager_module
import core.notification_manager as notification_manager_module
import core.project_manager as project_manager_module
import core.workout_manager as workout_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager, Reading
from core.event_bus import EventBus
from core.kitchen_manager import KitchenManager
from core.maintenance_manager import MaintenanceManager
from core.mission_manager import MissionManager
from core.notification_manager import NotificationManager
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.rewards_manager import (
    CHALLENGE_CHAINS,
    HIDDEN_ACHIEVEMENTS,
    RewardsManager,
    all_tiers,
    combined_stat_value,
    format_multi_unlock_notification,
    highest_unlocked_tier,
    is_attributed_to,
    next_locked_tier,
    rarity_tally_for_unlocked,
    reward_progress_fraction,
    stat_id_for_tier,
    usage_deltas_by_reader,
)
from core.workout_manager import WorkoutManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(maintenance_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(maintenance_manager_module, "_MAINTENANCE_FILE", data_dir / "maintenance.json")
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(workout_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(workout_manager_module, "_EXERCISES_FILE", data_dir / "workout_exercises.json")
    monkeypatch.setattr(workout_manager_module, "_TEMPLATES_FILE", data_dir / "workout_templates.json")
    monkeypatch.setattr(workout_manager_module, "_SESSIONS_FILE", data_dir / "workout_sessions.json")
    monkeypatch.setattr(data_logger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(data_logger_manager_module, "_READINGS_FILE", data_dir / "data_logger_readings.json")
    monkeypatch.setattr(kitchen_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(kitchen_manager_module, "_RECIPES_FILE", data_dir / "kitchen_recipes.json")
    monkeypatch.setattr(kitchen_manager_module, "_PANTRY_FILE", data_dir / "kitchen_pantry.json")
    monkeypatch.setattr(kitchen_manager_module, "_GROCERY_LIST_FILE", data_dir / "kitchen_grocery_list.json")
    monkeypatch.setattr(kitchen_manager_module, "_MEAL_LOG_FILE", data_dir / "kitchen_meal_log.json")
    monkeypatch.setattr(project_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(project_manager_module, "_PROJECTS_FILE", data_dir / "projects.json")
    monkeypatch.setattr(notification_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(notification_manager_module, "_NOTIFICATIONS_FILE", data_dir / "notifications.json")


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.maintenance = MaintenanceManager(context)
    context.missions = MissionManager(context)
    context.workout = WorkoutManager(context)
    context.data_logger = DataLoggerManager(context)
    context.kitchen = KitchenManager(context)
    context.projects = ProjectManager(context)
    context.notifications = NotificationManager(context)
    context.rewards = RewardsManager(context)
    return context


def _detach_rewards_event_subscriptions(context: AppContext) -> None:
    """Real app behavior (2026-09-14 event-sourced groundwork) always
    has RewardsManager auto-scan on "activity.logged"/"mission.completed"
    — see core/rewards_manager.py's own docstring. Several tests below
    want to call scan_for_new_unlocks()/scan_for_new_hidden_achievements()
    explicitly and observe THEIR OWN return value/notification in
    isolation, which the real-time auto-trigger would otherwise beat
    them to (making the explicit call a correct-but-uninteresting
    no-op) — a pure test-isolation tool, not something real code ever
    does."""
    context.events.unsubscribe("activity.logged", context.rewards._on_activity_event)
    context.events.unsubscribe("mission.completed", context.rewards._on_activity_event)


# ------------------------------------------------------------------
# reward_progress_fraction
# ------------------------------------------------------------------

def test_reward_progress_fraction_partway():
    assert reward_progress_fraction(3.0, 10.0) == 0.3


def test_reward_progress_fraction_clamps_above_one():
    assert reward_progress_fraction(15.0, 10.0) == 1.0


def test_reward_progress_fraction_clamps_below_zero():
    assert reward_progress_fraction(-5.0, 10.0) == 0.0


def test_reward_progress_fraction_zero_threshold_reads_complete():
    assert reward_progress_fraction(0.0, 0.0) == 1.0


# ------------------------------------------------------------------
# is_attributed_to / usage_deltas_by_reader — pure logic
# ------------------------------------------------------------------

def test_is_attributed_to_none_owner_counts_for_any_profile():
    assert is_attributed_to(None, "alex") is True
    assert is_attributed_to(None, "sam") is True


def test_is_attributed_to_matching_owner():
    assert is_attributed_to("alex", "alex") is True


def test_is_attributed_to_non_matching_owner():
    assert is_attributed_to("alex", "sam") is False


def _reading(value, profile_id=None, timestamp="2026-01-01T00:00:00") -> Reading:
    return Reading(reading_id="r", series_id="s", value=value, timestamp=timestamp, profile_id=profile_id)


def test_usage_deltas_by_reader_no_baseline_first_reading_counts_from_true_zero():
    """A brand-new task's very first-ever reading still counts as real
    accumulated usage — the same "starts truly at zero" behavior every
    meter task in this app had before per-reader attribution existed."""
    readings = [_reading(10.0, "zac", "2026-01-01T00:00:00")]
    assert usage_deltas_by_reader(readings) == {"zac": 10.0}


def test_usage_deltas_by_reader_single_reader_reduces_to_flat_baseline_subtraction():
    readings = [_reading(207500.0, "zac", "2026-01-02T00:00:00")]
    assert usage_deltas_by_reader(readings, baseline=207000.0) == {"zac": 500.0}


def test_usage_deltas_by_reader_splits_a_shared_asset_by_real_contributor():
    """The vision doc's own worked example: "14 hrs total, Zac 13.2,
    Faith 0.8." """
    readings = [
        _reading(13.2, "zac", "2026-01-01T00:00:00"),
        _reading(14.0, "faith", "2026-01-02T00:00:00"),
    ]
    assert usage_deltas_by_reader(readings, baseline=0.0) == pytest.approx({"zac": 13.2, "faith": 0.8})


def test_usage_deltas_by_reader_sorts_by_timestamp_not_list_order():
    readings = [
        _reading(14.0, "faith", "2026-01-02T00:00:00"),
        _reading(13.2, "zac", "2026-01-01T00:00:00"),
    ]
    assert usage_deltas_by_reader(readings, baseline=0.0) == pytest.approx({"zac": 13.2, "faith": 0.8})


def test_usage_deltas_by_reader_unattributed_readings_bucket_under_none():
    readings = [_reading(5.0, None, "2026-01-01T00:00:00")]
    assert usage_deltas_by_reader(readings, baseline=0.0) == {None: 5.0}


def test_usage_deltas_by_reader_negative_delta_contributes_zero_not_negative():
    readings = [
        _reading(10.0, "zac", "2026-01-01T00:00:00"),
        _reading(4.0, "faith", "2026-01-02T00:00:00"),  # a data reset/correction
    ]
    assert usage_deltas_by_reader(readings, baseline=0.0) == {"zac": 10.0, "faith": 0.0}


def test_usage_deltas_by_reader_no_readings_no_baseline_is_empty():
    assert usage_deltas_by_reader([]) == {}


# ------------------------------------------------------------------
# Stat values — derived from real data
# ------------------------------------------------------------------

def test_engine_hours_logged_sums_across_assets(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    mower = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=mower.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 4.5)
    context.maintenance.log_reading(task.task_id, 7.0)  # latest reading wins, not a sum of readings

    other = context.maintenance.add_asset(name="Generator", category="Power Equipment")
    other_task = context.maintenance.add_task(asset_id=other.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(other_task.task_id, 2.0)

    assert context.rewards.stat_value("engine_hours_logged", profile.profile_id) == 9.0


def test_engine_hours_logged_ignores_unrelated_tasks(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Oil Change", trigger_type="calendar", interval_days=30)
    context.maintenance.log_reading(task.task_id, 999.0)

    assert context.rewards.stat_value("engine_hours_logged", profile.profile_id) == 0.0


def test_engine_hours_logged_zero_with_no_readings(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)

    assert context.rewards.stat_value("engine_hours_logged", profile.profile_id) == 0.0


def test_engine_hours_logged_counts_a_differently_titled_runtime_task(isolated_paths):
    """Generalization (2026-09-14): matched by trigger_type +
    tracks_lifetime_usage, not the literal title "Engine Hours" — a
    brand-new piece of equipment (a greenhouse pump, say) with its own
    runtime meter task automatically counts, no new code needed."""
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    pump = context.maintenance.add_asset(name="Greenhouse Pump", category="Garden/Plant")
    task = context.maintenance.add_task(
        asset_id=pump.asset_id, title="Pump Runtime", trigger_type="runtime", meter_unit="hours",
        tracks_lifetime_usage=True,
    )
    context.maintenance.log_reading(task.task_id, 12.0)

    assert context.rewards.stat_value("engine_hours_logged", profile.profile_id) == 12.0


def test_engine_hours_logged_ignores_runtime_task_not_marked_lifetime_usage(isolated_paths):
    """Same trigger_type and even the same conventional title, but not
    marked as the asset's real lifetime meter — must not count, same
    "service-interval task can share a trigger_type" reasoning as
    test_vehicle_miles_logged_ignores_other_mileage_tasks below."""
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours",
    )
    context.maintenance.log_reading(task.task_id, 50.0)

    assert context.rewards.stat_value("engine_hours_logged", profile.profile_id) == 0.0


def test_workout_hours_logged_sums_session_minutes(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    context.workout.add_session(template_id="", date_str="2026-09-01", duration_minutes=90)
    context.workout.add_session(template_id="", date_str="2026-09-02", duration_minutes=30)

    assert context.rewards.stat_value("workout_hours_logged", profile.profile_id) == 2.0


def test_missions_completed_counts_only_completed_status(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    m1 = context.missions.add_mission(name="Done one")
    context.missions.update_mission(m1.mission_id, status="completed")
    context.missions.add_mission(name="Still active")

    assert context.rewards.stat_value("missions_completed", profile.profile_id) == 1.0


def test_vehicle_miles_logged_sums_odometer_readings_across_assets(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    truck = context.maintenance.add_asset(name="Ridgeline", category="Vehicle")
    odometer = context.maintenance.add_task(asset_id=truck.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles", tracks_lifetime_usage=True)
    context.maintenance.log_reading(odometer.task_id, 40000.0)
    context.maintenance.log_reading(odometer.task_id, 40250.0)  # latest reading wins

    other = context.maintenance.add_asset(name="Second Car", category="Vehicle")
    other_odometer = context.maintenance.add_task(asset_id=other.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles", tracks_lifetime_usage=True)
    context.maintenance.log_reading(other_odometer.task_id, 1000.0)

    assert context.rewards.stat_value("vehicle_miles_logged", profile.profile_id) == 41250.0


def test_vehicle_miles_logged_ignores_other_mileage_tasks(isolated_paths):
    """Oil changes/tire rotations also log in miles, but they track
    miles-since-last-service, not the vehicle's real lifetime total —
    only the Odometer task itself represents that."""
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    truck = context.maintenance.add_asset(name="Ridgeline", category="Vehicle")
    oil_change = context.maintenance.add_task(asset_id=truck.asset_id, title="Oil & filter change", trigger_type="mileage", meter_unit="miles")
    context.maintenance.log_reading(oil_change.task_id, 3000.0)

    assert context.rewards.stat_value("vehicle_miles_logged", profile.profile_id) == 0.0


def test_vehicle_miles_logged_ignores_mileage_task_not_marked_lifetime_usage(isolated_paths):
    """Even a task literally titled "Odometer" doesn't count unless
    it's marked as the asset's real lifetime total — trigger_type alone
    can't disambiguate it from a same-unit service-interval task."""
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    truck = context.maintenance.add_asset(name="Ridgeline", category="Vehicle")
    odometer = context.maintenance.add_task(asset_id=truck.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles")
    context.maintenance.log_reading(odometer.task_id, 40000.0)

    assert context.rewards.stat_value("vehicle_miles_logged", profile.profile_id) == 0.0


def test_vehicle_miles_logged_counts_only_for_its_real_owner(isolated_paths):
    """A vehicle owned by one profile doesn't count toward a different
    profile's own stat — the real bug the user caught (Faith getting
    credit for Zac's truck mileage)."""
    context = _make_context()
    zac = context.profiles.create_profile(name="Zac")
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    truck = context.maintenance.add_asset(name="Ridgeline", category="Vehicle", owner_profile_id=zac.profile_id)
    odometer = context.maintenance.add_task(asset_id=truck.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles", tracks_lifetime_usage=True)
    context.maintenance.log_reading(odometer.task_id, 5000.0)

    assert context.rewards.stat_value("vehicle_miles_logged", zac.profile_id) == 5000.0
    assert context.rewards.stat_value("vehicle_miles_logged", faith.profile_id) == 0.0


def test_vehicle_miles_logged_shared_asset_still_splits_by_real_reader(isolated_paths):
    """An UNOWNED asset (the default) can still be driven by anyone,
    but usage attributes to whoever actually logged each reading, not
    automatically to everyone just because the asset itself has no
    single owner — "shared object does not mean shared progression"
    (the multi-user vision's own framing). See the next test for the
    real "shared, counts for everyone" case: a reading with no
    attribution at all."""
    context = _make_context()
    zac = context.profiles.create_profile(name="Zac")
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    truck = context.maintenance.add_asset(name="Family Van", category="Vehicle")  # no owner
    odometer = context.maintenance.add_task(asset_id=truck.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles", tracks_lifetime_usage=True)
    context.maintenance.log_reading(odometer.task_id, 3000.0)  # logged as Zac (active)

    assert context.rewards.stat_value("vehicle_miles_logged", zac.profile_id) == 3000.0
    assert context.rewards.stat_value("vehicle_miles_logged", faith.profile_id) == 0.0


def test_vehicle_miles_logged_unattributed_reading_counts_for_everyone(isolated_paths):
    """A reading logged with no active profile at all (or from before
    per-reading attribution existed) stays genuinely shared — the same
    convention every other per-profile field in this codebase uses."""
    context = _make_context()
    zac = context.profiles.create_profile(name="Zac", make_active=False)
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    truck = context.maintenance.add_asset(name="Family Van", category="Vehicle")
    odometer = context.maintenance.add_task(asset_id=truck.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles", tracks_lifetime_usage=True)
    context.maintenance.log_reading(odometer.task_id, 3000.0)  # no active profile

    assert context.rewards.stat_value("vehicle_miles_logged", zac.profile_id) == 3000.0
    assert context.rewards.stat_value("vehicle_miles_logged", faith.profile_id) == 3000.0


def test_vehicle_miles_logged_subtracts_real_baseline(isolated_paths):
    """A vehicle with real prior history (a real 207,000-mile odometer
    reading) starts reward tracking from that baseline, not its full
    lifetime total — the user's own "the zero from the truck would be
    like 207,000" ask."""
    context = _make_context()
    profile = context.profiles.create_profile(name="Zac")
    truck = context.maintenance.add_asset(name="Ridgeline", category="Vehicle")
    odometer = context.maintenance.add_task(
        asset_id=truck.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles",
        reward_baseline_value=207000.0, tracks_lifetime_usage=True,
    )
    context.maintenance.log_reading(odometer.task_id, 207000.0)
    assert context.rewards.stat_value("vehicle_miles_logged", profile.profile_id) == 0.0

    context.maintenance.log_reading(odometer.task_id, 207500.0)
    assert context.rewards.stat_value("vehicle_miles_logged", profile.profile_id) == 500.0


def test_workout_hours_logged_counts_only_for_the_active_profile_at_logging_time(isolated_paths):
    context = _make_context()
    zac = context.profiles.create_profile(name="Zac")
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    context.workout.add_session(template_id="", date_str="2026-09-01", duration_minutes=60)  # logged as Zac (active)

    context.profiles.set_active_profile(faith.profile_id)
    context.workout.add_session(template_id="", date_str="2026-09-02", duration_minutes=30)  # logged as Faith

    assert context.rewards.stat_value("workout_hours_logged", zac.profile_id) == 1.0
    assert context.rewards.stat_value("workout_hours_logged", faith.profile_id) == 0.5


def test_missions_completed_counts_only_for_whoever_completed_it(isolated_paths):
    context = _make_context()
    zac = context.profiles.create_profile(name="Zac")
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    m1 = context.missions.add_mission(name="Zac's mission")
    context.missions.update_mission(m1.mission_id, status="completed")  # completed as Zac (active)

    context.profiles.set_active_profile(faith.profile_id)
    m2 = context.missions.add_mission(name="Faith's mission")
    context.missions.update_mission(m2.mission_id, status="completed")  # completed as Faith

    assert context.rewards.stat_value("missions_completed", zac.profile_id) == 1.0
    assert context.rewards.stat_value("missions_completed", faith.profile_id) == 1.0


def test_missions_completed_group_quest_counts_for_every_participant(isolated_paths):
    """Group quests (2026-09-14) — a real party Mission counts toward
    EVERY participant, not just whoever completed it."""
    context = _make_context()
    zac = context.profiles.create_profile(name="Zac")
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    mission = context.missions.add_mission(
        name="Prepare the House for Fall", participant_profile_ids=[zac.profile_id, faith.profile_id],
    )
    context.missions.update_mission(mission.mission_id, status="completed")

    assert context.rewards.stat_value("missions_completed", zac.profile_id) == 1.0
    assert context.rewards.stat_value("missions_completed", faith.profile_id) == 1.0


def test_meals_cooked_counts_real_meal_log_entries(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    recipe = context.kitchen.add_recipe(name="Tacos")
    context.kitchen.log_meal(recipe.recipe_id, date_str="2026-09-01")
    context.kitchen.log_meal(recipe.recipe_id, date_str="2026-09-02")

    assert context.rewards.stat_value("meals_cooked", profile.profile_id) == 2.0


def test_projects_completed_counts_only_complete_status(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    done = context.projects.add_project(name="Deck rebuild")
    context.projects.update_project(done.project_id, status="Complete")
    context.projects.add_project(name="Still planning")

    assert context.rewards.stat_value("projects_completed", profile.profile_id) == 1.0


def test_all_stat_values_covers_every_definition(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    values = context.rewards.all_stat_values(profile.profile_id)
    assert set(values.keys()) == {
        "engine_hours_logged", "workout_hours_logged", "missions_completed",
        "vehicle_miles_logged", "meals_cooked", "projects_completed",
    }


# ------------------------------------------------------------------
# Unlocking
# ------------------------------------------------------------------

def test_scan_for_new_unlocks_unlocks_when_threshold_crossed(isolated_paths):
    context = _make_context()
    _detach_rewards_event_subscriptions(context)
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 10.0)

    newly_unlocked = context.rewards.scan_for_new_unlocks(profile.profile_id)

    reward_ids = {r.reward_id for r in newly_unlocked}
    assert "mowing_rookie" in reward_ids
    assert context.rewards.is_unlocked(profile.profile_id, "mowing_rookie") is True


def test_scan_for_new_unlocks_credits_every_tier_already_reached(isolated_paths):
    """Retroactive credit — a stat that's already well past several
    thresholds (e.g. an established profile's real history) unlocks
    every tier up to that value in one scan, not just the newest one.
    This is exactly what makes "add a profile, credit real past
    accomplishment" work correctly."""
    context = _make_context()
    _detach_rewards_event_subscriptions(context)
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 60.0)  # past rookie(10)/yard_worker(25)/ranger(50)

    newly_unlocked = context.rewards.scan_for_new_unlocks(profile.profile_id)

    reward_ids = {r.reward_id for r in newly_unlocked}
    assert reward_ids == {"mowing_rookie", "mowing_yard_worker", "mowing_ranger"}


# ------------------------------------------------------------------
# Notification restraint (2026-09-14) — one notification per scan,
# not one toast per unlock
# ------------------------------------------------------------------

def test_scan_for_new_unlocks_fires_one_notification_for_a_single_unlock(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 10.0)

    context.rewards.scan_for_new_unlocks(profile.profile_id)

    achievement_notifications = [n for n in context.notifications.list_all() if n.source == "achievements"]
    assert len(achievement_notifications) == 1
    assert "Lawn Rookie" in achievement_notifications[0].message


def test_scan_for_new_unlocks_batches_multiple_unlocks_into_one_notification(isolated_paths):
    context = _make_context()
    _detach_rewards_event_subscriptions(context)
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 60.0)  # past 3 tiers at once

    context.rewards.scan_for_new_unlocks(profile.profile_id)

    achievement_notifications = [n for n in context.notifications.list_all() if n.source == "achievements"]
    assert len(achievement_notifications) == 1
    notification = achievement_notifications[0]
    assert "3" in notification.title
    assert "Lawn Rookie" in notification.message
    assert "Yard Worker" in notification.message
    assert "Lawn Ranger" in notification.message


def test_scan_for_new_hidden_achievements_batches_multiple_into_one_notification(isolated_paths):
    context = _make_context()
    _detach_rewards_event_subscriptions(context)
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 250.0)  # crosses built_different(50) and renaissance(200)

    context.rewards.scan_for_new_hidden_achievements(profile.profile_id)

    achievement_notifications = [n for n in context.notifications.list_all() if n.source == "achievements"]
    assert len(achievement_notifications) == 1
    notification = achievement_notifications[0]
    assert "2" in notification.title
    assert "Built Different" in notification.message
    assert "Renaissance" in notification.message


def test_format_multi_unlock_notification_shape():
    title, message = format_multi_unlock_notification(["Lawn Rookie", "Yard Worker"], "rewards")
    assert title == "\U0001F389 2 rewards unlocked!"
    assert message == "Lawn Rookie, Yard Worker"


def test_scan_for_new_unlocks_is_idempotent(isolated_paths):
    context = _make_context()
    _detach_rewards_event_subscriptions(context)
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 10.0)

    first_scan = context.rewards.scan_for_new_unlocks(profile.profile_id)
    second_scan = context.rewards.scan_for_new_unlocks(profile.profile_id)

    assert len(first_scan) >= 1
    assert second_scan == []


def test_scan_for_new_unlocks_below_threshold_unlocks_nothing(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 1.5)

    assert context.rewards.scan_for_new_unlocks(profile.profile_id) == []
    assert context.rewards.is_unlocked(profile.profile_id, "mowing_rookie") is False


def test_scan_for_new_unlocks_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 10.0)
    context.rewards.scan_for_new_unlocks(profile.profile_id)

    reloaded_profiles = ProfileManager(context)
    reloaded = reloaded_profiles.get_profile(profile.profile_id)
    assert "mowing_rookie" in reloaded.unlocked_reward_ids


def test_scan_for_new_unlocks_with_no_profiles_manager_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.rewards = RewardsManager(context)
    assert context.rewards.scan_for_new_unlocks("does-not-exist") == []


def test_is_unlocked_false_for_unknown_profile(isolated_paths):
    context = _make_context()
    assert context.rewards.is_unlocked("does-not-exist", "mowing_rookie") is False


def test_unlocked_reward_ids_reflects_real_unlocks(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 10.0)
    context.rewards.scan_for_new_unlocks(profile.profile_id)

    assert "mowing_rookie" in context.rewards.unlocked_reward_ids(profile.profile_id)


# ------------------------------------------------------------------
# Character page support (2026-09-14) — collection + rarity tally
# ------------------------------------------------------------------

def test_all_unlocked_tiers_empty_before_any_unlock(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    assert context.rewards.all_unlocked_tiers(profile.profile_id) == []


def test_all_unlocked_tiers_flattens_across_chains(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 10.0)  # mowing_rookie
    for i in range(5):
        m = context.missions.add_mission(name=f"M{i}")
        context.missions.update_mission(m.mission_id, status="completed")  # missions_rookie at 5

    ids = {tier.reward_id for tier in context.rewards.all_unlocked_tiers(profile.profile_id)}
    assert "mowing_rookie" in ids
    assert "missions_rookie" in ids


def test_rarity_tally_all_zero_before_any_unlock(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    assert context.rewards.rarity_tally(profile.profile_id) == [0, 0, 0, 0, 0]


def test_rarity_tally_counts_tiers_and_hidden_achievements(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 60.0)  # mowing_rookie(0)/yard_worker(1)/ranger(2) + built_different hidden(3)

    tally = context.rewards.rarity_tally(profile.profile_id)
    assert tally[0] == 1  # mowing_rookie, Common
    assert tally[1] == 1  # mowing_yard_worker, Uncommon
    assert tally[2] == 1  # mowing_ranger, Rare
    assert tally[3] == 1  # built_different, Epic


def test_rarity_tally_for_unlocked_pure():
    tally = rarity_tally_for_unlocked({"mowing_rookie", "mission_that_does_not_exist"})
    assert tally == [1, 0, 0, 0, 0]


# ------------------------------------------------------------------
# combined_stat_value — pure logic
# ------------------------------------------------------------------

def test_combined_stat_value_sums_named_stats():
    values = {"engine_hours_logged": 30.0, "workout_hours_logged": 12.0, "missions_completed": 4.0}
    assert combined_stat_value(values, ("engine_hours_logged", "workout_hours_logged")) == 42.0


def test_combined_stat_value_single_stat():
    values = {"missions_completed": 7.0}
    assert combined_stat_value(values, ("missions_completed",)) == 7.0


def test_combined_stat_value_missing_stat_reads_as_zero():
    assert combined_stat_value({}, ("engine_hours_logged",)) == 0.0


# ------------------------------------------------------------------
# Hidden achievements — never exposed until unlocked
# ------------------------------------------------------------------

def test_unlocked_hidden_achievements_empty_before_any_unlock(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    assert context.rewards.unlocked_hidden_achievements(profile.profile_id) == []


def test_scan_for_new_hidden_achievements_unlocks_on_combined_threshold(isolated_paths):
    context = _make_context()
    _detach_rewards_event_subscriptions(context)
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 30.0)
    context.workout.add_session(template_id="", date_str="2026-09-01", duration_minutes=20 * 60)  # 20 hrs

    newly_unlocked = context.rewards.scan_for_new_hidden_achievements(profile.profile_id)

    ids = {a.achievement_id for a in newly_unlocked}
    assert "built_different" in ids
    assert context.rewards.is_unlocked(profile.profile_id, "built_different") is True


def test_scan_for_new_hidden_achievements_below_combined_threshold_unlocks_nothing(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 5.0)

    assert context.rewards.scan_for_new_hidden_achievements(profile.profile_id) == []


def test_scan_for_new_hidden_achievements_is_idempotent(isolated_paths):
    context = _make_context()
    _detach_rewards_event_subscriptions(context)
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 60.0)

    first_scan = context.rewards.scan_for_new_hidden_achievements(profile.profile_id)
    second_scan = context.rewards.scan_for_new_hidden_achievements(profile.profile_id)

    assert len(first_scan) >= 1
    assert second_scan == []


def test_unlocked_hidden_achievements_reflects_real_unlocks(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)
    context.maintenance.log_reading(task.task_id, 60.0)
    context.rewards.scan_for_new_hidden_achievements(profile.profile_id)

    names = {a.name for a in context.rewards.unlocked_hidden_achievements(profile.profile_id)}
    assert "Built Different" in names


def test_hidden_achievement_ids_are_unique():
    ids = [achievement.achievement_id for achievement in HIDDEN_ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


def test_hidden_achievement_ids_never_collide_with_chain_tier_ids():
    tier_ids = {tier.reward_id for tier in all_tiers()}
    hidden_ids = {achievement.achievement_id for achievement in HIDDEN_ACHIEVEMENTS}
    assert tier_ids.isdisjoint(hidden_ids)


# ------------------------------------------------------------------
# Event-sourced groundwork (2026-09-14) — real activity auto-unlocks
# without any explicit scan call, via the "activity.logged"/
# "mission.completed" subscriptions RewardsManager sets up at
# construction. Uses the REAL (attached) context, unlike the tests
# above that call _detach_rewards_event_subscriptions() to isolate the
# scan methods themselves.
# ------------------------------------------------------------------

def test_logging_a_maintenance_reading_auto_unlocks_without_an_explicit_scan(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)

    context.maintenance.log_reading(task.task_id, 10.0)  # no explicit scan call anywhere

    assert context.rewards.is_unlocked(profile.profile_id, "mowing_rookie") is True
    achievement_notifications = [n for n in context.notifications.list_all() if n.source == "achievements"]
    assert len(achievement_notifications) == 1


def test_logging_a_workout_session_auto_unlocks_without_an_explicit_scan(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")

    context.workout.add_session(template_id="", date_str="2026-09-01", duration_minutes=5 * 60)

    assert context.rewards.is_unlocked(profile.profile_id, "fitness_getting_started") is True


def test_logging_a_meal_auto_unlocks_without_an_explicit_scan(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    recipe = context.kitchen.add_recipe(name="Tacos")

    for i in range(10):
        context.kitchen.log_meal(recipe.recipe_id, date_str=f"2026-08-{i + 1:02d}")

    assert context.rewards.is_unlocked(profile.profile_id, "home_chef_apprentice") is True


def test_completing_a_project_auto_unlocks_without_an_explicit_scan(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    project = context.projects.add_project(name="Deck rebuild")

    context.projects.update_project(project.project_id, status="Complete")

    assert context.rewards.is_unlocked(profile.profile_id, "builder_first_build") is True


def test_completing_a_mission_auto_unlocks_without_an_explicit_scan(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    for i in range(5):
        mission = context.missions.add_mission(name=f"Mission {i}")
        context.missions.update_mission(mission.mission_id, status="completed")

    assert context.rewards.is_unlocked(profile.profile_id, "missions_rookie") is True


def test_activity_logged_event_with_no_active_profile_does_not_crash(isolated_paths):
    context = _make_context()
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours", tracks_lifetime_usage=True)

    context.maintenance.log_reading(task.task_id, 10.0)  # no profile ever created — must not raise


# ------------------------------------------------------------------
# Prestige emblems — derived, no separate unlock tracking
# ------------------------------------------------------------------

def test_prestige_rewards_for_profile_empty_at_tier_zero(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    assert context.rewards.prestige_rewards_for_profile(profile.profile_id) == []


def test_prestige_rewards_for_profile_one_entry_per_tier_newest_first(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    from core.leveling import XP_PER_PRESTIGE_CYCLE
    context.profiles.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)
    context.profiles.prestige(profile.profile_id)
    context.profiles.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)
    context.profiles.prestige(profile.profile_id)

    rewards = context.rewards.prestige_rewards_for_profile(profile.profile_id)
    assert [r["name"] for r in rewards] == ["Prestige 2", "Prestige 1"]
    assert rewards[0]["color"] == "blue"
    assert rewards[1]["color"] == "green"


def test_reward_definitions_have_unique_ids():
    ids = [tier.reward_id for tier in all_tiers()]
    assert len(ids) == len(set(ids))


def test_chain_ids_are_unique():
    chain_ids = [chain.chain_id for chain in CHALLENGE_CHAINS]
    assert len(chain_ids) == len(set(chain_ids))


def test_every_chains_tiers_are_in_ascending_threshold_order():
    for chain in CHALLENGE_CHAINS:
        thresholds = [tier.threshold for tier in chain.tiers]
        assert thresholds == sorted(thresholds)


def test_every_tiers_rarity_index_is_valid():
    for tier in all_tiers():
        assert 0 <= tier.rarity_index <= 4


def test_stat_id_for_tier_finds_the_right_chain():
    assert stat_id_for_tier("mowing_ranger") == "engine_hours_logged"
    assert stat_id_for_tier("fitness_iron_will") == "workout_hours_logged"


def test_stat_id_for_tier_unknown_reward_id_returns_none():
    assert stat_id_for_tier("does-not-exist") is None


# ------------------------------------------------------------------
# Chain progression helpers — pure logic, no manager needed
# ------------------------------------------------------------------

def _mowing_tiers():
    return next(chain.tiers for chain in CHALLENGE_CHAINS if chain.chain_id == "mowing")


def test_highest_unlocked_tier_none_when_chain_not_started():
    assert highest_unlocked_tier(_mowing_tiers(), unlocked_ids=set()) is None


def test_highest_unlocked_tier_returns_the_furthest_reached():
    unlocked = {"mowing_rookie", "mowing_yard_worker"}
    assert highest_unlocked_tier(_mowing_tiers(), unlocked).reward_id == "mowing_yard_worker"


def test_next_locked_tier_returns_the_first_not_yet_unlocked():
    unlocked = {"mowing_rookie"}
    assert next_locked_tier(_mowing_tiers(), unlocked).reward_id == "mowing_yard_worker"


def test_next_locked_tier_none_once_chain_is_maxed_out():
    unlocked = {tier.reward_id for tier in _mowing_tiers()}
    assert next_locked_tier(_mowing_tiers(), unlocked) is None
