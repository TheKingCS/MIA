"""
core.assistant_accessibility_actions
=======================================

"Make the text bigger", "turn on high contrast", "read this screen to me"
(core/accessibility.py, 2026-10-01). Each changes only the speaker's own
look.
"""

from __future__ import annotations

from core import person_settings
from core.accessibility import TEXT_SIZES, look_for
from core.assistant_actions import AssistantAction, AssistantActionRegistry

_ORDER = list(TEXT_SIZES)


def _action_set_text_size(context, arguments: dict) -> str:
    current, _contrast = look_for(context)
    wanted = str(arguments.get("size") or "").lower().strip()
    if wanted in ("bigger", "larger", "up", "more"):
        size = _ORDER[min(len(_ORDER) - 1, _ORDER.index(current) + 1)]
    elif wanted in ("smaller", "down", "less"):
        size = _ORDER[max(0, _ORDER.index(current) - 1)]
    elif wanted in TEXT_SIZES:
        size = wanted
    elif wanted in ("default", "regular", "small"):
        size = "normal"
    else:
        return "Bigger or smaller? Sizes: " + ", ".join(label for label, _ in TEXT_SIZES.values()) + "."
    if size == current:
        return f"The text is already {TEXT_SIZES[size][0].lower()}" + (" (the biggest)." if size == _ORDER[-1] else ".")
    person_settings.put(context, "display.text_size", size)
    context.events.publish("display.changed")
    return f"Text size is now {TEXT_SIZES[size][0].lower()}."


def _action_set_high_contrast(context, arguments: dict) -> str:
    on = str(arguments.get("on", "true")).lower() not in ("false", "off", "no", "0")
    person_settings.put(context, "display.high_contrast", on)
    context.events.publish("display.changed")
    return "High contrast is on." if on else "High contrast is off."


def _action_read_screen(context, arguments: dict) -> str:
    context.events.publish("accessibility.read_screen")
    return "Reading the screen."


def register_accessibility_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="set_text_size", domain="accessibility",
        description="Make the text on screen bigger or smaller for the user (normal, larger, largest, huge).",
        parameters={"type": "object", "properties": {
            "size": {"type": "string", "description": "'bigger', 'smaller', or normal / larger / largest / huge."},
        }, "required": ["size"]},
        handler=_action_set_text_size,
        trigger_phrases=("text bigger", "text smaller", "font bigger", "font smaller", "bigger text", "larger text",
                         "smaller text", "text size", "font size", "can't read the text", "cant read the text",
                         "hard to read"),
    ))
    registry.register(AssistantAction(
        name="set_high_contrast", domain="accessibility",
        description="Turn high contrast (black and white with yellow highlights) on or off for the user.",
        parameters={"type": "object", "properties": {
            "on": {"type": "boolean", "description": "true to turn it on, false to turn it off."},
        }, "required": ["on"]},
        handler=_action_set_high_contrast,
        trigger_phrases=("high contrast", "more contrast", "easier to see"),
    ))
    registry.register(AssistantAction(
        name="read_screen", domain="accessibility",
        description="Read the screen that's open aloud to the user.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_read_screen,
        trigger_phrases=("read this screen", "read the screen", "read me this", "read it to me", "read this to me",
                         "read this page"),
    ))
