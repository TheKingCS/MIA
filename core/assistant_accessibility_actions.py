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
                "gold": "#d9b867", "champagne": "#e8c27a", "bronze": "#c99a52",  # soft golds (DEC-0186)
                "orange": "#ff8a00", "red": "#ef5350", "green": "#4fc48c", "yellow": "#f2d23d"}


def _action_tweak_theme(context, arguments: dict) -> str:
    """Tool tweak_theme: a theme of the person's own, from the one in use (or a named base) with the changes they
    asked for (accent by name, soft golds included since DEC-0186, or #rrggbb; material, corners, fire, bloom, mist,
    scanlines), saved (core/theme_actions
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
            return "Which colour? " + ", ".join(sorted(k for k in ACCENT_NAMES if k not in ("orange", "red", "green", "yellow"))) + "."
    if arguments.get("material") in MATERIALS:
        picks["material"] = arguments["material"]
    sound = str(arguments.get("sound") or "").lower().strip()
    if sound:
        from core.themes import SOUND_SETS

        named = next((k for k, label in SOUND_SETS.items() if k in sound or sound in label.lower()), "")
        if not named:
            return "Which chimes? " + ", ".join(label for label in SOUND_SETS.values()) + "."
        picks["sound"] = named
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


def _action_design_theme(context, arguments: dict) -> str:
    """Tool design_theme: MIA designs a theme from the person's description (core/theme_design.design: the words are
    read in code), saves it as one of theirs through theme.save (so it's checked and undoable) and puts it on."""
    from core.actions import ActionError
    from core.theme_actions import _save
    from core.theme_design import design, summary
    from core.themes import all_themes

    description = str(arguments.get("description") or "").strip()
    if not description:
        return "Describe it: a place, a mood or colours. \"A rainy Tokyo night\", \"calm ocean glass\"."
    result = design(description)
    taken = {t["name"].lower() for t in all_themes(context).values()}
    name, n = result["name"], 2
    while name.lower() in taken:
        name, n = f"{result['name']} {n}", n + 1
    try:
        _save(context, {"name": name, "choices": result["choices"], "base": result["base"], "use": True})
    except ActionError as problem:
        return str(problem)
    return summary({**result, "name": name}) + " It's on now; say \"undo\" or open the Theme Studio to tweak it."


def _save_new(context, name: str, choices: dict, base: str) -> str:
    """Saves choices as a new theme of the person's own under a free name ("Ocean 2" when "Ocean" is taken) through
    theme.save, and puts it on; the name it got. ActionError when it can't be kept."""
    from core.theme_actions import _save
    from core.themes import all_themes

    taken = {t["name"].lower() for t in all_themes(context).values()}
    title, n = name, 2
    while title.lower() in taken:
        title, n = f"{name} {n}", n + 1
    _save(context, {"name": title, "choices": choices, "base": base, "use": True})
    return title


def _action_theme_from_picture(context, arguments: dict) -> str:
    """Tool theme_from_picture (A7): a theme from one of the person's paintings their words point at
    (core/theme_picture.from_painting: its colours read in code), saved as theirs through theme.save and put on; undo
    takes it back. A photo of their own goes through the Appearance page's From a Picture."""
    from core.actions import ActionError
    from core.theme_picture import from_painting, summary

    words = str(arguments.get("picture") or "").strip()
    try:
        result = from_painting(context, words) if words else None
    except ValueError as problem:
        return str(problem)
    if result is None:
        return ("Which of your paintings? Say what it shows. For a photo of your own, open Appearance and press "
                "From a Picture.")
    try:
        result["name"] = _save_new(context, result["name"], result["choices"], result["base"])
    except ActionError as problem:
        return "That theme can't be kept: " + str(problem)
    return summary(result) + " It's on now; say \"undo\" to go back."


def _action_adjust_theme(context, arguments: dict) -> str:
    """Tool adjust_theme (A7): the theme in use nudged by plain words (core/theme_design.adjust: darker, lighter,
    warmer, cooler, brighter, calmer, more contrast). Their own theme in use is updated; a built-in one is saved as
    their own copy. Through theme.save, so it's checked and undoable."""
    from core.actions import ActionError
    from core.theme_actions import _save
    from core.theme_design import ADJUSTMENTS, adjust
    from core.themes import THEMES, all_themes, choices_of, theme_of

    themes = all_themes(context)
    current = theme_of(context)
    picks, done = adjust(choices_of(themes[current]), str(arguments.get("how") or ""))
    if not done:
        return "How should it change? Darker, lighter, warmer, cooler, brighter, calmer or more contrast."
    try:
        if current in THEMES:
            name = _save_new(context, "My " + themes[current]["name"], picks, current)
        else:
            _save(context, {"id": current, "name": themes[current]["name"], "choices": picks, "base": current,
                            "use": True})
            name = themes[current]["name"]
    except ActionError as problem:
        return "That can't be kept: " + str(problem)
    return f"Done: {name} now has " + ", ".join(done) + ". Say \"undo\" to go back."


def _action_mix_themes(context, arguments: dict) -> str:
    """Tool mix_themes: one of the person's themes with chosen parts of another (core/themes.combine: colours, shape
    and type, the room's light, sounds, the backdrop), saved as theirs through theme.save and put on; undo takes it
    back. Says why when the mix can't be kept (an accent that reads as a warning, text that can't be read)."""
    from core.actions import ActionError
    from core.theme_actions import _save
    from core.themes import all_themes, combine, parts_from, wants_theme

    themes = all_themes(context)

    def which(words):
        said = str(words or "").lower().strip()
        own = next((t for t in themes.values() if said and (t["name"].lower() == said or t["name"].lower() in said)), None)
        return own["id"] if own else wants_theme(said)

    first, second = which(arguments.get("first")), which(arguments.get("second"))
    if not first or not second or first == second:
        return "Which two themes? " + ", ".join(t["name"] for t in themes.values()) + "."
    parts = parts_from(str(arguments.get("parts") or "")) or ["room"]
    try:
        made = combine(context, first, second, parts)
    except ValueError as problem:
        return str(problem)
    if made["problem"]:
        return "That mix can't be kept: " + made["problem"]
    taken = {t["name"].lower() for t in themes.values()}
    name, n = made["name"], 2
    while name.lower() in taken:
        name, n = f"{made['name']} {n}", n + 1
    try:
        _save(context, {"name": name, "choices": made["choices"], "base": made["base"], "use": True})
    except ActionError as problem:
        return str(problem)
    return f"{name} is on: {themes[first]['name']} with {themes[second]['name']}'s {' and '.join(parts)}. \"Undo\" takes it back."


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


def _action_set_scheme(context, arguments: dict) -> str:
    """Tool set_color_scheme: the person's colour scheme (core/appearance.py), keeping their theme and layout."""
    from core import appearance

    words = str(arguments.get("scheme") or "")
    scheme = words.strip().lower() if words.strip().lower() in appearance.SCHEMES or words.strip().lower() == "theme" \
        else appearance.wants_scheme(words)
    if not scheme:
        return "Which colours? " + ", ".join(n for n, *_r in appearance.SCHEMES.values()) + ", or your theme's own."
    try:
        return appearance.set_scheme(context, scheme)
    except ValueError as problem:
        return str(problem)


def _action_set_layout(context, arguments: dict) -> str:
    """Tool set_layout: the person's density and sidebar, and how much glass to draw (core/appearance.py)."""
    from core import appearance, person_settings

    effects = str(arguments.get("effects") or "").strip().lower()
    said = []
    try:
        if arguments.get("density") or arguments.get("sidebar"):
            said.append(appearance.set_layout(context, density=str(arguments.get("density") or "").strip().lower(),
                                              sidebar=str(arguments.get("sidebar") or "").strip().lower()))
        if effects:
            if effects not in appearance.EFFECTS:
                return "Glass effects are one of: " + ", ".join(appearance.EFFECTS) + "."
            person_settings.put(context, appearance.EFFECTS_KEY, effects)
            said.append(f"Glass effects: {effects}.")
    except ValueError as problem:
        return str(problem)
    return " ".join(said) or "Say compact or comfortable, a full sidebar or icons only, or how much glass."


def register_accessibility_actions(registry: AssistantActionRegistry) -> None:
    """Registers the accessibility tools: set_text_size, set_high_contrast, set_display_style, set_theme,
    set_color_scheme and set_layout (the look's other two choices, core/appearance.py), tweak_theme, mix_themes,
    design_theme, theme_from_picture and adjust_theme (A7), delete_theme and read_screen, and the painting tools
    (core/assistant_art_actions.py)."""
    from core.assistant_art_actions import register_art_actions

    register_art_actions(registry)  # MIA paints (DEC-0140): the look's pictures live with the look's tools
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
        name="set_color_scheme", domain="accessibility",
        description=("Change only MIA's colours (the colour scheme), keeping the theme and layout: cyan, turquoise, "
                     "violet, champagne, ice, rose, or the theme's own colours."),
        parameters={"type": "object", "properties": {
            "scheme": {"type": "string", "description": "cyan, turquoise, violet, champagne, ice, rose, or theme."},
        }, "required": ["scheme"]},
        handler=_action_set_scheme, prompt_arg="scheme",
        trigger_phrases=("colour scheme", "color scheme", "accent colours", "accent colors", "make the colours",
                         "make the colors", "change the colours to", "change the colors to", "theme's own colours"),
    ))
    registry.register(AssistantAction(
        name="set_layout", domain="accessibility",
        description=("Change MIA's layout without touching her colours: spacing (comfortable or compact) and the "
                     "sidebar (full, or icons only); and how much glass to draw (full, light, none, or auto)."),
        parameters={"type": "object", "properties": {
            "density": {"type": "string", "description": "comfortable or compact."},
            "sidebar": {"type": "string", "description": "full or icons."},
            "effects": {"type": "string", "description": "auto, full, light (no blur) or none (solid panels)."},
        }, "required": []},
        handler=_action_set_layout,
        trigger_phrases=("compact layout", "compact view", "more compact", "less spacing", "more spacing", "icons only", "smaller sidebar",
                         "full sidebar", "less transparent", "no blur", "solid panels", "turn off the glass"),
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
            "sound": {"type": "string", "description": "optional: the theme's chimes: classic, bubbly, synth, soft or quiet."},
        }, "required": []},
        handler=_action_tweak_theme,
        trigger_phrases=("accent color", "accent colour", "make it more", "theme but", "my own theme", "tweak the theme",
                         "change the accent", "theme chimes", "theme sounds", "bubbly sounds", "synth sounds"),
    ))
    registry.register(AssistantAction(
        name="mix_themes", domain="accessibility",
        description="Mix two of the user's themes: the first with chosen parts of the second (colours, shape and type, "
                    "the room's light, sounds, the backdrop picture), saved as theirs and used. 'Stark with Cyberpunk's "
                    "room', 'Glass but Y2K's colours'.",
        parameters={"type": "object", "properties": {
            "first": {"type": "string", "description": "the theme to start with."},
            "second": {"type": "string", "description": "the theme to take parts from."},
            "parts": {"type": "string", "description": "which parts: colours, shape, room, sounds, backdrop."},
        }, "required": ["first", "second"]},
        handler=_action_mix_themes,
        trigger_phrases=("mix the themes", "mix two themes", "mix stark", "mix y2k", "mix glass", "mix cyberpunk",
                         "with cyberpunk's", "with y2k's", "with glass's", "with stark's", "room from", "colours from",
                         "colors from"),
    ))
    registry.register(AssistantAction(
        name="design_theme", domain="accessibility",
        description="Design a new theme for the user from their description (a place, a mood, colours: 'a rainy "
                    "Tokyo night', 'calm ocean glass', 'loud 2000s rave'), save it as theirs and use it.",
        parameters={"type": "object", "properties": {
            "description": {"type": "string", "description": "the user's description of the look they want."},
        }, "required": ["description"]},
        handler=_action_design_theme,
        trigger_phrases=("design a theme", "design me a theme", "make me a theme", "make a theme", "theme like",
                         "create a theme", "new theme like"),
    ))
    registry.register(AssistantAction(
        name="theme_from_picture", domain="accessibility",
        description="Make a theme for the user from one of their paintings (its colours read from the picture), save "
                    "it as theirs and use it. 'A theme from my ocean painting'.",
        parameters={"type": "object", "properties": {
            "picture": {"type": "string", "description": "what the painting shows, in the user's words."},
        }, "required": ["picture"]},
        handler=_action_theme_from_picture, prompt_arg="picture",
        trigger_phrases=("theme from my", "theme from the", "theme from this", "theme from a picture",
                         "theme from a painting", "colours from my painting", "colors from my painting"),
    ))
    registry.register(AssistantAction(
        name="adjust_theme", domain="accessibility",
        description="Nudge the user's current theme: darker, lighter, warmer, cooler, brighter, calmer or more "
                    "contrast (several at once is fine); saved as theirs and used.",
        parameters={"type": "object", "properties": {
            "how": {"type": "string", "description": "the change in the user's words: 'darker and warmer'."},
        }, "required": ["how"]},
        handler=_action_adjust_theme, prompt_arg="how",
        trigger_phrases=("theme darker", "theme lighter", "theme warmer", "theme cooler", "theme brighter",
                         "theme calmer", "make it darker", "make it warmer", "make it cooler", "a bit darker",
                         "a bit warmer", "a bit cooler", "colours warmer", "colors warmer", "colours cooler",
                         "colors cooler", "more muted", "calmer colours", "calmer colors"),
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
