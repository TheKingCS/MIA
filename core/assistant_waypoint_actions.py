"""
core.assistant_waypoint_actions
=================================

Waypoints by voice, for what Navigation's page added (DEC-0125: full use
both ways). "Rename the spring waypoint to Upper Spring", "mark the old
gate as a hazard", "note on the spring: dry in August": the same
`waypoint.edit` action kind as the page's Edit (core/waypoint_actions.py),
so "undo that" puts it back. Adding, listing, distances and deleting were
already voice tools.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _change(context, arguments: dict) -> str:
    """Tool change_waypoint: a new name, kind or notes for the waypoint they named; the rest stays."""
    from core.actions import ACTION_TYPES, ActionError
    from core.assistant_cooking_actions import find_recipe  # finds anything with a name by the words said

    book = getattr(context, "waypoints", None)
    if book is None:
        return "Waypoints aren't on this MIA."
    found = find_recipe(book.all_waypoints(), str(arguments.get("name") or "").replace("waypoint", ""))
    if found is None:
        return f"I don't have a waypoint called '{arguments.get('name', '')}'."
    params = {"waypoint_id": found.waypoint_id, "name": arguments.get("new_name") or found.name,
              "category": arguments.get("category") or found.category,
              "notes": found.notes if arguments.get("notes") in (None, "") else arguments["notes"]}
    try:
        ACTION_TYPES["waypoint.edit"].describe(context, params)
        return ACTION_TYPES["waypoint.edit"].execute(context, params)
    except ActionError as problem:
        return str(problem)


def register_waypoint_actions(registry) -> None:
    """Registers change_waypoint."""
    from core.waypoint_manager import WAYPOINT_CATEGORIES

    s = {"type": "string"}
    registry.register(AssistantAction(
        name="change_waypoint", domain="navigation",
        description="Rename a waypoint, change its kind, or set its notes. Where it is stays the same.",
        parameters={"type": "object", "properties": {
            "name": {**s, "description": "The waypoint's name as they said it."},
            "new_name": {**s, "description": "Its new name, only if they gave one."},
            "category": {**s, "enum": list(WAYPOINT_CATEGORIES), "description": "Its kind, only if they said."},
            "notes": {**s, "description": "Its notes, only if they gave some."}}, "required": ["name"]},
        handler=_change,
        trigger_phrases=("rename the waypoint", "rename waypoint", "change the waypoint", "mark the waypoint",
                         "note on the waypoint"),
        subjects=("waypoint",),
    ))
