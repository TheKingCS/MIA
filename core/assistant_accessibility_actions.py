"""
core.assistant_accessibility_actions
=======================================

"Make the text bigger", "turn on high contrast", "read this screen to me"
(core/accessibility.py, 2026-10-01), and "switch to the cards look"
(core/display_style.py, DEC-0135), "make it cyberpunk" (core/themes.py,
DEC-0136). Each changes only the speaker's own look.
"""

from __future__ import annotations

from core import person_settings
from core.accessibility import TEXT_SIZES, look_for
from core.assistant_actions import AssistantAction, AssistantActionRegistry

_ORDER = list(TEXT_SIZES)


def _action_set_text_size(context, arguments: dict) -> str:
    """Tool set_text_size: this person's text size one step bigger or smaller, or a size by name (normal,
    larger, largest, huge); the screens are told.
    """
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
    """Tool set_high_contrast: high contrast on or off for this person; the screens are told."""
    on = str(arguments.get("on", "true")).lower() not in ("false", "off", "no", "0")
    person_settings.put(context, "display.high_contrast", on)
    context.events.publish("display.changed")
    return "High contrast is on." if on else "High contrast is off."


def _action_set_display_style(context, arguments: dict) -> str:
    """Tool set_display_style: this person's look (DEC-0135): spatial (the Nexus and rooms), cards (the Dashboard
    and cards), or auto (spatial on the computer, cards on the phone); the screens are told."""
    from core.display_style import KEY, STYLES, style_of, wants_style

    wanted = str(arguments.get("style") or "").lower().strip()
    style = wanted if wanted in STYLES else wants_style(wanted)
    if style is None:
        return ("Which look? Spatial (the Nexus and its rooms), cards (the Dashboard and cards), or spatial on the "
                "computer and cards on the phone.")
    label = STYLES[style][0]
    if style == style_of(context):
        return "You're already on " + ("spatial on the computer, cards on the phone." if style == "auto" else f"the {label.lower()} look.")
    person_settings.put(context, KEY, style)
    context.events.publish("display.changed")
    return {"spatial": "Switched to the spatial look: MIA opens on the Nexus.",
            "cards": "Switched to the cards look: MIA opens on the Dashboard.",
            "auto": "Done: spatial on the computer, cards on the phone."}[style]


def _action_set_theme(context, arguments: dict) -> str:
    """Tool set_theme: this person's theme (DEC-0136, core/themes.py: Stark, Y2K Cyber, Cyberpunk, Glass), in both
    looks; the screens are told."""
    from core.themes import KEY, THEMES, theme_of, wants_theme

    wanted = str(arguments.get("theme") or "").lower().strip()
    theme_id = wanted if wanted in THEMES else wants_theme(wanted)
    if theme_id is None:
        return "Which theme? " + ", ".join(t.name for t in THEMES.values()) + "."
    name = THEMES[theme_id].name
    if theme_id == theme_of(context):
        return f"You're already on the {name} theme."
    person_settings.put(context, KEY, theme_id)
    context.events.publish("display.changed")
    return f"Switched to the {name} theme."


def _action_read_screen(context, arguments: dict) -> str:
    """Tool read_screen: asks the open screen to be read aloud."""
    context.events.publish("accessibility.read_screen")
    return "Reading the screen."


def register_accessibility_actions(registry: AssistantActionRegistry) -> None:
    """Registers the accessibility tools: set_text_size, set_high_contrast, set_display_style, set_theme and
    read_screen."""
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
        name="set_display_style", domain="accessibility",
        description="Switch MIA's look for the user: 'spatial' (the Nexus, portals and rooms), 'cards' (the Dashboard "
                    "and organized cards), or 'auto' (spatial on the computer, cards on the phone).",
        parameters={"type": "object", "properties": {
            "style": {"type": "string", "description": "spatial, cards or auto."},
        }, "required": ["style"]},
        handler=_action_set_display_style,
        trigger_phrases=("cards look", "card look", "spatial look", "portal look", "the old look", "classic look",
                         "switch the look", "change the look", "display style", "switch to cards", "switch to spatial",
                         "nexus look", "the new look"),
    ))
    registry.register(AssistantAction(
        name="set_theme", domain="accessibility",
        description="Change MIA's visual theme for the user, in both looks: stark (cyan holographic), y2k (Y2K cyber: "
                    "chrome, neon magenta, liquid), cyberpunk (dark neon city) or glass (minimal frosted glass).",
        parameters={"type": "object", "properties": {
            "theme": {"type": "string", "description": "stark, y2k, cyberpunk or glass."},
        }, "required": ["theme"]},
        handler=_action_set_theme,
        trigger_phrases=("theme", "y2k", "myspace", "cyberpunk", "glass theme", "stark theme", "change the colors",
                         "change the colours", "new theme"),
    ))
    registry.register(AssistantAction(
        name="read_screen", domain="accessibility",
        description="Read the screen that's open aloud to the user.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_read_screen,
        trigger_phrases=("read this screen", "read the screen", "read me this", "read it to me", "read this to me",
                         "read this page"),
    ))
