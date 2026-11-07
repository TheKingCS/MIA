"""
core.assistant_household_actions
==================================

The Household by voice, for what its screen added (DEC-0125: full use both
ways). "Pause the vacuum routine", "start the trash routine again": the same
`routine.pause` / `routine.resume` action kinds the Household screen's
buttons use (core/routine_actions.py), so "undo that" brings it back.
Adding, listing and logging routines were already voice tools
(core/assistant_life_actions.py).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _pause(context, arguments: dict) -> str:
    """Tool pause_household_routine: pauses (or, with resume yes, restarts) the routine they named."""
    from core.actions import ACTION_TYPES, ActionError

    book = getattr(context, "recurring_missions", None)
    if book is None:
        return "Household routines aren't available right now."
    resume = str(arguments.get("resume") or "no").lower() in ("yes", "true", "1")
    from core.assistant_cooking_actions import find_recipe  # finds anything with a name by the words said

    said = str(arguments.get("name") or "").replace("routine", "").replace("chore", "").strip()
    routines = [t for t in book.all_templates() if t.category == "Household" and t.active != resume]
    found = find_recipe(routines, said)
    if found is None:
        return f"I don't have a {'paused ' if resume else ''}routine called '{arguments.get('name', '')}'."
    kind = "routine.resume" if resume else "routine.pause"
    try:
        ACTION_TYPES[kind].describe(context, {"template_id": found.template_id})
        return ACTION_TYPES[kind].execute(context, {"template_id": found.template_id})
    except ActionError as problem:
        return str(problem)


def register_household_actions(registry) -> None:
    """Registers the Household's added voice tool: pause_household_routine (and resume)."""
    registry.register(AssistantAction(
        name="pause_household_routine", domain="household",
        description="Pause a household routine (it stops counting, its streak and history are kept), or start a paused "
                    "one again.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "The routine's name as they said it."},
            "resume": {"type": "string", "description": "'yes' to start a paused routine again; 'no' to pause."}},
            "required": ["name"]},
        handler=_pause,
        trigger_phrases=("pause the routine", "pause my routine", "pause the chore", "stop tracking the",
                         "resume the routine", "start the routine again", "turn the routine back on"),
        subjects=("routine", "chore"),
    ))
