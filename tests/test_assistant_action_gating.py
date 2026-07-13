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
