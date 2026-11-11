"""
tests.test_upkeep_missions
============================

Upkeep as scheduled missions (DEC-0153, core/upkeep_missions.py): this week's upkeep becomes one mission per task and
due date, attached to the task and its asset; it isn't made twice or remade once set aside; Done on the upkeep
completes the mission, and completing the mission marks the upkeep done, never twice.
"""

from datetime import date, timedelta

import pytest

import core.config_manager as config_module
from core import upkeep_missions
from core.actions import ACTION_TYPES
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceManager
from core.mission_manager import MissionManager

TODAY = date.today()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """Maintenance with a truck (oil due in 3 days), a furnace (filter overdue) and a mower (blades in 40 days), and
    missions, wired as at startup."""
    import core.mission_manager as mm

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(mm, "_MISSIONS_FILE", tmp_path / "missions.json")  # Missions takes no folder: never the real file
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.maintenance = MaintenanceManager(context, data_dir=tmp_path / "data")
    context.missions = MissionManager(context)
    assert context.missions.path == tmp_path / "missions.json"
    upkeep_missions.wire(context)
    iso = lambda days: (TODAY + timedelta(days=days)).isoformat()  # noqa: E731
    truck = context.maintenance.add_asset(name="Truck")
    furnace = context.maintenance.add_asset(name="Furnace")
    mower = context.maintenance.add_asset(name="Mower")
    context.oil = context.maintenance.add_task(truck.asset_id, "Change the oil", interval_days=90, last_completed=iso(-87))
    context.filter = context.maintenance.add_task(furnace.asset_id, "Replace the filter", interval_days=30, last_completed=iso(-35))
    context.maintenance.add_task(mower.asset_id, "Sharpen blades", interval_days=60, last_completed=iso(-20))
    context.truck = truck
    return context


def test_this_weeks_upkeep_becomes_one_mission_each_on_its_asset(ctx):
    made = upkeep_missions.ensure(ctx, TODAY)
    assert sorted(m.name for m in made) == ["Change the oil: Truck", "Replace the filter: Furnace"]
    oil = next(m for m in made if m.maintenance_task_id == ctx.oil.task_id)
    assert oil.maintenance_asset_id == ctx.truck.asset_id and oil.mission_type == "SCHEDULED MISSION"
    assert oil.assigned_by == "mia" and oil.occurrence_key.startswith("upkeep:") and len(oil.objectives) == 1
    assert ctx.missions.missions_for_maintenance_asset(ctx.truck.asset_id) == [oil]
    assert upkeep_missions.ensure(ctx, TODAY) == []  # never twice


def test_a_mission_set_aside_isnt_made_again_for_the_same_date(ctx):
    oil = next(m for m in upkeep_missions.ensure(ctx, TODAY) if m.maintenance_task_id == ctx.oil.task_id)
    ctx.missions.update_mission(oil.mission_id, status="abandoned", abandon_reason="Not this time")
    assert upkeep_missions.ensure(ctx, TODAY) == []


def test_done_on_the_upkeep_completes_its_mission(ctx):
    upkeep_missions.ensure(ctx, TODAY)
    said = ACTION_TYPES["maintenance.done"].execute(ctx, {"task_id": ctx.filter.task_id})
    assert said.startswith("Replace the filter is done")
    mission = ctx.missions.missions_for_maintenance_task(ctx.filter.task_id)[0]
    assert mission.status == "completed"
    assert ctx.maintenance.get_task(ctx.filter.task_id).last_completed == TODAY.isoformat()


def test_completing_the_mission_marks_the_upkeep_done_once(ctx):
    upkeep_missions.ensure(ctx, TODAY)
    mission = ctx.missions.missions_for_maintenance_task(ctx.oil.task_id)[0]
    ctx.missions.update_mission(mission.mission_id, status="completed")
    task = ctx.maintenance.get_task(ctx.oil.task_id)
    assert task.last_completed == TODAY.isoformat()
    assert upkeep_missions.ensure(ctx, TODAY) == []  # next due in 90 days: nothing this week


def test_a_deleted_task_sets_its_mission_aside(ctx):
    upkeep_missions.ensure(ctx, TODAY)
    ctx.maintenance.delete_task(ctx.oil.task_id)
    assert upkeep_missions.settle(ctx, TODAY) == 1
    assert ctx.missions.missions_for_maintenance_task(ctx.oil.task_id)[0].status == "abandoned"
