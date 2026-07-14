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
import core.journal_manager as journal_manager_module
import core.script_library_manager as script_library_manager_module
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
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.profile_manager import ProfileManager
from core.script_library_manager import ScriptLibraryManager
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

    ctx = AppContext(config=ConfigManager(), events=EventBus())
    ctx.config.set("trips.photo_root_path", str(tmp_path / "trip_photos"))
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
