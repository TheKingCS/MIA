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
import core.project_manager as project_manager_module
import core.workout_manager as workout_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.kitchen_manager import KitchenManager
from core.maintenance_manager import MaintenanceManager
from core.mission_manager import MissionManager
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.rewards_manager import (
    CHALLENGE_CHAINS,
    HIDDEN_ACHIEVEMENTS,
    RewardsManager,
    all_tiers,
    combined_stat_value,
    highest_unlocked_tier,
    next_locked_tier,
    reward_progress_fraction,
    stat_id_for_tier,
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


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.maintenance = MaintenanceManager(context)
    context.missions = MissionManager(context)
    context.workout = WorkoutManager(context)
    context.data_logger = DataLoggerManager(context)
    context.kitchen = KitchenManager(context)
    context.projects = ProjectManager(context)
    context.rewards = RewardsManager(context)
    return context


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
# Stat values — derived from real data
# ------------------------------------------------------------------

def test_engine_hours_logged_sums_across_assets(isolated_paths):
    context = _make_context()
    mower = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=mower.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 4.5)
    context.maintenance.log_reading(task.task_id, 7.0)  # latest reading wins, not a sum of readings

    other = context.maintenance.add_asset(name="Generator", category="Power Equipment")
    other_task = context.maintenance.add_task(asset_id=other.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(other_task.task_id, 2.0)

    assert context.rewards.stat_value("engine_hours_logged") == 9.0


def test_engine_hours_logged_ignores_unrelated_tasks(isolated_paths):
    context = _make_context()
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Oil Change", trigger_type="calendar", interval_days=30)
    context.maintenance.log_reading(task.task_id, 999.0)

    assert context.rewards.stat_value("engine_hours_logged") == 0.0


def test_engine_hours_logged_zero_with_no_readings(isolated_paths):
    context = _make_context()
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")

    assert context.rewards.stat_value("engine_hours_logged") == 0.0


def test_workout_hours_logged_sums_session_minutes(isolated_paths):
    context = _make_context()
    context.workout.add_session(template_id="", date_str="2026-09-01", duration_minutes=90)
    context.workout.add_session(template_id="", date_str="2026-09-02", duration_minutes=30)

    assert context.rewards.stat_value("workout_hours_logged") == 2.0


def test_missions_completed_counts_only_completed_status(isolated_paths):
    context = _make_context()
    m1 = context.missions.add_mission(name="Done one")
    context.missions.update_mission(m1.mission_id, status="completed")
    context.missions.add_mission(name="Still active")

    assert context.rewards.stat_value("missions_completed") == 1.0


def test_vehicle_miles_logged_sums_odometer_readings_across_assets(isolated_paths):
    context = _make_context()
    truck = context.maintenance.add_asset(name="Ridgeline", category="Vehicle")
    odometer = context.maintenance.add_task(asset_id=truck.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles")
    context.maintenance.log_reading(odometer.task_id, 40000.0)
    context.maintenance.log_reading(odometer.task_id, 40250.0)  # latest reading wins

    other = context.maintenance.add_asset(name="Second Car", category="Vehicle")
    other_odometer = context.maintenance.add_task(asset_id=other.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles")
    context.maintenance.log_reading(other_odometer.task_id, 1000.0)

    assert context.rewards.stat_value("vehicle_miles_logged") == 41250.0


def test_vehicle_miles_logged_ignores_other_mileage_tasks(isolated_paths):
    """Oil changes/tire rotations also log in miles, but they track
    miles-since-last-service, not the vehicle's real lifetime total —
    only the Odometer task itself represents that."""
    context = _make_context()
    truck = context.maintenance.add_asset(name="Ridgeline", category="Vehicle")
    oil_change = context.maintenance.add_task(asset_id=truck.asset_id, title="Oil & filter change", trigger_type="mileage", meter_unit="miles")
    context.maintenance.log_reading(oil_change.task_id, 3000.0)

    assert context.rewards.stat_value("vehicle_miles_logged") == 0.0


def test_meals_cooked_counts_real_meal_log_entries(isolated_paths):
    context = _make_context()
    recipe = context.kitchen.add_recipe(name="Tacos")
    context.kitchen.log_meal(recipe.recipe_id, date_str="2026-09-01")
    context.kitchen.log_meal(recipe.recipe_id, date_str="2026-09-02")

    assert context.rewards.stat_value("meals_cooked") == 2.0


def test_projects_completed_counts_only_complete_status(isolated_paths):
    context = _make_context()
    done = context.projects.add_project(name="Deck rebuild")
    context.projects.update_project(done.project_id, status="Complete")
    context.projects.add_project(name="Still planning")

    assert context.rewards.stat_value("projects_completed") == 1.0


def test_all_stat_values_covers_every_definition(isolated_paths):
    context = _make_context()
    values = context.rewards.all_stat_values()
    assert set(values.keys()) == {
        "engine_hours_logged", "workout_hours_logged", "missions_completed",
        "vehicle_miles_logged", "meals_cooked", "projects_completed",
    }


# ------------------------------------------------------------------
# Unlocking
# ------------------------------------------------------------------

def test_scan_for_new_unlocks_unlocks_when_threshold_crossed(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
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
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 60.0)  # past rookie(10)/yard_worker(25)/ranger(50)

    newly_unlocked = context.rewards.scan_for_new_unlocks(profile.profile_id)

    reward_ids = {r.reward_id for r in newly_unlocked}
    assert reward_ids == {"mowing_rookie", "mowing_yard_worker", "mowing_ranger"}


def test_scan_for_new_unlocks_is_idempotent(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 10.0)

    first_scan = context.rewards.scan_for_new_unlocks(profile.profile_id)
    second_scan = context.rewards.scan_for_new_unlocks(profile.profile_id)

    assert len(first_scan) >= 1
    assert second_scan == []


def test_scan_for_new_unlocks_below_threshold_unlocks_nothing(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 1.5)

    assert context.rewards.scan_for_new_unlocks(profile.profile_id) == []
    assert context.rewards.is_unlocked(profile.profile_id, "mowing_rookie") is False


def test_scan_for_new_unlocks_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
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
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 10.0)
    context.rewards.scan_for_new_unlocks(profile.profile_id)

    assert "mowing_rookie" in context.rewards.unlocked_reward_ids(profile.profile_id)


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
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
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
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 5.0)

    assert context.rewards.scan_for_new_hidden_achievements(profile.profile_id) == []


def test_scan_for_new_hidden_achievements_is_idempotent(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 60.0)

    first_scan = context.rewards.scan_for_new_hidden_achievements(profile.profile_id)
    second_scan = context.rewards.scan_for_new_hidden_achievements(profile.profile_id)

    assert len(first_scan) >= 1
    assert second_scan == []


def test_unlocked_hidden_achievements_reflects_real_unlocks(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
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
