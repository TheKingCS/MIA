"""
tests.test_assistant_action_handlers
=======================================

Unit tests for core.application.MIAApplication's assistant action
handlers (_action_*) — milestone 5.7's read/list actions, plus
regression coverage for the pre-existing write actions that had no
direct unit test before (only exercised via test_llm_manager.py's
chat_with_tools mocks and manual/live-model verification). These are
all plain @staticmethods (context, arguments) -> str, so they're called
directly here with real manager instances (data dirs isolated to
tmp_path, same pattern as test_alarm_manager.py's isolated_paths) —
no Qt, no LLM, no MIAApplication instance needed.
"""

from __future__ import annotations

import pytest

import core.alarm_manager as alarm_manager_module
import core.calendar_manager as calendar_manager_module
import core.component_manager as component_manager_module
import core.config_manager as config_manager_module
import core.expedition_manager as expedition_manager_module
import core.inventory_manager as inventory_manager_module
import core.insight_manager as insight_manager_module
import core.job_manager as job_manager_module
import core.journal_manager as journal_manager_module
import core.ledger_manager as ledger_manager_module
import core.material_manager as material_manager_module
import core.mission_manager as mission_manager_module
import core.product_manager as product_manager_module
import core.project_manager as project_manager_module
import core.script_library_manager as script_library_manager_module
import core.task_manager as task_manager_module
import core.trail_map_library as trail_map_library_module
import core.trip_manager as trip_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.application import MIAApplication
from core.calendar_manager import CalendarManager
from core.component_manager import ComponentManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager
from core.insight_manager import InsightManager
from core.inventory_manager import InventoryManager
from core.job_manager import JobManager
from core.journal_manager import JournalManager
from core.ledger_manager import LedgerManager
from core.material_manager import MaterialManager
from core.memory_manager import MemoryManager
from core.mission_manager import MissionManager
from core.product_manager import ProductManager
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.script_library_manager import ScriptLibraryManager
from core.task_manager import TaskManager
from core.trail_map_library import NotAPdfError, TrailMapLibrary
from core.trip_manager import TripManager
from core.waypoint_manager import WaypointManager


