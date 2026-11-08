"""
core.assistant_accessibility_actions
=======================================

"Make the text bigger", "turn on high contrast", "read this screen to me"
(core/accessibility.py, 2026-10-01), and "switch to the cards look"
(core/display_style.py, DEC-0135), "make it cyberpunk" (core/themes.py,
DEC-0136). Each changes only the speaker's own look.
"""

from __future__ import annotations

import re

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
    """Tool set_theme: this person's theme (DEC-0136, core/themes.py: Stark, Y2K Cyber, Cyberpunk, Glass, or one of
    their own from the Theme Studio, matched by name first), in both looks; the screens are told."""
    from core.themes import KEY, THEMES, theme_of, wants_theme

    from core.themes import all_themes

    themes = all_themes(context)
    wanted = str(arguments.get("theme") or "").lower().strip()
    own = next((i for i, t in themes.items() if i not in THEMES and t["name"].lower() in wanted), None)  # theirs first
    theme_id = wanted if wanted in themes else own or wants_theme(wanted)
    if theme_id is None:
        return "Which theme? " + ", ".join(t["name"] for t in themes.values()) + "."
    name = themes[theme_id]["name"]
    if theme_id == theme_of(context):
        return f"You're already on the {name} theme."
    person_settings.put(context, KEY, theme_id)
    context.events.publish("display.changed")
    return f"Switched to the {name} theme."


# Accents by name for "make the accent purple" (core/themes.accent_problem refuses ones that read as warnings).
ACCENT_NAMES = {"cyan": "#35d4ff", "blue": "#3f7bff", "ice": "#96d6ff", "sky": "#6fc6ff", "violet": "#8a5cff",
                "purple": "#9b6bff", "lavender": "#b9a8ff", "pink": "#ff5ce6", "magenta": "#ff2ea6", "rose": "#ff8ad8",
                "white": "#e8f0ff", "silver": "#c0c8d4", "teal": "#2ad1c9",
                "orange": "#ff8a00", "red": "#ef5350", "green": "#4fc48c", "yellow": "#f2d23d", "gold": "#f6c453"}


def _action_tweak_theme(context, arguments: dict) -> str:
    """Tool tweak_theme: a theme of the person's own, from the one in use (or a named base) with the changes they
    asked for (accent by name or #rrggbb, material, corners, fire, bloom, mist, scanlines), saved (core/theme_actions
    `theme.save`, so it's undoable) and used. Their own theme in use is updated rather than copied."""
    from core.actions import ActionError
    from core.theme_actions import _save
    from core.themes import MATERIALS, THEMES, all_themes, choices_of, theme_of, wants_theme

    themes = all_themes(context)
    current = theme_of(context)
    base_id = wants_theme(str(arguments.get("base") or "")) or current
    base = themes[base_id]
    picks = dict(choices_of(base))
    accent = str(arguments.get("accent") or "").lower().strip()
    if accent:
        picks["accent"] = accent if re.fullmatch(r"#[0-9a-f]{6}", accent) else ACCENT_NAMES.get(accent.split()[-1], "")
        if not picks["accent"]:
            return "Which colour? " + ", ".join(sorted(k for k in ACCENT_NAMES if k not in ("orange", "red", "green", "yellow", "gold"))) + "."
    if arguments.get("material") in MATERIALS:
        picks["material"] = arguments["material"]
    for key in ("radius", "fire", "bloom", "mist", "scan", "grain"):
        if arguments.get(key) is not None:
            picks[key] = arguments[key]
    own = base_id == current and current not in THEMES
    params = {"choices": picks, "base": base_id, "use": True,
              "name": str(arguments.get("name") or "").strip() or (base["name"] if own else "My " + base["name"])}
    if own:
        params["id"] = current
    else:
        taken = {t["name"].lower() for t in themes.values()}
        n = 2
        while params["name"].lower() in taken:
            params["name"] = f"My {base['name']} {n}"
            n += 1
    try:
        return _save(context, params)
    except ActionError as problem:
        return str(problem)


def _action_delete_theme(context, arguments: dict) -> str:
    """Tool delete_theme: one of the person's own themes, by name (built-in ones stay)."""
    from core.actions import ActionError
    from core.theme_actions import _delete
    from core.themes import custom_themes

    wanted = str(arguments.get("theme") or "").lower().strip()
    found = next((t for t in custom_themes(context) if t["name"].lower() == wanted or t["id"] == wanted), None)
    found = found or next((t for t in custom_themes(context) if t["name"].lower() in wanted), None)
    if found is None:
        mine = [t["name"] for t in custom_themes(context)]
        return ("Which of your themes? " + ", ".join(mine) + ".") if mine else "You haven't made any themes of your own."
    try:
        return _delete(context, {"id": found["id"]})
    except ActionError as problem:
        return str(problem)


def _action_read_screen(context, arguments: dict) -> str:
    """Tool read_screen: asks the open screen to be read aloud."""
    context.events.publish("accessibility.read_screen")
    return "Reading the screen."


def register_accessibility_actions(registry: AssistantActionRegistry) -> None:
    """Registers the accessibility tools: set_text_size, set_high_contrast, set_display_style, set_theme,
    tweak_theme, delete_theme and read_screen."""
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
        name="tweak_theme", domain="accessibility",
        description="Make the user's own version of a theme: change its accent colour (by name: cyan, blue, ice, sky, "
                    "violet, purple, lavender, pink, magenta, rose, white, silver, teal; or #rrggbb), material (solid, "
                    "glass, chrome, wire), corners, or the 3D room's fire, bloom, mist or scanlines; saved and used.",
        parameters={"type": "object", "properties": {
            "accent": {"type": "string", "description": "a colour name or #rrggbb."},
            "material": {"type": "string", "description": "solid, glass, chrome or wire."},
            "base": {"type": "string", "description": "optional: the theme to start from (default: the one in use)."},
            "name": {"type": "string", "description": "optional: what to call it."},
            "radius": {"type": "number", "description": "optional: corner roundness, 0 to 28."},
            "fire": {"type": "number", "description": "optional: the room's fire, 0 to 2."},
            "bloom": {"type": "number", "description": "optional: the room's glow, 0 to 2."},
            "mist": {"type": "number", "description": "optional: the room's mist, 0 to 2.5."},
            "scan": {"type": "number", "description": "optional: scanlines, 0 to 1."},
        }, "required": []},
        handler=_action_tweak_theme,
        trigger_phrases=("accent color", "accent colour", "make it more", "theme but", "my own theme", "tweak the theme",
                         "change the accent"),
    ))
    registry.register(AssistantAction(
        name="delete_theme", domain="accessibility",
        description="Delete one of the user's own themes by name (the built-in ones stay).",
        parameters={"type": "object", "properties": {"theme": {"type": "string", "description": "the theme's name."}},
                    "required": ["theme"]},
        handler=_action_delete_theme,
        trigger_phrases=("delete my theme", "delete the theme", "remove my theme"),
    ))
    registry.register(AssistantAction(
        name="read_screen", domain="accessibility",
        description="Read the screen that's open aloud to the user.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_action_read_screen,
        trigger_phrases=("read this screen", "read the screen", "read me this", "read it to me", "read this to me",
                         "read this page"),
    ))
