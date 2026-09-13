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
import core.maintenance_manager as maintenance_manager_module
import core.mission_manager as mission_manager_module
import core.workout_manager as workout_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceManager
from core.mission_manager import MissionManager
from core.profile_manager import ProfileManager
from core.rewards_manager import (
    REWARD_DEFINITIONS,
    RewardsManager,
    reward_progress_fraction,
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


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.maintenance = MaintenanceManager(context)
    context.missions = MissionManager(context)
    context.workout = WorkoutManager(context)
    context.data_logger = DataLoggerManager(context)
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


def test_all_stat_values_covers_every_definition(isolated_paths):
    context = _make_context()
    values = context.rewards.all_stat_values()
    assert set(values.keys()) == {"engine_hours_logged", "workout_hours_logged", "missions_completed"}


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
    assert "john_deere_hat" in reward_ids
    assert context.rewards.is_unlocked(profile.profile_id, "john_deere_hat") is True


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
    assert context.rewards.is_unlocked(profile.profile_id, "john_deere_hat") is False


def test_scan_for_new_unlocks_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 10.0)
    context.rewards.scan_for_new_unlocks(profile.profile_id)

    reloaded_profiles = ProfileManager(context)
    reloaded = reloaded_profiles.get_profile(profile.profile_id)
    assert "john_deere_hat" in reloaded.unlocked_reward_ids


def test_scan_for_new_unlocks_with_no_profiles_manager_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.rewards = RewardsManager(context)
    assert context.rewards.scan_for_new_unlocks("does-not-exist") == []


def test_is_unlocked_false_for_unknown_profile(isolated_paths):
    context = _make_context()
    assert context.rewards.is_unlocked("does-not-exist", "john_deere_hat") is False


def test_unlocked_reward_ids_reflects_real_unlocks(isolated_paths):
    context = _make_context()
    profile = context.profiles.create_profile(name="Alex")
    asset = context.maintenance.add_asset(name="Mower", category="Power Equipment")
    task = context.maintenance.add_task(asset_id=asset.asset_id, title="Engine Hours", trigger_type="runtime", meter_unit="engine hours")
    context.maintenance.log_reading(task.task_id, 10.0)
    context.rewards.scan_for_new_unlocks(profile.profile_id)

    assert "john_deere_hat" in context.rewards.unlocked_reward_ids(profile.profile_id)


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
    ids = [r.reward_id for r in REWARD_DEFINITIONS]
    assert len(ids) == len(set(ids))
