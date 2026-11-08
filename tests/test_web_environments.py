"""
tests.test_web_environments
=============================

An area's own space (DEC-0130 M3, core/web_environments.py): the Garage environment's bays come from the Garage's own
assets (never the house's), most overdue first; the parts running low are gathered across them, each once with what
uses it; the hub carries the environment for the Garage and none for areas still on tiles.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import core.web_surfaces as surfaces
from core.actions import ACTION_TYPES
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager
from core.links import LinkStore
from core.maintenance_manager import MaintenanceManager
from core.material_manager import MaterialManager
from core.web_areas import hub
from core.web_environments import garage, low_parts


@pytest.fixture
def shop(tmp_path):
    """A mower (one task overdue), a truck, a furnace (the house's), oil running low used by both vehicles."""
    ctx = SimpleNamespace(events=EventBus(), config=None, profiles=None)
    ctx.links = LinkStore(ctx, data_dir=tmp_path)
    ctx.maintenance = MaintenanceManager(ctx, data_dir=tmp_path)
    ctx.materials = MaterialManager(ctx, data_dir=tmp_path)
    ctx.inventory = InventoryManager(ctx, data_dir=tmp_path)
    m = ctx.maintenance
    mower, truck = m.add_asset("Mower", "Power Equipment"), m.add_asset("Truck", "Vehicle")
    m.add_asset("Furnace", "Appliance")
    task = m.add_task(mower.asset_id, "Check oil", trigger_type="calendar", interval_days=30)
    m.update_task(task.task_id, last_completed=(date.today() - timedelta(days=45)).isoformat())
    oil = ctx.materials.add_material("10W-30 oil", unit="qt", quantity_on_hand=0.5, reorder_threshold=1)
    for asset in (mower, truck):
        ACTION_TYPES["asset.part_add"].execute(ctx, {"asset_id": asset.asset_id, "part": f"material:{oil.material_id}"})
    return ctx, mower, truck


def test_bays_are_the_garages_own_most_overdue_first(shop):
    ctx, mower, truck = shop
    env = garage(ctx)
    assert [b["name"] for b in env["bays"]] == ["Mower", "Truck"]
    assert env["bays"][0]["overdue"] == 1 and env["bays"][0]["page"] == f"asset.html?id={mower.asset_id}"
    assert [n["title"] for n in env["needs"]] == ["Check oil"]
    assert [t["id"] for t in env["bench"]][:2] == ["toolbox", "inventory"]


def test_low_parts_are_gathered_once_with_what_uses_them(shop):
    ctx, mower, truck = shop
    [oil] = low_parts(ctx, [mower.asset_id, truck.asset_id])
    assert oil["name"] == "10W-30 oil" and oil["state"] == "low" and sorted(oil["used_by"]) == ["Mower", "Truck"]


def test_the_hub_carries_the_garage_space_and_tiles_elsewhere(shop, monkeypatch):
    ctx, _, _ = shop
    monkeypatch.setattr(surfaces, "_visible", lambda context, app: True)
    assert hub(ctx, "garage")["environment"]["kind"] == "garage"
    assert hub(ctx, "finances")["environment"] is None
