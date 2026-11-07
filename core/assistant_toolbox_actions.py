"""
core.assistant_toolbox_actions
================================

The Toolbox by voice, for what the web Toolbox added (DEC-0125: full use
both ways). "How many board feet in ten 2x6s, 8 feet long", "how much
concrete for a 10 by 12 pad, 4 inches thick", "turn off my wake up alarm".
Each tool uses the same core math (core/toolbox_calcs.py) or the same action
kind (core/toolbox_actions.py) as the screen, so the answers match.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _num(arguments: dict, name: str, default=None):
    """A number from the tool call, the default when it's missing; None when it isn't a number."""
    raw = arguments.get(name, default)
    try:
        return None if raw is None or raw == "" else float(raw)
    except (TypeError, ValueError):
        return None


def _board_feet(context, arguments: dict) -> str:
    """Tool calculate_board_feet: board feet for some boards of a size."""
    from core.toolbox_calcs import board_feet

    t, w, length = _num(arguments, "thickness_in"), _num(arguments, "width_in"), _num(arguments, "length_ft")
    if None in (t, w, length):
        return "I need the board's thickness and width in inches and its length in feet, like 2 by 6, 8 feet."
    try:
        return board_feet(t, w, length, _num(arguments, "count", 1) or 1)["text"].capitalize() + "."
    except ValueError as problem:
        return str(problem)


def _concrete(context, arguments: dict) -> str:
    """Tool calculate_concrete: concrete for a slab or pad, in yards and bags."""
    from core.toolbox_calcs import concrete_volume

    length, width, thick = _num(arguments, "length_ft"), _num(arguments, "width_ft"), _num(arguments, "thickness_in", 4)
    if None in (length, width, thick):
        return "I need the length and width in feet, and how thick in inches."
    try:
        r = concrete_volume(length, width, thick)
    except ValueError as problem:
        return str(problem)
    return f"{r['text'][0].upper()}{r['text'][1:]}. {r['note']}"


def _switch_alarm(context, arguments: dict) -> str:
    """Tool switch_alarm: turns the alarm with that label on or off (the same action as the Toolbox's switch)."""
    from core.actions import ACTION_TYPES, ActionError

    store = getattr(context, "alarms", None)
    if store is None:
        return "Alarms aren't on this MIA."
    label = str(arguments.get("label") or "").strip().lower()
    found = next((a for a in store.all_alarms() if a.label.lower() == label), None) or next(
        (a for a in store.all_alarms() if label and label in a.label.lower()), None)
    if found is None:
        return f"I don't have an alarm called '{arguments.get('label', '')}'."
    on = str(arguments.get("on") or "yes").lower() in ("yes", "true", "1", "on")
    params = {"alarm_id": found.alarm_id, "on": "yes" if on else "no"}
    try:
        ACTION_TYPES["alarm.switch"].describe(context, params)
        return ACTION_TYPES["alarm.switch"].execute(context, params)
    except ActionError as problem:
        return str(problem)


def register_toolbox_actions(registry) -> None:
    """Registers the Toolbox's voice tools: calculate_board_feet, calculate_concrete and switch_alarm."""
    n = {"type": "number"}
    registry.register(AssistantAction(
        name="calculate_board_feet", domain="toolbox",
        description="Board feet of lumber: nominal thickness and width in inches, length in feet, and how many.",
        parameters={"type": "object", "properties": {
            "thickness_in": {**n, "description": "Nominal thickness in inches (2 for a 2x6)."},
            "width_in": {**n, "description": "Nominal width in inches (6 for a 2x6)."},
            "length_ft": {**n, "description": "Length in feet."},
            "count": {**n, "description": "How many boards; 1 if not said."}},
            "required": ["thickness_in", "width_in", "length_ft"]},
        handler=_board_feet,
        trigger_phrases=("board feet", "board foot", "bd ft"),
        subjects=("lumber",),
    ))
    registry.register(AssistantAction(
        name="calculate_concrete", domain="toolbox",
        description="Concrete for a slab or pad: cubic yards with 10% extra, and bags of premix.",
        parameters={"type": "object", "properties": {
            "length_ft": {**n, "description": "Length in feet."}, "width_ft": {**n, "description": "Width in feet."},
            "thickness_in": {**n, "description": "Thickness in inches; 4 if not said."}},
            "required": ["length_ft", "width_ft"]},
        handler=_concrete,
        trigger_phrases=("yards of concrete", "cubic yards", "bags of concrete", "concrete volume"),
        subjects=("concrete",),
    ))
    registry.register(AssistantAction(
        name="switch_alarm", domain="alarms",
        description="Turn an alarm on or off without deleting it.",
        parameters={"type": "object", "properties": {
            "label": {"type": "string", "description": "The alarm's name as they said it."},
            "on": {"type": "string", "description": "'yes' to turn it on, 'no' to turn it off."}},
            "required": ["label", "on"]},
        handler=_switch_alarm,
        trigger_phrases=("turn off my alarm", "turn on my alarm", "turn off the alarm", "turn on the alarm",
                         "disable the alarm", "enable the alarm", "switch off the alarm"),
        subjects=("alarm",),
    ))
