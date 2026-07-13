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
import core.inventory_manager as inventory_manager_module
import core.journal_manager as journal_manager_module
import core.waypoint_manager as waypoint_manager_module
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.application import MIAApplication
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.waypoint_manager import WaypointManager


@pytest.fixture
def context(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(alarm_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(alarm_manager_module, "_ALARMS_FILE", data_dir / "alarms.json")
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", data_dir / "journal_entries.json")
    monkeypatch.setattr(inventory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(inventory_manager_module, "_ITEMS_FILE", data_dir / "inventory_items.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")

    ctx = AppContext(config=ConfigManager(), events=EventBus())
    ctx.alarms = AlarmManager(ctx)
    ctx.journal = JournalManager(ctx)
    ctx.inventory = InventoryManager(ctx)
    ctx.waypoints = WaypointManager(ctx)
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
