"""
tests.test_import_life_data
=============================

Importing a life-data pack into the Garage (tools/import_life_data.py): a compound hours/miles-OR-time line becomes
one meter task with a calendar fallback (DEC-0131); a timing belt is flagged high and never given a fabricated
baseline; the import is idempotent (an existing asset is updated via a pack alias, not duplicated; a task isn't
re-added); and no meter task is handed a current reading. Fictional data only — no real vehicles in the repo.
"""

import json

import pytest

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceManager
from tools.import_life_data import import_life_data, trigger_for

PACK = {
    "aliases": {"Acme Hauler": "Old Blue"},
    "assets": [
        {"id": "hauler", "module": "garage", "name": "Acme Hauler", "make": "Acme", "model": "Hauler LX",
         "year": 2006, "owner": "self", "odometer_mi": None, "maintenance": [
             {"task": "Timing belt + water pump", "basis": "mileage_or_time", "interval": "105,000 mi or 7 years", "note": "Interference engine; treat as DUE."},
             {"task": "Engine oil & filter", "basis": "minder", "interval": "Maintenance Minder (~7,500 mi typical)"}]},
        {"id": "mower", "module": "garage", "name": "Acme Mower", "make": "Acme", "model": "ZM-100", "owner": "self",
         "category": "Lawn equipment", "hour_meter": None, "warranty": {"months": 36, "hours": 200, "until": "2029-09-12"},
         "maintenance": [
             {"task": "Engine oil & filter", "basis": "hours_or_time", "interval": "100 hours or annually"},
             {"task": "Break-in oil & filter", "basis": "hours", "interval": "After first 8 hours"}]},
    ],
}


@pytest.fixture
def manager(tmp_path):
    context = AppContext(config=ConfigManager(), events=EventBus())
    return MaintenanceManager(context, data_dir=tmp_path)


@pytest.fixture
def pack_file(tmp_path):
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(PACK), encoding="utf-8")
    return p


def test_a_compound_line_becomes_one_meter_task_with_a_calendar_fallback():
    assert trigger_for("hours_or_time", "100 hours or annually") == {
        "trigger_type": "runtime", "meter_unit": "hours", "meter_interval": 100, "calendar_fallback_days": 365}
    belt = trigger_for("mileage_or_time", "105,000 mi or 7 years")
    assert belt["meter_interval"] == 105000 and belt["calendar_fallback_days"] == 7 * 365
    assert trigger_for("hours", "After first 8 hours") == {"trigger_type": "runtime", "meter_unit": "hours", "meter_interval": 8}
    assert trigger_for("time", "3 years")["interval_days"] == 3 * 365


def test_the_import_creates_assets_and_compound_tasks_without_fabricating_readings(manager, pack_file):
    import_life_data(manager, pack=pack_file, owner_profile_id="zac1")
    names = sorted(a.name for a in manager.all_assets())
    assert names == ["Acme Hauler", "Acme Mower"]
    mower = next(a for a in manager.all_assets() if a.name == "Acme Mower")
    assert mower.owner_profile_id == "zac1" and mower.warranty_until == "2029-09-12" and mower.category == "Lawn equipment"
    oil = next(t for t in manager.tasks_for_asset(mower.asset_id) if t.title == "Engine oil & filter")
    assert oil.is_compound and oil.meter_interval == 100 and oil.calendar_fallback_days == 365
    assert oil.last_completed is None and oil.last_completed_meter_value is None


def test_the_timing_belt_is_flagged_high_and_never_given_a_baseline(manager, pack_file):
    import_life_data(manager, pack=pack_file, owner_profile_id="zac1")
    truck = next(a for a in manager.all_assets() if a.name == "Acme Hauler")
    belt = next(t for t in manager.tasks_for_asset(truck.asset_id) if "Timing belt" in t.title)
    assert belt.priority == "high" and belt.trigger_type == "mileage"
    assert belt.meter_interval == 105000 and belt.calendar_fallback_days == 7 * 365
    assert belt.last_completed is None and belt.last_completed_meter_value is None


def test_a_re_run_updates_in_place_and_adds_no_duplicates(manager, pack_file):
    first = import_life_data(manager, pack=pack_file, owner_profile_id="zac1")
    assets_before = len(manager.all_assets())
    tasks_before = len(manager.all_tasks())
    second = import_life_data(manager, pack=pack_file, owner_profile_id="zac1")
    assert len(manager.all_assets()) == assets_before and len(manager.all_tasks()) == tasks_before
    assert second["assets_added"] == [] and second["tasks_added"] == []
    assert set(second["assets_updated"]) == {"Acme Hauler", "Acme Mower"}
    assert first["tasks_added"] and second["skipped_tasks"] >= len(first["tasks_added"])


def test_an_existing_named_asset_is_updated_not_duplicated(manager, pack_file):
    """An existing record matched by a pack alias is updated, never a second record."""
    manager.add_asset("Old Blue", category="Vehicle", manufacturer="Acme", model="Hauler")
    import_life_data(manager, pack=pack_file, owner_profile_id="zac1")
    haulers = [a for a in manager.all_assets() if a.manufacturer == "Acme" and "Hauler" in a.model]
    assert len(haulers) == 1 and haulers[0].name == "Old Blue"
    assert haulers[0].model == "Hauler LX"  # updated with the richer model
