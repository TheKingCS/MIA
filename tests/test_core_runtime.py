"""
tests.test_core_runtime
==========================

Unit tests for core.core_runtime — headless MIA Core's build_core_context()
and its curated Assistant action handlers (_action_*). These are
independent copies of core/application.py's own staticmethods (see
that module's docstring for why), so this mirrors
tests/test_assistant_action_handlers.py's exact fixture/isolation
pattern — real manager instances with data dirs isolated to tmp_path,
no Qt, no LLM, no MIAApplication instance needed. Uses the real
build_core_context() entry point itself as the fixture (not hand-wired
managers) so a wiring mistake in that function would actually be
caught here, not just in the handler tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import core.alarm_manager as alarm_manager_module
import core.calendar_manager as calendar_manager_module
import core.config_manager as config_manager_module
import core.expedition_manager as expedition_manager_module
import core.inventory_manager as inventory_manager_module
import core.journal_manager as journal_manager_module
import core.mission_manager as mission_manager_module
import core.notification_manager as notification_manager_module
import core.trip_manager as trip_manager_module
import core.user_memory_manager as user_memory_manager_module
import core.waypoint_manager as waypoint_manager_module
import core.activity_log_manager as activity_log_manager_module
from core.config_manager import ConfigManager
from core.core_runtime import (
    _action_add_alarm,
    _action_add_calendar_event,
    _action_add_inventory_item,
    _action_add_mission,
    _action_add_note,
    _action_add_objective,
    _action_add_waypoint,
    _action_adjust_inventory_quantity,
    _action_complete_mission,
    _action_delete_alarm,
    _action_delete_calendar_event,
    _action_delete_inventory_item,
    _action_delete_mission,
    _action_delete_note,
    _action_get_power_status,
    _action_get_system_health,
    _action_list_alarms,
    _action_list_calendar_events,
    _action_list_inventory,
    _action_list_missions,
    _action_list_notes,
    _action_list_waypoints,
    _action_log_mission_progress,
    _action_recall_recent_activity,
    _action_waypoint_distance,
    build_core_context,
)
from core.event_bus import EventBus


@pytest.fixture
def context(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    # Same real reason test_assistant_action_handlers.py's own fixture
    # isolates this: several handlers/managers call context.config.save()
    # for real (e.g. ProfileManager) — without this, a throwaway test
    # write would land in the actual config/config.json.
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    # 2026-09-28: Core also loads what "remind me why" reads.
    import core.budget_manager, core.intent_manager, core.project_manager, core.real_estate_manager, core.why_graph
    for _module in (core.budget_manager, core.intent_manager, core.project_manager, core.real_estate_manager,
                    core.why_graph):
        _original = _module._DATA_DIR
        for _attr, _value in list(vars(_module).items()):
            if isinstance(_value, Path) and (_value == _original or _original in _value.parents):
                monkeypatch.setattr(_module, _attr, data_dir / _value.relative_to(_original))
    monkeypatch.setattr(notification_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(notification_manager_module, "_NOTIFICATIONS_FILE", data_dir / "notifications.json")
    monkeypatch.setattr(calendar_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(calendar_manager_module, "_EVENTS_FILE", data_dir / "calendar_events.json")
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
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(user_memory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(user_memory_manager_module, "_USER_MEMORIES_FILE", data_dir / "user_memories.json")
    monkeypatch.setattr(activity_log_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(activity_log_manager_module, "_ACTIVITY_LOG_FILE", data_dir / "activity_log.json")

    return build_core_context(ConfigManager(), EventBus())


# ----------------------------------------------------------------------
# build_core_context — the real wiring, not just individual handlers
# ----------------------------------------------------------------------

def test_build_core_context_constructs_every_manager_the_handlers_need(context):
    # A crash here (AttributeError on any of these) is exactly the same
    # bug class as the Power-module context.energy crash found earlier
    # this session — a manager the handlers reach through context.*
    # silently missing from construction.
    assert context.alarms is not None
    assert context.journal is not None
    assert context.inventory is not None
    assert context.calendar is not None
    assert context.waypoints is not None
    assert context.missions is not None
    assert context.trips is not None
    assert context.activity_log is not None


def test_build_core_context_registers_the_curated_action_set(context):
    registered = set(context.assistant_actions._actions.keys())
    expected = {
        "add_alarm", "list_alarms", "delete_alarm",
        "add_note", "list_notes", "delete_note",
        "add_inventory_item", "list_inventory", "delete_inventory_item", "adjust_inventory_quantity",
        "add_calendar_event", "list_calendar_events", "delete_calendar_event",
        "add_waypoint", "list_waypoints", "waypoint_distance",
        "add_mission", "list_missions", "add_objective", "log_mission_progress",
        "delete_mission", "complete_mission",
        "get_power_status", "get_system_health", "recall_recent_activity",
    }
    assert expected <= registered


def test_build_core_context_excludes_gui_only_actions(context):
    """Deliberate exclusions per this module's own docstring — no
    screen to navigate on headless Core."""
    registered = set(context.assistant_actions._actions.keys())
    assert "open_module" not in registered
    assert "set_theme" not in registered


def test_registered_actions_dispatch_through_execute_to_the_real_handler(context):
    """Confirms _register_core_assistant_actions() wired the right
    handler to the right name — not just that the handler function
    itself works in isolation (the tests below), but that the real
    registry.execute() dispatch path actually reaches it."""
    result = context.assistant_actions.execute(context, "add_alarm", {"label": "Wake Up", "time": "07:00"})
    assert "Wake Up" in result and "07:00" in result
    assert len(context.alarms.all_alarms()) == 1


# ----------------------------------------------------------------------
# Alarms
# ----------------------------------------------------------------------

def test_add_alarm_requires_a_time(context):
    result = _action_add_alarm(context, {"label": "Wake Up"})
    assert "time" in result.lower()
    assert context.alarms.all_alarms() == []


def test_add_alarm_creates_alarm(context):
    result = _action_add_alarm(context, {"label": "Wake Up", "time": "07:00"})
    assert "Wake Up" in result and "07:00" in result
    assert len(context.alarms.all_alarms()) == 1


def test_list_alarms_empty(context):
    assert "no alarms" in _action_list_alarms(context, {}).lower()


def test_list_alarms_returns_all(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    context.alarms.add_alarm(label="Lunch", time="12:00")
    result = _action_list_alarms(context, {})
    assert "Wake Up" in result and "07:00" in result
    assert "Lunch" in result and "12:00" in result


def test_delete_alarm_removes_matching_alarm(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    result = _action_delete_alarm(context, {"label": "Wake Up"})
    assert "Wake Up" in result
    assert context.alarms.all_alarms() == []


def test_delete_alarm_is_case_insensitive(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    _action_delete_alarm(context, {"label": "wake up"})
    assert context.alarms.all_alarms() == []


def test_delete_alarm_unknown_label_does_not_delete_anything(context):
    context.alarms.add_alarm(label="Wake Up", time="07:00")
    result = _action_delete_alarm(context, {"label": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert len(context.alarms.all_alarms()) == 1


# ----------------------------------------------------------------------
# Notes
# ----------------------------------------------------------------------

def test_add_note_requires_a_title(context):
    result = _action_add_note(context, {"body": "buy milk"})
    assert "title" in result.lower()
    assert context.journal.all_entries() == []


def test_add_note_creates_entry(context):
    result = _action_add_note(context, {"title": "Groceries", "body": "buy milk"})
    assert "Groceries" in result
    assert len(context.journal.all_entries()) == 1


def test_list_notes_empty(context):
    assert "no notes" in _action_list_notes(context, {}).lower()


def test_list_notes_returns_all_without_a_query(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    context.journal.add_entry(title="Ideas", body="")
    result = _action_list_notes(context, {})
    assert "Groceries" in result and "buy milk" in result
    assert "Ideas" in result


def test_list_notes_query_no_match(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    result = _action_list_notes(context, {"query": "zzz_no_match"})
    assert "no matching" in result.lower()


def test_delete_note_removes_matching_entry(context):
    context.journal.add_entry(title="Groceries", body="buy milk")
    result = _action_delete_note(context, {"title": "Groceries"})
    assert "Groceries" in result
    assert context.journal.all_entries() == []


def test_delete_note_unknown_title(context):
    result = _action_delete_note(context, {"title": "Nonexistent"})
    assert "nonexistent" in result.lower()


# ----------------------------------------------------------------------
# Inventory
# ----------------------------------------------------------------------

def test_add_inventory_item_requires_a_name(context):
    result = _action_add_inventory_item(context, {"quantity": 5})
    assert "name" in result.lower()
    assert context.inventory.all_items() == []


def test_add_inventory_item_creates_item_with_quantity(context):
    result = _action_add_inventory_item(context, {"name": "M3 bolts", "quantity": 10})
    assert "10" in result and "M3 bolts" in result
    assert len(context.inventory.all_items()) == 1


def test_add_inventory_item_bad_quantity_defaults_to_zero(context):
    result = _action_add_inventory_item(context, {"name": "M3 bolts", "quantity": "not a number"})
    assert "0" in result and "M3 bolts" in result


def test_list_inventory_empty(context):
    assert "empty" in _action_list_inventory(context, {}).lower()


def test_list_inventory_returns_all(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    result = _action_list_inventory(context, {})
    assert "10" in result and "M3 bolts" in result


def test_delete_inventory_item_removes_matching_item(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    result = _action_delete_inventory_item(context, {"name": "M3 bolts"})
    assert "M3 bolts" in result
    assert context.inventory.all_items() == []


def test_delete_inventory_item_unknown_name(context):
    result = _action_delete_inventory_item(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_adjust_inventory_quantity_bad_delta(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    result = _action_adjust_inventory_quantity(context, {"name": "M3 bolts", "delta": "not a number"})
    assert "whole number" in result.lower()


def test_adjust_inventory_quantity_unknown_item(context):
    result = _action_adjust_inventory_quantity(context, {"name": "Nonexistent", "delta": -5})
    assert "nonexistent" in result.lower()


def test_adjust_inventory_quantity_subtracts(context):
    context.inventory.add_item(name="M3 bolts", quantity=10)
    result = _action_adjust_inventory_quantity(context, {"name": "M3 bolts", "delta": -5})
    assert "5" in result and "M3 bolts" in result


# ----------------------------------------------------------------------
# Calendar
# ----------------------------------------------------------------------

def test_add_calendar_event_requires_a_title(context):
    result = _action_add_calendar_event(context, {"date": "2026-09-01"})
    assert "title" in result.lower()
    assert context.calendar.all_events() == []


def test_add_calendar_event_requires_a_date(context):
    result = _action_add_calendar_event(context, {"title": "Dentist"})
    assert "date" in result.lower()
    assert context.calendar.all_events() == []


def test_add_calendar_event_creates_with_time(context):
    result = _action_add_calendar_event(context, {"title": "Dentist", "date": "2026-09-01", "time": "14:00"})
    assert "Dentist" in result and "2026-09-01" in result and "14:00" in result
    assert len(context.calendar.all_events()) == 1


def test_add_calendar_event_all_day_without_time(context):
    result = _action_add_calendar_event(context, {"title": "Holiday", "date": "2026-09-01"})
    assert "Holiday" in result
    assert "at" not in result.split("2026-09-01")[-1]


def test_list_calendar_events_empty(context):
    assert "no calendar events" in _action_list_calendar_events(context, {}).lower()


def test_list_calendar_events_returns_all(context):
    context.calendar.add_event(title="Dentist", date="2026-09-01", time="14:00")
    result = _action_list_calendar_events(context, {})
    assert "Dentist" in result and "2026-09-01" in result and "14:00" in result


def test_delete_calendar_event_removes_matching_event(context):
    context.calendar.add_event(title="Dentist", date="2026-09-01")
    result = _action_delete_calendar_event(context, {"title": "Dentist"})
    assert "Dentist" in result
    assert context.calendar.all_events() == []


def test_delete_calendar_event_unknown_title(context):
    result = _action_delete_calendar_event(context, {"title": "Nonexistent"})
    assert "nonexistent" in result.lower()


# ----------------------------------------------------------------------
# Waypoints
# ----------------------------------------------------------------------

def test_add_waypoint_requires_a_name(context):
    result = _action_add_waypoint(context, {"latitude": 44.0, "longitude": -110.1})
    assert "name" in result.lower()
    assert context.waypoints.all_waypoints() == []


def test_add_waypoint_requires_valid_coordinates(context):
    result = _action_add_waypoint(context, {"name": "Ridge Camp", "latitude": "not a number", "longitude": -110.1})
    assert "latitude" in result.lower() or "longitude" in result.lower()
    assert context.waypoints.all_waypoints() == []


def test_add_waypoint_creates_waypoint(context):
    result = _action_add_waypoint(context, {"name": "Ridge Camp", "latitude": 44.0, "longitude": -110.1})
    assert "Ridge Camp" in result
    assert len(context.waypoints.all_waypoints()) == 1


def test_add_waypoint_unknown_category_falls_back_silently(context):
    result = _action_add_waypoint(context, {
        "name": "Ridge Camp", "latitude": 44.0, "longitude": -110.1, "category": "Not A Real Category",
    })
    assert "Ridge Camp" in result
    assert context.waypoints.all_waypoints()[0].category == ""


def test_list_waypoints_empty(context):
    assert "no waypoints" in _action_list_waypoints(context, {}).lower()


def test_list_waypoints_query_filters(context):
    context.waypoints.add_waypoint(name="Ridge Camp", latitude=44.0, longitude=-110.1)
    context.waypoints.add_waypoint(name="Lake View", latitude=45.0, longitude=-111.0)
    result = _action_list_waypoints(context, {"query": "ridge"})
    assert "Ridge Camp" in result
    assert "Lake View" not in result


def test_waypoint_distance_unknown_from(context):
    context.waypoints.add_waypoint(name="Cabin", latitude=44.0, longitude=-110.1)
    result = _action_waypoint_distance(context, {"from_name": "Nonexistent", "to_name": "Cabin"})
    assert "nonexistent" in result.lower()


def test_waypoint_distance_unknown_to(context):
    context.waypoints.add_waypoint(name="Home", latitude=44.0, longitude=-110.1)
    result = _action_waypoint_distance(context, {"from_name": "Home", "to_name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_waypoint_distance_computes_real_distance(context):
    context.waypoints.add_waypoint(name="Home", latitude=44.0, longitude=-110.1)
    context.waypoints.add_waypoint(name="Cabin", latitude=44.5, longitude=-110.1)
    result = _action_waypoint_distance(context, {"from_name": "Home", "to_name": "Cabin"})
    assert "Home" in result and "Cabin" in result
    assert "km" in result and "bearing" in result.lower()


# ----------------------------------------------------------------------
# Missions
# ----------------------------------------------------------------------

def test_add_mission_requires_a_name(context):
    result = _action_add_mission(context, {})
    assert "name" in result.lower()
    assert context.missions.all_missions() == []


def test_add_mission_creates_mission(context):
    result = _action_add_mission(context, {"name": "Master Angler"})
    assert "Master Angler" in result
    assert len(context.missions.all_missions()) == 1


def test_add_mission_unknown_trip_name(context):
    result = _action_add_mission(context, {"name": "Master Angler", "trip_name": "Nonexistent"})
    assert "nonexistent" in result.lower()
    assert context.missions.all_missions() == []


def test_add_mission_links_to_a_real_trip(context):
    context.expeditions.add_expedition(name="Field Season")
    expedition = context.expeditions.all_expeditions()[0]
    context.trips.add_trip(expedition_id=expedition.expedition_id, name="Day One")
    result = _action_add_mission(context, {"name": "Master Angler", "trip_name": "Day One"})
    assert "Master Angler" in result and "Day One" in result


def test_list_missions_empty(context):
    assert "no missions" in _action_list_missions(context, {}).lower()


def test_list_missions_shows_objectives_and_progress(context):
    context.missions.add_mission(name="Master Angler")
    mission = context.missions.all_missions()[0]
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3)
    result = _action_list_missions(context, {})
    assert "Master Angler" in result
    assert "Catch 3 fish" in result
    assert "0 of 3" in result


def test_add_objective_requires_a_description(context):
    context.missions.add_mission(name="Master Angler")
    result = _action_add_objective(context, {"mission_name": "Master Angler", "target": 3})
    assert "description" in result.lower()


def test_add_objective_unknown_mission(context):
    result = _action_add_objective(context, {"mission_name": "Nonexistent", "description": "Catch 3 fish", "target": 3})
    assert "nonexistent" in result.lower()


def test_add_objective_bad_target(context):
    context.missions.add_mission(name="Master Angler")
    result = _action_add_objective(context, {
        "mission_name": "Master Angler", "description": "Catch 3 fish", "target": "not a number",
    })
    assert "numeric" in result.lower()


def test_add_objective_unknown_metric_type_falls_back_to_tally(context):
    context.missions.add_mission(name="Master Angler")
    _action_add_objective(context, {
        "mission_name": "Master Angler", "description": "Catch 3 fish",
        "metric_type": "not_a_real_type", "target": 3,
    })
    mission = context.missions.all_missions()[0]
    assert mission.objectives[0].metric_type == "tally"


def test_log_mission_progress_unknown_mission(context):
    result = _action_log_mission_progress(context, {"mission_name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_log_mission_progress_single_tally_objective_auto_resolves(context):
    context.missions.add_mission(name="Master Angler")
    mission = context.missions.all_missions()[0]
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3)
    result = _action_log_mission_progress(context, {"mission_name": "Master Angler"})
    assert "1 of 3" in result


def test_log_mission_progress_ambiguous_without_objective_description(context):
    context.missions.add_mission(name="Master Angler")
    mission = context.missions.all_missions()[0]
    context.missions.add_objective(mission.mission_id, "Catch 3 fish", "tally", 3)
    context.missions.add_objective(mission.mission_id, "Identify 2 species", "tally", 2)
    result = _action_log_mission_progress(context, {"mission_name": "Master Angler"})
    assert "2" in result and "tally objectives" in result.lower()


def test_log_mission_progress_completes_objective(context):
    context.missions.add_mission(name="Master Angler")
    mission = context.missions.all_missions()[0]
    context.missions.add_objective(mission.mission_id, "Catch 1 fish", "tally", 1)
    result = _action_log_mission_progress(context, {"mission_name": "Master Angler"})
    assert "complete" in result.lower()


def test_delete_mission_removes_matching_mission(context):
    context.missions.add_mission(name="Master Angler")
    result = _action_delete_mission(context, {"name": "Master Angler"})
    assert "Master Angler" in result
    assert context.missions.all_missions() == []


def test_delete_mission_unknown_name(context):
    result = _action_delete_mission(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


def test_complete_mission_marks_completed(context):
    context.missions.add_mission(name="Master Angler")
    result = _action_complete_mission(context, {"name": "Master Angler"})
    assert "completed" in result.lower()
    assert context.missions.all_missions()[0].status == "completed"


def test_complete_mission_unknown_name(context):
    result = _action_complete_mission(context, {"name": "Nonexistent"})
    assert "nonexistent" in result.lower()


# ----------------------------------------------------------------------
# Power
# ----------------------------------------------------------------------

def test_get_power_status_unavailable(context):
    # A fake backend, not a real PowerManager — same real reason
    # test_assistant_action_handlers.py's own equivalent test gives:
    # this sandbox's psutil reports a real host-passthrough battery
    # reading, so relying on real hardware state would be non-deterministic.
    class _FakeNoPower:
        def read(self):
            return None

    context.power = _FakeNoPower()
    result = _action_get_power_status(context, {})
    assert "not available" in result.lower() or "no battery" in result.lower()


def test_get_power_status_reports_reading(context):
    from core.power_manager import PowerStatus

    class _FakePower:
        def read(self):
            return PowerStatus(percent=87.0, plugged_in=False, seconds_left=3600)

    context.power = _FakePower()
    result = _action_get_power_status(context, {})
    assert "87" in result
    assert "battery" in result.lower()
    assert "60 minutes" in result


# ----------------------------------------------------------------------
# System health / recent activity
# ----------------------------------------------------------------------

def test_get_system_health_returns_formatted_snapshot(context):
    result = _action_get_system_health(context, {})
    assert isinstance(result, str)
    assert len(result) > 0


def test_recall_recent_activity_empty(context):
    assert "no recent activity" in _action_recall_recent_activity(context, {}).lower()


def test_recall_recent_activity_keyword_no_match(context):
    # Real event publish, not a direct private-method call — exercises
    # the same "module.opened" -> ActivityLogManager._on_module_opened()
    # -> _log() path production code actually goes through.
    context.events.publish("module.opened", module_id="notes")
    result = _action_recall_recent_activity(context, {"keyword": "zzz_no_match"})
    assert "no matching" in result.lower()


def test_recall_recent_activity_returns_entries(context):
    context.events.publish("module.opened", module_id="notes")
    result = _action_recall_recent_activity(context, {})
    assert "notes" in result.lower()


def test_perspective_works_on_core(context):
    """2026-09-28: "remind me why" on the headless voice loop gets the
    owner's own reasons, like on the desktop and the phone."""
    from core.assistant_turn import run_assistant_turn
    from core.conversation_manager import Conversation
    from core.conversation_modes import PERSPECTIVE
    from core.llm_manager import ChatReply

    factory = context.intents.add_intent("Factory work")
    freedom = context.intents.add_intent("Control over my time")
    context.intents.set_serves(factory.intent_id, freedom.intent_id, "the factory pays the bills")
    seen = []

    class FakeLLM:
        def chat_with_tools(self, messages, tools):
            seen.append((messages, tools))
            return ChatReply(content="Because it buys you your time back.")

        def generate(self, prompt):
            return ""

    context.llm = FakeLLM()
    conversation = Conversation(conversation_id="core")
    turn = run_assistant_turn(context, conversation, "Remind me why I'm doing all this")
    assert conversation.mode == PERSPECTIVE and turn.replies == ["Because it buys you your time back."]
    system = seen[0][0][0]["content"]
    assert "Control over my time" in system and "Factory work" in system
    assert "link_my_reason" in context.assistant_actions._actions