@pytest.fixture
def context(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    # _action_set_theme() calls context.config.save() for real — without
    # this, that write would land in the actual config/config.json, not
    # a throwaway file (found by discovering an actual pytest tmp_path
    # value sitting in the real config.json's trips.photo_root_path key
    # after an earlier test run — see docs/ROADMAP.md milestone 5.14).
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(alarm_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(alarm_manager_module, "_ALARMS_FILE", data_dir / "alarms.json")
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", data_dir / "journal_entries.json")
    monkeypatch.setattr(inventory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(inventory_manager_module, "_ITEMS_FILE", data_dir / "inventory_items.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", data_dir / "expeditions.json")
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", data_dir / "trips.json")
    monkeypatch.setattr(calendar_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(calendar_manager_module, "_EVENTS_FILE", data_dir / "calendar_events.json")
    monkeypatch.setattr(component_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(component_manager_module, "_COMPONENTS_FILE", data_dir / "components.json")
    monkeypatch.setattr(script_library_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(script_library_manager_module, "_SCRIPTS_FILE", data_dir / "scripts.json")
    monkeypatch.setattr(project_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(project_manager_module, "_PROJECTS_FILE", data_dir / "projects.json")
    monkeypatch.setattr(task_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(task_manager_module, "_TASKS_FILE", data_dir / "tasks.json")
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(material_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(material_manager_module, "_MATERIALS_FILE", data_dir / "materials.json")
    monkeypatch.setattr(job_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(job_manager_module, "_JOBS_FILE", data_dir / "jobs.json")
    monkeypatch.setattr(product_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(product_manager_module, "_PRODUCTS_FILE", data_dir / "products.json")
    monkeypatch.setattr(ledger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(ledger_manager_module, "_REVENUE_FILE", data_dir / "revenue.json")
    monkeypatch.setattr(ledger_manager_module, "_EXPENSES_FILE", data_dir / "expenses.json")
    monkeypatch.setattr(trail_map_library_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trail_map_library_module, "_TRAIL_MAPS_FILE", data_dir / "trail_maps.json")
    monkeypatch.setattr(insight_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(insight_manager_module, "_INSIGHTS_FILE", data_dir / "insights.json")
    monkeypatch.setattr(insight_manager_module, "_RECOMMENDATIONS_FILE", data_dir / "recommendations.json")

    ctx = AppContext(config=ConfigManager(), events=EventBus())
    ctx.config.set("trips.photo_root_path", str(tmp_path / "trip_photos"))
    ctx.config.set("maps.trail_map_root_path", str(tmp_path / "trail_maps"))
    ctx.alarms = AlarmManager(ctx)
    ctx.journal = JournalManager(ctx)
    ctx.inventory = InventoryManager(ctx)
    ctx.waypoints = WaypointManager(ctx)
    ctx.expeditions = ExpeditionManager(ctx)
    ctx.trips = TripManager(ctx)
    ctx.calendar = CalendarManager(ctx)
    ctx.components = ComponentManager(ctx)
    ctx.scripts = ScriptLibraryManager(ctx)
    ctx.profiles = ProfileManager(ctx)
    ctx.projects = ProjectManager(ctx)
    ctx.tasks = TaskManager(ctx)
    ctx.memories = MemoryManager(ctx)
    ctx.missions = MissionManager(ctx)
    ctx.materials = MaterialManager(ctx)
    ctx.jobs = JobManager(ctx)
    ctx.products = ProductManager(ctx)
    ctx.ledger = LedgerManager(ctx)
    ctx.trail_maps = TrailMapLibrary(ctx)
    ctx.insights = InsightManager(ctx)
    return ctx


# ----------------------------------------------------------------------
# Alarms
# ----------------------------------------------------------------------

def test_add_alarm_requires_a_time(context):
    result = MIAApplication._action_add_alarm(context, {"label": "Wake Up"})
    assert "time" in result.lower()
    assert context.alarms.all_alarms() == []


def test_add_alarm_creates_alarm(context):
    result = MIAApplication._action_add_alarm(context, {"label": "Wake Up", "time": "07:00"})
    assert "Wake Up" in result and "07:00" in result
    assert len(context.alarms.all_alarms()) == 1


def test_list_alarms_empty(context):
    assert "no alarms" in MIAApplication._action_list_alarms(context, {}).lower()


def test_list_alarms_returns_all(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    context.alarms.add_alarm(label="Lunch", time="12:00")
    result = MIAApplication._action_list_alarms(context, {})
    assert "Wake Up" in result and "07:00" in result
    assert "Lunch" in result and "12:00" in result


def test_delete_alarm_removes_matching_alarm(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    result = MIAApplication._action_delete_alarm(context, {"label": "Wake Up"})
    assert "Wake Up" in result
    assert context.alarms.all_alarms() == []


def test_delete_alarm_is_case_insensitive(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    MIAApplication._action_delete_alarm(context, {"label": "wake up"})
    assert context.alarms.all_alarms() == []


def test_delete_alarm_unknown_label_does_not_delete_anything(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    result = MIAApplication._action_delete_alarm(context, {"label": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.alarms.all_alarms()) == 1


# ----------------------------------------------------------------------
# Notes
# ----------------------------------------------------------------------

def test_add_note_requires_a_title(context):
    result = MIAApplication._action_add_note(context, {"body": "buy milk"})
    assert "title" in result.lower()
    assert context.journal.all_entries() == []


def test_add_note_creates_entry(context):
    result = MIAApplication._action_add_note(context, {"title": "Groceries", "body": "buy milk"})
    assert "Groceries" in result
    assert len(context.journal.all_entries()) == 1


def test_list_notes_empty(context):
    assert "no notes" in MIAApplication._action_list_notes(context, {}).lower()


def test_list_notes_returns_all(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    context.journal.add_entry(title="Reminder", body="call mom")
    result = MIAApplication._action_list_notes(context, {})
    assert "Groceries" in result and "buy milk" in result
    assert "Reminder" in result and "call mom" in result


def test_list_notes_search_filters_by_query(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    context.journal.add_entry(title="Reminder", body="call mom")
    result = MIAApplication._action_list_notes(context, {"query": "milk"})
    assert "Groceries" in result
    assert "Reminder" not in result


def test_list_notes_search_no_match(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    result = MIAApplication._action_list_notes(context, {"query": "nonexistent"})
    assert "no matching notes" in result.lower()


def test_delete_note_removes_matching_entry(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    result = MIAApplication._action_delete_note(context, {"title": "Groceries"})
    assert "Groceries" in result
    assert context.journal.all_entries() == []


def test_delete_note_is_case_insensitive(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    MIAApplication._action_delete_note(context, {"title": "groceries"})
    assert context.journal.all_entries() == []


def test_delete_note_unknown_title_does_not_delete_anything(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    result = MIAApplication._action_delete_note(context, {"title": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.journal.all_entries()) == 1


# ----------------------------------------------------------------------
# Inventory
# ----------------------------------------------------------------------

def test_add_inventory_item_requires_a_name(context):
    result = MIAApplication._action_add_inventory_item(context, {"quantity": 5})
    assert "name" in result.lower()
    assert context.inventory.all_items() == []


def test_add_inventory_item_creates_item(context):
    result = MIAApplication._action_add_inventory_item(context, {"name": "M3 bolts", "quantity": 10})
    assert "10" in result and "M3 bolts" in result
    assert len(context.inventory.all_items()) == 1


def test_list_inventory_empty(context):
    assert "empty" in MIAApplication._action_list_inventory(context, {}).lower()


def test_list_inventory_returns_all(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    context.inventory.add_item(name="Solder", quantity=2)
    result = MIAApplication._action_list_inventory(context, {})
    assert "10x 'M3 bolts'" in result
    assert "2x 'Solder'" in result


def test_list_inventory_search_filters_by_query(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    context.inventory.add_item(name="Solder", quantity=2)
    result = MIAApplication._action_list_inventory(context, {"query": "bolt"})
    assert "M3 bolts" in result
    assert "Solder" not in result


def test_delete_inventory_item_removes_matching_item(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    result = MIAApplication._action_delete_inventory_item(context, {"name": "M3 bolts"})
    assert "M3 bolts" in result
    assert context.inventory.all_items() == []


def test_delete_inventory_item_unknown_name_does_not_delete_anything(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    result = MIAApplication._action_delete_inventory_item(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.inventory.all_items()) == 1


def test_adjust_inventory_quantity_decreases(context):
    context.inventory.add_item(name="M3 bolts", quantity=25)
    result = MIAApplication._action_adjust_inventory_quantity(context, {"name": "M3 bolts", "delta": -5})
    assert "20" in result
    assert context.inventory.all_items()[0].quantity == 20


def test_adjust_inventory_quantity_increases(context):
    context.inventory.add_item(name="M3 bolts", quantity=25)
    result = MIAApplication._action_adjust_inventory_quantity(context, {"name": "M3 bolts", "delta": 10})
    assert "35" in result
    assert context.inventory.all_items()[0].quantity == 35


def test_adjust_inventory_quantity_clamps_at_zero(context):
    context.inventory.add_item(name="M3 bolts", quantity=5)
    MIAApplication._action_adjust_inventory_quantity(context, {"name": "M3 bolts", "delta": -100})
    assert context.inventory.all_items()[0].quantity == 0


def test_adjust_inventory_quantity_unknown_name_does_not_crash(context):
    result = MIAApplication._action_adjust_inventory_quantity(context, {"name": "Nonexistent", "delta": 5})
    assert "nonexistent" in result.lower()


# ----------------------------------------------------------------------
# Waypoints
# ----------------------------------------------------------------------

def test_list_waypoints_empty(context):
    assert "no waypoints" in MIAApplication._action_list_waypoints(context, {}).lower()


def test_list_waypoints_returns_all(context):
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    context.waypoints.add_waypoint(name="Cabin", latitude=41.0, longitude=-84.0)
    result = MIAApplication._action_list_waypoints(context, {})
    assert "Home" in result and "Cabin" in result


def test_list_waypoints_search_filters_by_query(context):
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    context.waypoints.add_waypoint(name="Cabin", latitude=41.0, longitude=-84.0)
    result = MIAApplication._action_list_waypoints(context, {"query": "cabin"})
    assert "Cabin" in result
    assert "Home" not in result


def test_waypoint_distance_between_known_waypoints(context):
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    context.waypoints.add_waypoint(name="Cabin", latitude=41.0, longitude=-84.0)
    result = MIAApplication._action_waypoint_distance(context, {"from_name": "Home", "to_name": "Cabin"})
    assert "Home" in result and "Cabin" in result
    assert "km" in result and "bearing" in result


def test_waypoint_distance_unknown_from_waypoint(context):
    context.waypoints.add_waypoint(name="Cabin", latitude=41.0, longitude=-84.0)
    result = MIAApplication._action_waypoint_distance(context, {"from_name": "Nowhere", "to_name": "Cabin"})
    assert "nowhere" in result.lower()


def test_waypoint_distance_unknown_to_waypoint(context):
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    result = MIAApplication._action_waypoint_distance(context, {"from_name": "Home", "to_name": "Nowhere"})
    assert "nowhere" in result.lower()


def test_waypoint_distance_is_case_insensitive(context):
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    context.waypoints.add_waypoint(name="Cabin", latitude=41.0, longitude=-84.0)
    result = MIAApplication._action_waypoint_distance(context, {"from_name": "home", "to_name": "CABIN"})
    assert "km" in result


def test_delete_waypoint_removes_matching_waypoint(context):
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    result = MIAApplication._action_delete_waypoint(context, {"name": "Home"})
    assert "Home" in result
    assert context.waypoints.all_waypoints() == []


def test_delete_waypoint_unknown_name_does_not_delete_anything(context):
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    result = MIAApplication._action_delete_waypoint(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.waypoints.all_waypoints()) == 1


# ----------------------------------------------------------------------
# System health
# ----------------------------------------------------------------------

def test_get_system_health_returns_formatted_snapshot(context):
    result = MIAApplication._action_get_system_health(context, {})
    assert "CPU:" in result
    assert "Memory:" in result
    assert "Disk:" in result


# ----------------------------------------------------------------------
# Waypoints: add
# ----------------------------------------------------------------------

def test_add_waypoint_requires_a_name(context):
    result = MIAApplication._action_add_waypoint(context, {"latitude": 40.0, "longitude": -83.0})
    assert "name" in result.lower()
    assert context.waypoints.all_waypoints() == []


def test_add_waypoint_requires_valid_coordinates(context):
    result = MIAApplication._action_add_waypoint(context, {"name": "Home", "latitude": "not-a-number", "longitude": -83.0})
    assert "latitude" in result.lower()
    assert context.waypoints.all_waypoints() == []


def test_add_waypoint_creates_waypoint(context):
    result = MIAApplication._action_add_waypoint(
        context, {"name": "Home", "latitude": 40.0, "longitude": -83.0, "category": "Campsite"}
    )
    assert "Home" in result
    waypoints = context.waypoints.all_waypoints()
    assert len(waypoints) == 1
    assert waypoints[0].category == "Campsite"


def test_add_waypoint_unrecognized_category_falls_back_to_uncategorized(context):
    MIAApplication._action_add_waypoint(
        context, {"name": "Home", "latitude": 40.0, "longitude": -83.0, "category": "Bogus"}
    )
    assert context.waypoints.all_waypoints()[0].category == ""


# ----------------------------------------------------------------------
# Expeditions
# ----------------------------------------------------------------------

def test_add_expedition_requires_a_name(context):
    result = MIAApplication._action_add_expedition(context, {})
    assert "name" in result.lower()
    assert context.expeditions.all_expeditions() == []


def test_add_expedition_creates_expedition(context):
    result = MIAApplication._action_add_expedition(context, {"name": "Field Season", "start_date": "2026-08-14"})
    assert "Field Season" in result
    assert len(context.expeditions.all_expeditions()) == 1


def test_list_expeditions_empty(context):
    assert "no expeditions" in MIAApplication._action_list_expeditions(context, {}).lower()


def test_list_expeditions_returns_all(context):
    context.expeditions.add_expedition(name="Field Season", start_date="2026-08-14", location="Sawtooth Wilderness")
    result = MIAApplication._action_list_expeditions(context, {})
    assert "Field Season" in result and "2026-08-14" in result and "Sawtooth Wilderness" in result


# ----------------------------------------------------------------------
# Trips
# ----------------------------------------------------------------------

def test_add_trip_requires_a_name(context):
    context.expeditions.add_expedition(name="Field Season")
    result = MIAApplication._action_add_trip(context, {"expedition_name": "Field Season"})
    assert "name" in result.lower()
    assert context.trips.all_trips() == []


def test_add_trip_unknown_expedition_does_not_create_anything(context):
    result = MIAApplication._action_add_trip(context, {"expedition_name": "Nonexistent", "name": "Day 1"})
    assert "nonexistent" in result.lower()
    assert context.trips.all_trips() == []


def test_add_trip_creates_trip_under_expedition(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    result = MIAApplication._action_add_trip(
        context, {"expedition_name": "field season", "name": "Day 1", "activity_type": "Hiking"}
    )
    assert "Day 1" in result and "Field Season" in result
    trips = context.trips.all_trips()
    assert len(trips) == 1
    assert trips[0].expedition_id == expedition.expedition_id
    assert trips[0].activity_type == "Hiking"


def test_add_trip_unrecognized_activity_type_falls_back_to_unspecified(context):
    context.expeditions.add_expedition(name="Field Season")
    MIAApplication._action_add_trip(context, {"expedition_name": "Field Season", "name": "Day 1", "activity_type": "Bogus"})
    assert context.trips.all_trips()[0].activity_type == ""


def test_list_trips_empty(context):
    assert "no trips" in MIAApplication._action_list_trips(context, {}).lower()


def test_list_trips_returns_all(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="Hiking")
    result = MIAApplication._action_list_trips(context, {})
    assert "Day 1" in result and "Hiking" in result


def test_list_trips_filters_by_unknown_expedition(context):
    result = MIAApplication._action_list_trips(context, {"expedition_name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_list_trips_filters_by_known_expedition(context):
    expedition_a = context.expeditions.add_expedition(name="Field Season")
    expedition_b = context.expeditions.add_expedition(name="Other Trip")
    context.trips.add_trip(expedition_id=expedition_a.expedition_id, name="Day 1")
    context.trips.add_trip(expedition_id=expedition_b.expedition_id, name="Other Day")
    result = MIAApplication._action_list_trips(context, {"expedition_name": "Field Season"})
    assert "Day 1" in result
    assert "Other Day" not in result


# ----------------------------------------------------------------------
# Gear checklist
# ----------------------------------------------------------------------

def test_add_gear_item_requires_a_label(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    result = MIAApplication._action_add_gear_item(context, {"trip_name": "Day 1"})
    assert "gear item" in result.lower()


def test_add_gear_item_unknown_trip_does_not_add_anything(context):
    result = MIAApplication._action_add_gear_item(context, {"trip_name": "Nonexistent", "label": "Tent"})
    assert "nonexistent" in result.lower()


def test_add_gear_item_adds_to_matching_trip(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    result = MIAApplication._action_add_gear_item(context, {"trip_name": "day 1", "label": "Tent"})
    assert "Tent" in result and "Day 1" in result
    reloaded = context.trips.get_trip(trip.trip_id)
    assert reloaded.gear[0].label == "Tent"


# ----------------------------------------------------------------------
# Trip journal / weather log
# ----------------------------------------------------------------------

def test_add_trip_log_entry_requires_a_title(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    result = MIAApplication._action_add_trip_log_entry(context, {"trip_name": "Day 1"})
    assert "title" in result.lower()
    assert context.journal.all_entries() == []


def test_add_trip_log_entry_unknown_trip_does_not_add_anything(context):
    result = MIAApplication._action_add_trip_log_entry(context, {"trip_name": "Nonexistent", "title": "Reached camp"})
    assert "nonexistent" in result.lower()
    assert context.journal.all_entries() == []


def test_add_trip_log_entry_creates_linked_entry(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    result = MIAApplication._action_add_trip_log_entry(
        context, {"trip_name": "day 1", "title": "Reached camp", "conditions": "Clear, ~15C"}
    )
    assert "Reached camp" in result
    entries = context.journal.all_entries()
    assert len(entries) == 1
    assert entries[0].trip_id == trip.trip_id
    assert entries[0].conditions == "Clear, ~15C"


# ----------------------------------------------------------------------
# Device profile / theme
# ----------------------------------------------------------------------

def test_get_device_profile_defaults_to_core(context):
    result = MIAApplication._action_get_device_profile(context, {})
    assert "core" in result.lower()


def test_get_device_profile_reports_home(context):
    context.config.set("system.device_profile", "home")
    result = MIAApplication._action_get_device_profile(context, {})
    assert "home" in result.lower()


def test_set_theme_rejects_unknown_theme(context):
    result = MIAApplication._action_set_theme(context, {"theme_id": "bogus"})
    assert "bogus" in result.lower()
    assert context.config.get("gui.theme") != "bogus"


def test_set_theme_updates_config_and_publishes_event(context):
    received = []
    context.events.subscribe("theme.changed", lambda theme_id: received.append(theme_id))
    result = MIAApplication._action_set_theme(context, {"theme_id": "low_energy"})
    assert "Low Energy" in result
    assert context.config.get("gui.theme") == "low_energy"
    assert received == ["low_energy"]


# ----------------------------------------------------------------------
# Birthday
# ----------------------------------------------------------------------

def test_set_birthday_requires_active_profile(context):
    result = MIAApplication._action_set_birthday(context, {"birthday": "1990-03-03"})
    assert "active user profile" in result.lower()


def test_set_birthday_rejects_invalid_format(context):
    context.profiles.create_profile(name="Alex", make_active=True)
    result = MIAApplication._action_set_birthday(context, {"birthday": "March 3rd"})
    assert "yyyy-mm-dd" in result.lower()


def test_set_birthday_saves_to_active_profile(context):
    context.profiles.create_profile(name="Alex", make_active=True)
    result = MIAApplication._action_set_birthday(context, {"birthday": "1990-03-03"})
    assert "1990-03-03" in result
    assert context.profiles.get_active_profile().birthday == "1990-03-03"


# ----------------------------------------------------------------------
# Calendar
# ----------------------------------------------------------------------

def test_add_calendar_event_requires_a_title(context):
    result = MIAApplication._action_add_calendar_event(context, {"date": "2026-08-14"})
    assert "title" in result.lower()
    assert context.calendar.all_events() == []


def test_add_calendar_event_requires_a_date(context):
    result = MIAApplication._action_add_calendar_event(context, {"title": "Doctor Appointment"})
    assert "date" in result.lower()
    assert context.calendar.all_events() == []


def test_add_calendar_event_creates_event(context):
    result = MIAApplication._action_add_calendar_event(
        context, {"title": "Doctor Appointment", "date": "2026-08-14", "time": "09:00"}
    )
    assert "Doctor Appointment" in result and "2026-08-14" in result
    assert len(context.calendar.all_events()) == 1


def test_list_calendar_events_empty(context):
    assert "no calendar events" in MIAApplication._action_list_calendar_events(context, {}).lower()


def test_list_calendar_events_returns_all(context):
    context.calendar.add_event(title="Doctor Appointment", date="2026-08-14", time="09:00")
    result = MIAApplication._action_list_calendar_events(context, {})
    assert "Doctor Appointment" in result and "2026-08-14" in result


def test_delete_calendar_event_removes_matching_event(context):
    context.calendar.add_event(title="Doctor Appointment", date="2026-08-14")
    result = MIAApplication._action_delete_calendar_event(context, {"title": "Doctor Appointment"})
    assert "Doctor Appointment" in result
    assert context.calendar.all_events() == []


def test_delete_calendar_event_unknown_title_does_not_delete_anything(context):
    context.calendar.add_event(title="Doctor Appointment", date="2026-08-14")
    result = MIAApplication._action_delete_calendar_event(context, {"title": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.calendar.all_events()) == 1


# ----------------------------------------------------------------------
# Power
# ----------------------------------------------------------------------

def test_get_power_status_unavailable(context):
    # A fake backend, not a real PowerManager — this sandbox's psutil
    # actually reports a real (likely host-passthrough) battery reading,
    # so relying on real hardware state here would be non-deterministic.
    class _FakeNoPower:
        def read(self):
            return None

    context.power = _FakeNoPower()
    result = MIAApplication._action_get_power_status(context, {})
    assert "not available" in result.lower() or "no battery" in result.lower()


def test_get_power_status_reports_reading(context):
    from core.power_manager import PowerStatus

    class _FakePower:
        def read(self):
            return PowerStatus(percent=87.0, plugged_in=False, seconds_left=3600)

    context.power = _FakePower()
    result = MIAApplication._action_get_power_status(context, {})
    assert "87" in result
    assert "battery" in result.lower()
    assert "60 minutes" in result


# ----------------------------------------------------------------------
# Components
# ----------------------------------------------------------------------

def test_add_component_requires_a_name(context):
    result = MIAApplication._action_add_component(context, {})
    assert "name" in result.lower()
    assert context.components.all_components() == []


def test_add_component_creates_component(context):
    result = MIAApplication._action_add_component(context, {"name": "M3 bolts", "quantity": 25, "category": "Fastener"})
    assert "M3 bolts" in result
    components = context.components.all_components()
    assert len(components) == 1
    assert components[0].quantity == 25


def test_list_components_empty(context):
    assert "no components" in MIAApplication._action_list_components(context, {}).lower()


def test_list_components_returns_all(context):
    context.components.add_component(name="M3 bolts", quantity=25, category="Fastener")
    result = MIAApplication._action_list_components(context, {})
    assert "M3 bolts" in result and "25" in result


def test_list_components_query_filters(context):
    context.components.add_component(name="M3 bolts", quantity=25)
    context.components.add_component(name="10k resistor", quantity=10)
    result = MIAApplication._action_list_components(context, {"query": "bolts"})
    assert "M3 bolts" in result
    assert "resistor" not in result.lower()


def test_delete_component_removes_matching_component(context):
    context.components.add_component(name="M3 bolts", quantity=25)
    result = MIAApplication._action_delete_component(context, {"name": "M3 bolts"})
    assert "M3 bolts" in result
    assert context.components.all_components() == []


def test_delete_component_unknown_name_does_not_delete_anything(context):
    context.components.add_component(name="M3 bolts", quantity=25)
    result = MIAApplication._action_delete_component(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.components.all_components()) == 1


# ----------------------------------------------------------------------
# Field Kit: connected devices + scripts
# ----------------------------------------------------------------------

def test_list_connected_devices_none_connected(context):
    class _FakeDevices:
        def list_block_devices(self):
            return []

        def list_serial_devices(self):
            return []

    context.devices = _FakeDevices()
    result = MIAApplication._action_list_connected_devices(context, {})
    assert "no external devices" in result.lower()


def test_list_connected_devices_reports_connected(context):
    class _FakeBlockDevice:
        display_name = "SanDisk USB Drive (32G)"

    class _FakeDevices:
        def list_block_devices(self):
            return [_FakeBlockDevice()]

        def list_serial_devices(self):
            return []

    context.devices = _FakeDevices()
    result = MIAApplication._action_list_connected_devices(context, {})
    assert "SanDisk USB Drive" in result


def test_list_scripts_empty(context):
    assert "no saved scripts" in MIAApplication._action_list_scripts(context, {}).lower()


def test_list_scripts_returns_all(context):
    context.scripts.add_script(name="Backup", interpreter="shell", category="Maintenance")
    result = MIAApplication._action_list_scripts(context, {})
    assert "Backup" in result and "shell" in result


def test_list_scripts_query_filters(context):
    context.scripts.add_script(name="Backup", interpreter="shell")
    context.scripts.add_script(name="Deploy", interpreter="python")
    result = MIAApplication._action_list_scripts(context, {"query": "backup"})
    assert "Backup" in result
    assert "Deploy" not in result


# ----------------------------------------------------------------------
# Profiles (list only — no switch_profile, see core/application.py's
# _register_assistant_actions() docstring comment on why)
# ----------------------------------------------------------------------

def test_list_profiles_empty(context):
    assert "no profiles" in MIAApplication._action_list_profiles(context, {}).lower()


def test_list_profiles_returns_all(context):
    context.profiles.create_profile(name="Zac", make_active=True)
    context.profiles.create_profile(name="Guest", make_active=False)
    result = MIAApplication._action_list_profiles(context, {})
    assert "Zac" in result and "Guest" in result


def test_list_profiles_marks_active_profile(context):
    context.profiles.create_profile(name="Zac", make_active=True)
    context.profiles.create_profile(name="Guest", make_active=False)
    result = MIAApplication._action_list_profiles(context, {})
    zac_line = next(line for line in result.splitlines() if "Zac" in line)
    guest_line = next(line for line in result.splitlines() if "Guest" in line)
    assert "active" in zac_line.lower()
    assert "active" not in guest_line.lower()


def test_list_profiles_shows_password_lock_marker(context):
    context.profiles.create_profile(name="Zac", password="secret123")
    result = MIAApplication._action_list_profiles(context, {})
    assert "\U0001F512" in result


# ----------------------------------------------------------------------
# Security tab tools (hash identifier, password strength, subnet
# calculator, port scanner) — pure functions, no manager state needed
# beyond `context` itself.
# ----------------------------------------------------------------------

def test_identify_hash_requires_a_value(context):
    result = MIAApplication._action_identify_hash(context, {})
    assert "hash value" in result.lower()


def test_identify_hash_returns_match(context):
    result = MIAApplication._action_identify_hash(context, {"value": "$2b$12$abcdefghijklmnopqrstuv"})
    assert "bcrypt" in result.lower()


def test_identify_hash_no_match(context):
    result = MIAApplication._action_identify_hash(context, {"value": "not-a-real-hash"})
    assert "no known hash format" in result.lower()


def test_check_password_strength_requires_a_password(context):
    result = MIAApplication._action_check_password_strength(context, {})
    assert "password" in result.lower()


def test_check_password_strength_weak(context):
    result = MIAApplication._action_check_password_strength(context, {"password": "password"})
    assert "Very Weak" in result


def test_check_password_strength_strong(context):
    result = MIAApplication._action_check_password_strength(context, {"password": "Tr0ub4dour&3xtra-Long!"})
    assert "Strong" in result  # "Very Strong" or "Strong" both contain "Strong"


def test_calculate_subnet_requires_a_cidr(context):
    result = MIAApplication._action_calculate_subnet(context, {})
    assert "cidr" in result.lower()


def test_calculate_subnet_valid(context):
    result = MIAApplication._action_calculate_subnet(context, {"cidr": "192.168.1.0/24"})
    assert "192.168.1.255" in result
    assert "254" in result


def test_calculate_subnet_invalid(context):
    result = MIAApplication._action_calculate_subnet(context, {"cidr": "not-a-cidr"})
    assert "invalid" in result.lower()


def test_scan_ports_requires_a_host(context):
    result = MIAApplication._action_scan_ports(context, {})
    assert "host" in result.lower()


def test_scan_ports_checks_the_three_fixed_ports_and_reports_open_ones(context, monkeypatch):
    # Mocked rather than binding a real listener: all 3 of the fixed
    # ports this handler checks (22/80/443) are privileged (<1024) and
    # can't be bound without root — the real TCP-scanning mechanics are
    # already covered by tests/test_port_scanner.py's ephemeral-port
    # tests. This test only verifies _action_scan_ports' own behavior:
    # which ports it asks for, and how it formats the result.
    import core.application as application_module
    from core.port_scanner import PortScanResult

    captured = {}

    def _fake_scan_ports(host, ports=None, timeout=None):
        captured["host"] = host
        captured["ports"] = ports
        captured["timeout"] = timeout
        return PortScanResult(host=host, open_ports=[22, 443], scanned_count=len(ports))

    monkeypatch.setattr(application_module, "scan_ports", _fake_scan_ports)

    result = MIAApplication._action_scan_ports(context, {"host": "192.168.1.1"})

    assert captured["ports"] == [22, 80, 443]
    assert captured["host"] == "192.168.1.1"
    assert "22" in result and "443" in result
    assert "80" not in result.split("checked")[0]  # 80 wasn't reported open, only mentioned in "checked (...)"


def test_scan_ports_reports_no_open_ports(context, monkeypatch):
    import core.application as application_module
    from core.port_scanner import PortScanResult

    monkeypatch.setattr(
        application_module, "scan_ports",
        lambda host, ports=None, timeout=None: PortScanResult(host=host, open_ports=[], scanned_count=len(ports)),
    )
    result = MIAApplication._action_scan_ports(context, {"host": "192.168.1.1"})
    assert "no open ports" in result.lower()


def test_scan_ports_reports_resolution_error(context, monkeypatch):
    import core.application as application_module
    from core.port_scanner import PortScanResult

    monkeypatch.setattr(
        application_module, "scan_ports",
        lambda host, ports=None, timeout=None: PortScanResult(host=host, error=f"Could not resolve '{host}'"),
    )
    result = MIAApplication._action_scan_ports(context, {"host": "bogus.invalid"})
    assert "could not resolve" in result.lower()


# ----------------------------------------------------------------------
# Project Manager (Projects, Tasks)
# ----------------------------------------------------------------------

def test_add_project_requires_a_name(context):
    result = MIAApplication._action_add_project(context, {})
    assert "name" in result.lower()
    assert context.projects.all_projects() == []


def test_add_project_creates_project(context):
    result = MIAApplication._action_add_project(context, {"name": "Garage Rewire", "status": "Active"})
    assert "Garage Rewire" in result
    projects = context.projects.all_projects()
    assert len(projects) == 1
    assert projects[0].status == "Active"


def test_add_project_unrecognized_status_falls_back_to_planning(context):
    MIAApplication._action_add_project(context, {"name": "X", "status": "Bogus"})
    assert context.projects.all_projects()[0].status == "Planning"


def test_list_projects_empty(context):
    assert "no projects" in MIAApplication._action_list_projects(context, {}).lower()


def test_list_projects_returns_all(context):
    context.projects.add_project(name="Garage Rewire", status="Active", due_date="2026-08-14")
    result = MIAApplication._action_list_projects(context, {})
    assert "Garage Rewire" in result and "Active" in result and "2026-08-14" in result


def test_add_task_requires_a_title(context):
    context.projects.add_project(name="Garage Rewire")
    result = MIAApplication._action_add_task(context, {"project_name": "Garage Rewire"})
    assert "title" in result.lower()
    assert context.tasks.tasks_for_project(context.projects.all_projects()[0].project_id) == []


def test_add_task_unknown_project_does_not_create_anything(context):
    result = MIAApplication._action_add_task(context, {"project_name": "Nonexistent", "title": "Buy fuse box"})
    assert "nonexistent" in result.lower()


def test_add_task_creates_task_under_project(context):
    project = context.projects.add_project(name="Garage Rewire")
    result = MIAApplication._action_add_task(
        context, {"project_name": "garage rewire", "title": "Buy fuse box", "due_date": "2026-08-10"}
    )
    assert "Buy fuse box" in result and "Garage Rewire" in result
    tasks = context.tasks.tasks_for_project(project.project_id)
    assert len(tasks) == 1
    assert tasks[0].due_date == "2026-08-10"


def test_list_tasks_empty(context):
    assert "no tasks" in MIAApplication._action_list_tasks(context, {}).lower()


def test_list_tasks_unknown_project_reports_not_found(context):
    result = MIAApplication._action_list_tasks(context, {"project_name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_list_tasks_filtered_by_project(context):
    project_a = context.projects.add_project(name="Garage Rewire")
    project_b = context.projects.add_project(name="Other Project")
    context.tasks.add_task(project_id=project_a.project_id, title="Buy fuse box")
    context.tasks.add_task(project_id=project_b.project_id, title="Unrelated task")

    result = MIAApplication._action_list_tasks(context, {"project_name": "Garage Rewire"})
    assert "Buy fuse box" in result and "Unrelated task" not in result


def test_list_tasks_all_projects_when_unfiltered(context):
    project_a = context.projects.add_project(name="Garage Rewire")
    project_b = context.projects.add_project(name="Other Project")
    context.tasks.add_task(project_id=project_a.project_id, title="Buy fuse box")
    context.tasks.add_task(project_id=project_b.project_id, title="Unrelated task")

    result = MIAApplication._action_list_tasks(context, {})
    assert "Buy fuse box" in result and "Unrelated task" in result


def test_delete_project_removes_matching_project(context):
    context.projects.add_project(name="Garage Rewire")
    result = MIAApplication._action_delete_project(context, {"name": "Garage Rewire"})
    assert "Garage Rewire" in result
    assert context.projects.all_projects() == []


def test_delete_project_is_case_insensitive(context):
    context.projects.add_project(name="Garage Rewire")
    MIAApplication._action_delete_project(context, {"name": "garage rewire"})
    assert context.projects.all_projects() == []


def test_delete_project_unknown_name_does_not_delete_anything(context):
    context.projects.add_project(name="Garage Rewire")
    result = MIAApplication._action_delete_project(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.projects.all_projects()) == 1


def test_delete_project_unlinks_but_does_not_delete_its_tasks(context):
    project = context.projects.add_project(name="Garage Rewire")
    context.tasks.add_task(project_id=project.project_id, title="Buy fuse box")
    MIAApplication._action_delete_project(context, {"name": "Garage Rewire"})
    assert len(context.tasks.all_tasks()) == 1


def test_delete_task_removes_matching_task(context):
    project = context.projects.add_project(name="Garage Rewire")
    context.tasks.add_task(project_id=project.project_id, title="Buy fuse box")
    result = MIAApplication._action_delete_task(context, {"title": "Buy fuse box"})
    assert "Buy fuse box" in result
    assert context.tasks.all_tasks() == []


def test_delete_task_is_case_insensitive(context):
    project = context.projects.add_project(name="Garage Rewire")
    context.tasks.add_task(project_id=project.project_id, title="Buy fuse box")
    MIAApplication._action_delete_task(context, {"title": "buy fuse box"})
    assert context.tasks.all_tasks() == []


def test_delete_task_unknown_title_does_not_delete_anything(context):
    project = context.projects.add_project(name="Garage Rewire")
    context.tasks.add_task(project_id=project.project_id, title="Buy fuse box")
    result = MIAApplication._action_delete_task(context, {"title": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.tasks.all_tasks()) == 1


def test_mark_task_done_defaults_to_true(context):
    project = context.projects.add_project(name="Garage Rewire")
    task = context.tasks.add_task(project_id=project.project_id, title="Buy fuse box")
    result = MIAApplication._action_mark_task_done(context, {"title": "Buy fuse box"})
    assert "Buy fuse box" in result and "as done" in result
    assert context.tasks.get_task(task.task_id).done is True


def test_mark_task_done_can_set_false(context):
    project = context.projects.add_project(name="Garage Rewire")
    task = context.tasks.add_task(project_id=project.project_id, title="Buy fuse box")
    context.tasks.toggle_done(task.task_id)
    result = MIAApplication._action_mark_task_done(context, {"title": "Buy fuse box", "done": False})
    assert "as not done" in result
    assert context.tasks.get_task(task.task_id).done is False


def test_mark_task_done_unknown_title_reports_not_found(context):
    result = MIAApplication._action_mark_task_done(context, {"title": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_recall_expedition_no_expeditions(context):
    assert "no expeditions" in MIAApplication._action_recall_expedition(context, {}).lower()


def test_recall_expedition_unknown_name_reports_not_found(context):
    context.expeditions.add_expedition(name="Field Season")
    result = MIAApplication._action_recall_expedition(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_recall_expedition_by_name(context):
    context.expeditions.add_expedition(name="Field Season", location="Land Between the Lakes", start_date="2026-08-14")
    result = MIAApplication._action_recall_expedition(context, {"name": "field season"})
    assert "Field Season" in result and "Land Between the Lakes" in result


def test_recall_expedition_defaults_to_most_recent(context):
    context.expeditions.add_expedition(name="Earlier", start_date="2026-07-01")
    context.expeditions.add_expedition(name="Later", start_date="2026-09-01")
    result = MIAApplication._action_recall_expedition(context, {})
    assert "Later" in result and "Earlier" not in result


def test_recall_expedition_includes_activity_and_distance(context):
    expedition = context.expeditions.add_expedition(name="Field Season", start_date="2026-08-14")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1", activity_type="Hiking")
    a = context.waypoints.add_waypoint(name="A", latitude=0.0, longitude=0.0)
    b = context.waypoints.add_waypoint(name="B", latitude=0.0, longitude=1.0)
    from datetime import datetime
    context.trips.record_split(trip.trip_id, a.waypoint_id, timestamp=datetime(2026, 8, 14, 8, 0, 0))
    context.trips.record_split(trip.trip_id, b.waypoint_id, timestamp=datetime(2026, 8, 14, 10, 0, 0))

    result = MIAApplication._action_recall_expedition(context, {"name": "Field Season"})
    assert "Hiking" in result and "km" in result


# ----------------------------------------------------------------------
# Missions (v0.18)
# ----------------------------------------------------------------------

def test_add_mission_requires_a_name(context):
    result = MIAApplication._action_add_mission(context, {})
    assert "name" in result.lower()
    assert context.missions.all_missions() == []


def test_add_mission_creates_mission(context):
    result = MIAApplication._action_add_mission(context, {"name": "Master Angler"})
    assert "Master Angler" in result
    missions = context.missions.all_missions()
    assert len(missions) == 1
    assert missions[0].trip_id is None


def test_add_mission_links_to_a_trip_by_name(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Fishing Day")

    result = MIAApplication._action_add_mission(context, {"name": "Master Angler", "trip_name": "fishing day"})
    assert "Master Angler" in result and "Fishing Day" in result
    assert context.missions.all_missions()[0].trip_id == trip.trip_id


def test_add_mission_unknown_trip_does_not_create_anything(context):
    result = MIAApplication._action_add_mission(context, {"name": "X", "trip_name": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert context.missions.all_missions() == []


def test_list_missions_empty(context):
    assert "no missions" in MIAApplication._action_list_missions(context, {}).lower()


def test_list_missions_includes_objective_progress(context):
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)
    context.missions.increment_tally(mission.mission_id, 0, delta=1.0)

    result = MIAApplication._action_list_missions(context, {})
    assert "Master Angler" in result and "Catch 3 fish" in result and "1 of 3" in result


def test_add_objective_requires_a_description(context):
    mission = context.missions.add_mission(name="Master Angler")
    result = MIAApplication._action_add_objective(
        context, {"mission_name": "Master Angler", "description": "", "target": 3}
    )
    assert "description" in result.lower()
    assert context.missions.get_mission(mission.mission_id).objectives == []


def test_add_objective_unknown_mission_does_not_create_anything(context):
    result = MIAApplication._action_add_objective(
        context, {"mission_name": "Nonexistent", "description": "Catch 3 fish", "target": 3}
    )
    assert "nonexistent" in result.lower()


def test_add_objective_creates_tally_objective(context):
    mission = context.missions.add_mission(name="Master Angler")
    result = MIAApplication._action_add_objective(
        context, {"mission_name": "master angler", "description": "Catch 3 fish", "metric_type": "tally", "target": 3}
    )
    assert "Catch 3 fish" in result and "Master Angler" in result
    reloaded = context.missions.get_mission(mission.mission_id)
    assert len(reloaded.objectives) == 1
    assert reloaded.objectives[0].metric_type == "tally"
    assert reloaded.objectives[0].target == 3.0


def test_add_objective_unrecognized_metric_type_falls_back_to_tally(context):
    mission = context.missions.add_mission(name="X")
    MIAApplication._action_add_objective(
        context, {"mission_name": "X", "description": "Bogus", "metric_type": "not_a_real_metric", "target": 1}
    )
    assert context.missions.get_mission(mission.mission_id).objectives[0].metric_type == "tally"


def test_log_mission_progress_unknown_mission_reports_not_found(context):
    result = MIAApplication._action_log_mission_progress(context, {"mission_name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_log_mission_progress_defaults_to_the_only_tally_objective(context):
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    result = MIAApplication._action_log_mission_progress(context, {"mission_name": "Master Angler"})
    assert "Catch 3 fish" in result and "1 of 3" in result
    assert context.missions.objective_progress(mission.mission_id, 0) == 1.0


def test_log_mission_progress_reports_completion(context):
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 1 fish", "tally", 1.0)

    result = MIAApplication._action_log_mission_progress(context, {"mission_name": "Master Angler"})
    assert "complete" in result.lower()


def test_log_mission_progress_ambiguous_without_objective_description(context):
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)
    context.missions.add_objective(mission.mission_id, "Identify 2 species", "tally", 2.0)

    result = MIAApplication._action_log_mission_progress(context, {"mission_name": "Master Angler"})
    assert "which one" in result.lower()
    assert context.missions.objective_progress(mission.mission_id, 0) == 0.0
    assert context.missions.objective_progress(mission.mission_id, 1) == 0.0


def test_log_mission_progress_resolves_by_objective_description(context):
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)
    context.missions.add_objective(mission.mission_id, "Identify 2 species", "tally", 2.0)

    MIAApplication._action_log_mission_progress(
        context, {"mission_name": "Master Angler", "objective_description": "identify 2 species", "delta": 2}
    )
    assert context.missions.objective_progress(mission.mission_id, 1) == 2.0
    assert context.missions.objective_progress(mission.mission_id, 0) == 0.0


def test_log_mission_progress_unknown_objective_description(context):
    mission = context.missions.add_mission(name="Master Angler")
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3.0)

    result = MIAApplication._action_log_mission_progress(
        context, {"mission_name": "Master Angler", "objective_description": "Bogus objective"}
    )
    assert "bogus objective" in result.lower()


def test_delete_mission_removes_matching_mission(context):
    context.missions.add_mission(name="Master Angler")
    result = MIAApplication._action_delete_mission(context, {"name": "Master Angler"})
    assert "Master Angler" in result
    assert context.missions.all_missions() == []


def test_delete_mission_unknown_name_does_not_delete_anything(context):
    context.missions.add_mission(name="Master Angler")
    result = MIAApplication._action_delete_mission(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.missions.all_missions()) == 1


def test_complete_mission_sets_status(context):
    mission = context.missions.add_mission(name="Master Angler")
    result = MIAApplication._action_complete_mission(context, {"name": "Master Angler"})
    assert "Master Angler" in result
    assert context.missions.get_mission(mission.mission_id).status == "completed"


def test_complete_mission_unknown_name_reports_not_found(context):
    result = MIAApplication._action_complete_mission(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


# ----------------------------------------------------------------------
# Workshop production pipeline: Materials, Jobs, Products, Ledger
# ----------------------------------------------------------------------

def test_add_material_requires_a_name(context):
    result = MIAApplication._action_add_material(context, {})
    assert "name" in result.lower()
    assert context.materials.all_materials() == []


def test_add_material_creates_material(context):
    result = MIAApplication._action_add_material(context, {"name": "Plywood", "unit": "sheet", "quantity_on_hand": 10})
    assert "Plywood" in result and "10" in result
    assert len(context.materials.all_materials()) == 1


def test_list_materials_empty(context):
    assert "no materials" in MIAApplication._action_list_materials(context, {}).lower()


def test_list_materials_returns_all(context):
    context.materials.add_material(name="Plywood", unit="sheet", quantity_on_hand=10)
    result = MIAApplication._action_list_materials(context, {})
    assert "Plywood" in result and "10" in result


def test_add_product_requires_a_name(context):
    result = MIAApplication._action_add_product(context, {})
    assert "name" in result.lower()
    assert context.products.all_products() == []


def test_add_product_creates_product(context):
    result = MIAApplication._action_add_product(context, {"name": "Birdhouse", "quantity_in_stock": 2})
    assert "Birdhouse" in result
    assert len(context.products.all_products()) == 1


def test_list_products_empty(context):
    assert "no products" in MIAApplication._action_list_products(context, {}).lower()


def test_add_job_requires_a_name(context):
    result = MIAApplication._action_add_job(context, {})
    assert "name" in result.lower()
    assert context.jobs.all_jobs() == []


def test_add_job_creates_job(context):
    result = MIAApplication._action_add_job(context, {"name": "Birdhouse Batch"})
    assert "Birdhouse Batch" in result
    assert len(context.jobs.all_jobs()) == 1


def test_list_jobs_empty(context):
    assert "no jobs" in MIAApplication._action_list_jobs(context, {}).lower()


def test_consume_material_deducts_material_stock(context):
    job = context.jobs.add_job(name="Birdhouse Batch")
    material = context.materials.add_material(name="Plywood", quantity_on_hand=10)
    result = MIAApplication._action_consume_material(
        context, {"job_name": "Birdhouse Batch", "material_name": "Plywood", "quantity": 4}
    )
    assert "4" in result and "Plywood" in result and "Birdhouse Batch" in result
    assert context.materials.get_material(material.material_id).quantity_on_hand == 6


def test_consume_material_unknown_job_reports_not_found(context):
    context.materials.add_material(name="Plywood", quantity_on_hand=10)
    result = MIAApplication._action_consume_material(
        context, {"job_name": "Nonexistent", "material_name": "Plywood", "quantity": 4}
    )
    assert "nonexistent" in result.lower()


def test_consume_material_unknown_material_reports_not_found(context):
    context.jobs.add_job(name="Birdhouse Batch")
    result = MIAApplication._action_consume_material(
        context, {"job_name": "Birdhouse Batch", "material_name": "Nonexistent", "quantity": 4}
    )
    assert "nonexistent" in result.lower()


def test_produce_product_credits_product_stock(context):
    job = context.jobs.add_job(name="Birdhouse Batch")
    product = context.products.add_product(name="Birdhouse", quantity_in_stock=2)
    result = MIAApplication._action_produce_product(
        context, {"job_name": "Birdhouse Batch", "product_name": "Birdhouse", "quantity": 3}
    )
    assert "3" in result and "Birdhouse" in result
    assert context.products.get_product(product.product_id).quantity_in_stock == 5


def test_record_sale_deducts_stock_and_logs_revenue(context):
    product = context.products.add_product(name="Birdhouse", quantity_in_stock=5)
    result = MIAApplication._action_record_sale(
        context, {"product_name": "Birdhouse", "quantity": 2, "amount": 50.0}
    )
    assert "2" in result and "Birdhouse" in result and "50.00" in result
    assert context.products.get_product(product.product_id).quantity_in_stock == 3
    assert context.ledger.total_revenue() == 50.0


def test_record_sale_unknown_product_reports_not_found(context):
    result = MIAApplication._action_record_sale(
        context, {"product_name": "Nonexistent", "quantity": 2, "amount": 50.0}
    )
    assert "nonexistent" in result.lower()


def test_get_ledger_summary_reports_revenue_expenses_and_profit(context):
    product = context.products.add_product(name="Birdhouse", quantity_in_stock=5)
    context.ledger.record_sale(product.product_id, quantity_sold=2, amount=50.0)
    context.ledger.add_expense(amount=10.0, description="Wood")
    result = MIAApplication._action_get_ledger_summary(context, {})
    assert "50.00" in result and "10.00" in result and "40.00" in result


# ----------------------------------------------------------------------
# Trail maps
# ----------------------------------------------------------------------

def _seed_trail_map(context, tmp_path, park_name, state, filename="map.pdf"):
    pdf_path = tmp_path / filename
    pdf_path.write_bytes(b"%PDF-1.4 fake trail map contents")
    return context.trail_maps.add_from_local_file(park_name, state, pdf_path)


def test_list_trail_maps_empty(context):
    result = MIAApplication._action_list_trail_maps(context, {})
    assert "no trail maps" in result.lower()


def test_list_trail_maps_returns_all(context, tmp_path):
    _seed_trail_map(context, tmp_path, "Mammoth Cave", "Kentucky", "mammoth.pdf")
    _seed_trail_map(context, tmp_path, "Great Smoky Mountains", "Tennessee", "smoky.pdf")
    result = MIAApplication._action_list_trail_maps(context, {})
    assert "Mammoth Cave" in result and "Great Smoky Mountains" in result


def test_list_trail_maps_search_filters_by_query(context, tmp_path):
    _seed_trail_map(context, tmp_path, "Mammoth Cave", "Kentucky", "mammoth.pdf")
    _seed_trail_map(context, tmp_path, "Great Smoky Mountains", "Tennessee", "smoky.pdf")
    result = MIAApplication._action_list_trail_maps(context, {"query": "smoky"})
    assert "Great Smoky Mountains" in result and "Mammoth Cave" not in result


def test_add_trail_map_from_url_requires_all_fields(context):
    result = MIAApplication._action_add_trail_map_from_url(context, {"park_name": "Mammoth Cave"})
    assert "need" in result.lower()
    assert context.trail_maps.all_trail_maps() == []


def test_add_trail_map_from_url_rejects_non_pdf_response(context, monkeypatch):
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            return b"<html>not a pdf</html>"

    monkeypatch.setattr(trail_map_library_module.urllib.request, "urlopen", lambda *a, **k: _FakeResponse())
    result = MIAApplication._action_add_trail_map_from_url(
        context, {"park_name": "Mammoth Cave", "state": "Kentucky", "url": "https://example.com/map.pdf"}
    )
    assert "doesn't look like a real" in result.lower()
    assert context.trail_maps.all_trail_maps() == []


def test_add_trail_map_from_url_adds_a_real_pdf_response(context, monkeypatch):
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            return b"%PDF-1.4 fake trail map contents"

    monkeypatch.setattr(trail_map_library_module.urllib.request, "urlopen", lambda *a, **k: _FakeResponse())
    result = MIAApplication._action_add_trail_map_from_url(
        context, {"park_name": "Mammoth Cave", "state": "Kentucky", "url": "https://example.com/map.pdf"}
    )
    assert "Mammoth Cave" in result
    assert len(context.trail_maps.all_trail_maps()) == 1


def test_delete_trail_map_removes_matching_map(context, tmp_path):
    _seed_trail_map(context, tmp_path, "Mammoth Cave", "Kentucky", "mammoth.pdf")
    result = MIAApplication._action_delete_trail_map(context, {"park_name": "mammoth cave"})
    assert "Mammoth Cave" in result
    assert context.trail_maps.all_trail_maps() == []


def test_delete_trail_map_unknown_name_reports_not_found(context):
    result = MIAApplication._action_delete_trail_map(context, {"park_name": "Nonexistent"})
    assert "nonexistent" in result.lower()


# ----------------------------------------------------------------------
# Expeditions / trips — delete, gear, summary
# ----------------------------------------------------------------------

def test_delete_expedition_removes_matching_expedition(context):
    context.expeditions.add_expedition(name="Field Season")
    result = MIAApplication._action_delete_expedition(context, {"name": "field season"})
    assert "Field Season" in result
    assert context.expeditions.all_expeditions() == []


def test_delete_expedition_unknown_name_reports_not_found(context):
    result = MIAApplication._action_delete_expedition(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_delete_trip_removes_matching_trip(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    result = MIAApplication._action_delete_trip(context, {"name": "day 1"})
    assert "Day 1" in result
    assert context.trips.all_trips() == []


def test_delete_trip_unknown_name_reports_not_found(context):
    result = MIAApplication._action_delete_trip(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_toggle_gear_packed_marks_item_packed(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    context.trips.add_gear_item(trip.trip_id, label="Tent")
    result = MIAApplication._action_toggle_gear_packed(context, {"trip_name": "day 1", "label": "tent"})
    assert "packed" in result.lower() and "not packed" not in result.lower()
    reloaded = context.trips.get_trip(trip.trip_id)
    assert reloaded.gear[0].packed is True


def test_toggle_gear_packed_toggles_back_to_not_packed(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    context.trips.add_gear_item(trip.trip_id, label="Tent")
    MIAApplication._action_toggle_gear_packed(context, {"trip_name": "Day 1", "label": "Tent"})
    result = MIAApplication._action_toggle_gear_packed(context, {"trip_name": "Day 1", "label": "Tent"})
    assert "not packed" in result.lower()


def test_toggle_gear_packed_unknown_trip_reports_not_found(context):
    result = MIAApplication._action_toggle_gear_packed(context, {"trip_name": "Nonexistent", "label": "Tent"})
    assert "nonexistent" in result.lower()


def test_toggle_gear_packed_unknown_label_reports_not_found(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    result = MIAApplication._action_toggle_gear_packed(context, {"trip_name": "Day 1", "label": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_get_trip_summary_unknown_name_reports_not_found(context):
    result = MIAApplication._action_get_trip_summary(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_get_trip_summary_reports_no_data_yet(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    result = MIAApplication._action_get_trip_summary(context, {"name": "Day 1"})
    assert "no distance" in result.lower()


def test_get_trip_summary_reports_planned_route_distance(context):
    expedition = context.expeditions.add_expedition(name="Field Season")
    trip = context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day 1")
    context.waypoints.add_waypoint(name="Home", latitude=40.0, longitude=-83.0)
    context.waypoints.add_waypoint(name="Cabin", latitude=41.5, longitude=-84.5)
    home = next(w for w in context.waypoints.all_waypoints() if w.name == "Home")
    cabin = next(w for w in context.waypoints.all_waypoints() if w.name == "Cabin")
    context.trips.add_waypoint_to_route(trip.trip_id, home.waypoint_id)
    context.trips.add_waypoint_to_route(trip.trip_id, cabin.waypoint_id)
    result = MIAApplication._action_get_trip_summary(context, {"name": "Day 1"})
    assert "Planned route distance" in result


# ----------------------------------------------------------------------
# Sun / moon
# ----------------------------------------------------------------------

def test_get_sun_moon_info_unknown_waypoint_reports_not_found(context):
    result = MIAApplication._action_get_sun_moon_info(context, {"waypoint_name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_get_sun_moon_info_returns_summary_for_known_waypoint(context):
    context.waypoints.add_waypoint(name="Cabin", latitude=41.5, longitude=-84.5)
    result = MIAApplication._action_get_sun_moon_info(context, {"waypoint_name": "cabin"})
    assert "Cabin" in result
    assert "Sunrise" in result or "unavailable" in result.lower()


# ----------------------------------------------------------------------
# Toolbox — unit conversion, Ohm's Law
# ----------------------------------------------------------------------

def test_convert_units_requires_from_and_to(context):
    result = MIAApplication._action_convert_units(context, {"value": 5, "from_unit": "miles"})
    assert "need" in result.lower()


def test_convert_units_requires_a_numeric_value(context):
    result = MIAApplication._action_convert_units(context, {"value": "abc", "from_unit": "miles", "to_unit": "km"})
    assert "numeric" in result.lower()


def test_convert_units_miles_to_kilometers(context):
    result = MIAApplication._action_convert_units(context, {"value": 1, "from_unit": "miles", "to_unit": "kilometers"})
    assert "1.609" in result


def test_convert_units_celsius_to_fahrenheit(context):
    result = MIAApplication._action_convert_units(context, {"value": 0, "from_unit": "celsius", "to_unit": "fahrenheit"})
    assert "32" in result


def test_convert_units_unrecognized_unit_reports_not_found(context):
    result = MIAApplication._action_convert_units(context, {"value": 1, "from_unit": "bogus", "to_unit": "km"})
    assert "don't recognize" in result.lower()


def test_calculate_ohms_law_requires_solve_for(context):
    result = MIAApplication._action_calculate_ohms_law(context, {"current": 2, "resistance": 10})
    assert "solve for" in result.lower() or "need to know" in result.lower()


def test_calculate_ohms_law_solves_for_voltage(context):
    result = MIAApplication._action_calculate_ohms_law(context, {"solve_for": "voltage", "current": 2, "resistance": 10})
    assert "20" in result and "V" in result


def test_calculate_ohms_law_solves_for_current(context):
    result = MIAApplication._action_calculate_ohms_law(context, {"solve_for": "current", "voltage": 20, "resistance": 10})
    assert "2" in result


def test_calculate_ohms_law_missing_values_reports_need_more(context):
    result = MIAApplication._action_calculate_ohms_law(context, {"solve_for": "voltage", "current": 2})
    assert "need" in result.lower()


# ----------------------------------------------------------------------
# Observations
# ----------------------------------------------------------------------

def test_list_observations_nothing_open(context):
    result = MIAApplication._action_list_observations(context, {})
    assert "nothing open" in result.lower()


def test_list_observations_returns_open_insights_with_recommendations(context):
    insight = context.insights.create_insight_if_new(
        source_type="maintenance", source_id="t1", kind="overdue",
        title="Oil change", message="'Oil change' is overdue by 10 days.",
    )
    context.insights.add_recommendation(insight.insight_id, "Mark it complete, or reschedule it.")

    result = MIAApplication._action_list_observations(context, {})
    assert "[maintenance]" in result
    assert "overdue by 10 days" in result
    assert "Recommendation: Mark it complete" in result


def test_list_observations_excludes_resolved(context):
    insight = context.insights.create_insight_if_new(
        source_type="maintenance", source_id="t1", kind="overdue",
        title="Oil change", message="'Oil change' is overdue by 10 days.",
    )
    context.insights.resolve_insight(insight.insight_id)

    result = MIAApplication._action_list_observations(context, {})
    assert "nothing open" in result.lower()


def test_list_observations_no_service_reports_unavailable(context):
    context.insights = None
    result = MIAApplication._action_list_observations(context, {})
    assert "not available" in result.lower() or "aren't available" in result.lower()
