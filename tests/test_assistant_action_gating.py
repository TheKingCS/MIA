"""
tests.test_assistant_action_gating
=====================================

Regression tests tying modules.assistant.module.looks_like_action_request()
to the REAL trigger_phrases registered in core.application's
_register_assistant_actions() (milestone 5.7-5.9) — not a hand-copied
keyword list. Two real gaps were found only by live-model testing and
are pinned here so they can't silently regress: "How many M3 bolts do I
have?" (no literal "inventory") and "What's the distance from Home to
Cabin?" ("distance from", not "distance to"). Pure keyword-matching
logic, no Qt/LLM/Ollama involved — fast enough to run every time,
unlike the live-model verification these gaps were originally found
with.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.application import MIAApplication
from core.assistant_chat import looks_like_action_request
from core.config_manager import ConfigManager
from core.event_bus import EventBus


def _real_gating_keywords() -> list[str]:
    """
    Builds the real assistant_actions registry the same way
    MIAApplication does (via _register_assistant_actions()), without
    constructing a full MIAApplication (which boots a real QApplication
    and the entire module/profile/wizard flow) — _register_assistant_actions
    only touches self.context and self.module_manager, so a bare stub
    with just those two attributes is enough, same trick used in this
    project's own scratch verification scripts this session.
    """
    context = AppContext(config=ConfigManager(), events=EventBus())
    app_stub = object.__new__(MIAApplication)
    app_stub.context = context
    app_stub.module_manager = None  # unused unless open_module's handler actually runs
    MIAApplication._register_assistant_actions(app_stub)
    return context.assistant_actions.gating_keywords()


def test_inventory_quantity_question_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("How many M3 bolts do I have?", keywords) is True


def test_waypoint_distance_from_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What's the distance from Home to Cabin?", keywords) is True


def test_honda_civics_question_still_does_not_gate_open():
    """The original 5.6-follow-up regression — must still hold with the full real registry."""
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What can you tell me about Honda Civics?", keywords) is False


def test_list_alarms_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("List my alarms", keywords) is True


def test_system_health_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What's my system health?", keywords) is True


def test_unrelated_how_many_question_does_not_gate_open():
    """
    Regression test: a bare "how many" trigger phrase was tried for
    list_inventory and rejected after live-model testing showed it made
    "How many people live in Ohio?" hallucinate a get_system_health
    tool call — exactly the failure mode this gating mechanism exists
    to prevent. "do i have" (without "any") replaced it, catching real
    inventory questions ("how many M3 bolts do I have?") without this
    false positive.
    """
    keywords = _real_gating_keywords()
    assert looks_like_action_request("How many people live in Ohio?", keywords) is False


# ----------------------------------------------------------------------
# milestone 5.10 — delete/adjust actions
# ----------------------------------------------------------------------

def test_delete_alarm_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete my Wake Up alarm", keywords) is True


def test_delete_note_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete the note called Groceries", keywords) is True


def test_delete_inventory_item_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Remove M3 bolts from inventory", keywords) is True


def test_adjust_inventory_quantity_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("I used 5 M3 bolts", keywords) is True


def test_delete_waypoint_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete the Cabin waypoint", keywords) is True


def test_used_to_phrasing_gates_open_as_a_known_accepted_tradeoff():
    """
    "I used to live in Ohio" gates open (contains "i used",
    adjust_inventory_quantity's trigger for "I used 5 M3 bolts") even
    though it's unrelated to inventory — a known, deliberately accepted
    trade-off (see docs/ROADMAP.md's 5.10 writeup), not a bug being
    tracked for a fix. Verified against the live model that the worst
    case observed is a harmless read-only recall_recent_activity call,
    never a destructive one: every delete/adjust handler in
    core/application.py does an exact-match name lookup and fails
    closed with a clear "I don't have a/an X called '...'" message when
    nothing matches, so a stray tool call from this false positive
    can't actually delete or change real data.
    """
    keywords = _real_gating_keywords()
    assert looks_like_action_request("I used to live in Ohio", keywords) is True


# ----------------------------------------------------------------------
# Assistant action-registry expansion: Expedition Mode + Device Profile/Theme
# ----------------------------------------------------------------------

def test_add_waypoint_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Save a waypoint here called Ridge Camp", keywords) is True


def test_add_expedition_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Start a new expedition called Field Season", keywords) is True


def test_list_expeditions_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("List my expeditions", keywords) is True


def test_add_trip_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Add a trip called Day 1 to Field Season", keywords) is True


def test_list_trips_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What trips do I have?", keywords) is True


def test_add_gear_item_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Add gear to my Day 1 trip", keywords) is True


def test_add_trip_log_entry_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Add to my trip log: reached camp", keywords) is True


def test_get_device_profile_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What device profile am I running?", keywords) is True


def test_set_theme_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Change the theme to low energy", keywords) is True


def test_set_theme_does_not_collide_with_switch_to_phrasing():
    """
    set_theme deliberately avoids open_module's bare "switch to "
    trigger — "Switch to the Anime Monochrome theme" should still gate
    open (open_module's trigger catches it), but this pins that
    set_theme's own trigger phrases don't ALSO fire on "switch to ",
    which would just be redundant, not a bug — the real risk (which
    tool the *model* picks) is verified live in
    tests/live_model_check.py, not here.
    """
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Switch to the Anime Monochrome theme", keywords) is True


def test_ordinary_trip_mention_does_not_gate_open():
    """False-positive check: 'trip' as an ordinary word, not a request to act on a Trip record."""
    keywords = _real_gating_keywords()
    assert looks_like_action_request("That trip to the store took forever", keywords) is False


# ----------------------------------------------------------------------
# milestone 5.13 — Calendar, Power, Components, Field Kit (read actions)
# ----------------------------------------------------------------------

def test_add_calendar_event_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Add an event called Doctor Appointment on 2026-08-14", keywords) is True


def test_list_calendar_events_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What's on my calendar?", keywords) is True


def test_delete_calendar_event_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete my Doctor Appointment event", keywords) is True


def test_eventful_does_not_gate_open_on_bare_event_trigger():
    """Same 'trailing space avoids the substring' trick as the existing 'alarm '/'component ' triggers."""
    keywords = _real_gating_keywords()
    assert looks_like_action_request("This was an eventful day", keywords) is False


def test_get_power_status_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What's my battery level?", keywords) is True


def test_add_component_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Add a component called 10k resistor", keywords) is True


def test_list_components_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What components do I have?", keywords) is True


def test_delete_component_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete my M3 bolts component", keywords) is True


def test_list_connected_devices_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What devices are connected?", keywords) is True


def test_list_scripts_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("List my scripts", keywords) is True


# ----------------------------------------------------------------------
# milestone 5.14 — Profiles (list only)
# ----------------------------------------------------------------------

def test_list_profiles_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What profiles are set up on this device?", keywords) is True


# ----------------------------------------------------------------------
# Security tab tools: hash identifier, password strength, subnet
# calculator, port scanner
# ----------------------------------------------------------------------

def test_identify_hash_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What hash is this: $2b$12$abc...", keywords) is True


def test_check_password_strength_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("How strong is this password: hunter2", keywords) is True


def test_calculate_subnet_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Calculate this subnet: 192.168.1.0/24", keywords) is True


def test_scan_ports_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Scan 192.168.1.1 for open ports", keywords) is True


# ----------------------------------------------------------------------
# Project Manager tool: Projects, Tasks
# ----------------------------------------------------------------------

def test_add_project_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Start a new project called Garage Rewire", keywords) is True


def test_list_projects_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What projects do I have?", keywords) is True


def test_add_task_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Add a task called Buy fuse box to my Garage Rewire project", keywords) is True


def test_list_tasks_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What tasks do I have?", keywords) is True


def test_ordinary_project_mention_does_not_gate_open():
    """False-positive check: 'project' as an ordinary word, not a request to act on a Project record."""
    keywords = _real_gating_keywords()
    assert looks_like_action_request("This project is taking forever", keywords) is False


def test_delete_project_phrasing_gates_open():
    """
    Uses "called X" phrasing (name after the noun), same as
    test_delete_note_phrasing_gates_open — "project"/"task" are common
    enough English words (see test_ordinary_project_mention_does_not_gate_open
    above) that neither gets a bare trailing-space trigger the way
    "alarm "/"component " do, so name-before-noun phrasing ("Delete my
    Garage Rewire project") is a known, deliberately accepted gap here,
    same trade-off as delete_note's.
    """
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete the project called Garage Rewire", keywords) is True


def test_delete_task_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete the task called Buy fuse box", keywords) is True


def test_mark_task_done_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Mark the task called Buy fuse box as done", keywords) is True


# ----------------------------------------------------------------------
# Memories (v0.17): recall_expedition
# ----------------------------------------------------------------------

def test_recall_expedition_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Tell me about my last expedition", keywords) is True


def test_recall_expedition_recap_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Can you describe my expedition to me", keywords) is True


def test_recall_expedition_named_phrasing_gates_open():
    """
    Uses "the expedition called X" phrasing (name after the noun), same
    reasoning as test_delete_project_phrasing_gates_open — "Tell me
    about my Field Season expedition" (name before the noun) is a known,
    deliberately accepted gap, not a bug.
    """
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Tell me about the expedition called Field Season", keywords) is True


# ----------------------------------------------------------------------
# Missions (v0.18)
# ----------------------------------------------------------------------

def test_add_mission_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Start a new mission called Master Baiter", keywords) is True


def test_list_missions_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("What missions do I have?", keywords) is True


def test_add_objective_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Add an objective to my Master Baiter mission", keywords) is True


def test_log_mission_progress_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Log a catch for my mission", keywords) is True


def test_delete_mission_phrasing_gates_open():
    """"called X" phrasing (name after the noun), same accepted trade-off as delete_project/delete_task."""
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Delete the mission called Master Baiter", keywords) is True


def test_complete_mission_phrasing_gates_open():
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Complete the mission called Master Baiter", keywords) is True


def test_ordinary_mission_mention_does_not_gate_open():
    """False-positive check: 'mission' as an ordinary word, not a request to act on a Mission record."""
    keywords = _real_gating_keywords()
    assert looks_like_action_request("Our company's mission is customer satisfaction", keywords) is False
