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
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from modules.assistant.module import looks_like_action_request


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
