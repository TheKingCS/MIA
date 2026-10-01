"""
core.assistant_starter_actions
=================================

"What starter sets are there?", "set me up with the homestead starter
set", "add the student starter but not the weekly plan"
(core/starter_templates.py, 2026-10-01). Adding one is undoable.
"""

from __future__ import annotations

from core import starter_templates
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.starter_templates import STARTERS


def _action_list_starter_sets(context, arguments: dict) -> str:
    wanted = starter_templates.find(str(arguments.get("name") or ""))
    if wanted is not None:
        return starter_templates.describe(wanted)
    return ("Starter sets: " + "; ".join(f"{s.name} ({s.description[0].lower()}{s.description[1:-1]})"
                                         for s in STARTERS.values())
            + ". Say which one to add, and anything to leave out.")


def _action_add_starter_set(context, arguments: dict) -> str:
    starter = starter_templates.find(str(arguments.get("name") or ""))
    if starter is None:
        return "Which starter set? " + ", ".join(s.name for s in STARTERS.values()) + "."
    skip = str(arguments.get("leave_out") or "").lower()
    parts = [p.part_id for p in starter.parts
             if not skip or not any(word in p.label.lower() or word == p.part_id
                                   for word in (w.strip(" ,.") for w in skip.replace(" and ", ",").split(",")) if word)]
    result = starter_templates.apply(context, starter.starter_id, parts)
    return f"{starter.name} starter set: {result.describe()} Say \"undo that\" to take it back."


def register_starter_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="list_starter_sets", domain="starters",
        description="List the starter sets (ready-made chores, routines, upkeep schedules and workouts for a kind "
                    "of life), or what's in one.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "Optional: one set's name, to say what's in it."},
        }, "required": []},
        handler=_action_list_starter_sets,
        trigger_phrases=("starter set", "starter sets", "starter template", "starter pack", "get me started",
                         "help me get started", "where do i start", "what should i track"),
    ))
    registry.register(AssistantAction(
        name="add_starter_set", domain="starters",
        description="Add a starter set: Home & Family, Homestead, Student, Personal, Business or Fitness. Adds "
                    "its usual chores, routines, upkeep schedules or workout; nothing twice.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "The set: home_family, homestead, student, personal, "
                                                      "business or fitness."},
            "leave_out": {"type": "string", "description": "Optional: parts to skip, e.g. 'well, generator'."},
        }, "required": ["name"]},
        handler=_action_add_starter_set,
        trigger_phrases=("starter set", "starter template", "starter pack", "set me up with", "set me up for",
                         "get me started", "set up the usual", "add the usual chores"),
    ))
