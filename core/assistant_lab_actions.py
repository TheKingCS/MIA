"""
core.assistant_lab_actions
============================

The Lab by voice, for what the web Lab added (DEC-0125: full use both ways).
"Delete the last soil moisture reading" takes out the newest reading in that
series with the same action kind the Lab's Delete button uses
(core/lab_reading_actions.py), so "undo that" brings it back. Logging and
listing readings were already voice tools (log_lab_reading,
list_lab_readings in core/application.py).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _delete_last(context, arguments: dict) -> str:
    """Tool delete_lab_reading: deletes the newest reading in the series they named."""
    from core.actions import ACTION_TYPES, ActionError
    from core.web_lab import resolve_series

    logger = getattr(context, "data_logger", None)
    if logger is None:
        return "The Lab isn't on this MIA."
    wanted = str(arguments.get("series") or "").strip()
    series = resolve_series(logger.list_series(), wanted)
    readings = logger.readings_for(series) if wanted else []
    if not readings:
        return f"There are no readings in '{wanted}'." if wanted else "Which series?"
    params = {"reading_id": readings[-1].reading_id}
    try:
        ACTION_TYPES["lab_reading.delete"].describe(context, params)
        return ACTION_TYPES["lab_reading.delete"].execute(context, params)
    except ActionError as problem:
        return str(problem)


def register_lab_actions(registry) -> None:
    """Registers the Lab's added voice tool: delete_lab_reading."""
    registry.register(AssistantAction(
        name="delete_lab_reading", domain="lab",
        description="Delete the newest reading in a Lab (Data Logger) series, when they logged it by mistake.",
        parameters={"type": "object", "properties": {
            "series": {"type": "string", "description": "The series' name as they said it."}}, "required": ["series"]},
        handler=_delete_last,
        trigger_phrases=("delete the last reading", "remove the last reading", "delete that reading",
                         "undo the last reading"),
        subjects=("reading",),
    ))
