"""
core.assistant_art_actions
============================

MIA paints by voice (DEC-0140, core/art_studio.py): "paint me a fantasy
castle village for my background", "use the castle one as my background",
"take the background down", "delete the castle picture". Painting runs on the
PC's own graphics card and takes a minute or so; a background asked for this
way goes up by itself when it's done (and "undo" takes it down).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry

_PORTAL_WORDS = ("portal", "door", "gateway")


def _action_paint(context, arguments: dict) -> str:
    """Tool paint_picture: MIA paints from the description on this PC's graphics card; as the background (the default)
    it goes up by itself when it's done."""
    from core.art_studio import start

    description = str(arguments.get("description") or "").strip()
    use = "portal" if any(w in str(arguments.get("use") or "").lower() for w in _PORTAL_WORDS) else "backdrop"
    background = use == "backdrop" and str(arguments.get("as_background", "true")).lower() not in ("false", "no", "0")
    try:
        start(context, description, use, apply=background)
    except ValueError as problem:
        return str(problem)
    return ("Painting it now on your PC's graphics card; it takes about a minute. "
            + ("It'll go up as your background when it's done." if background else "It'll be in your art in the Theme Studio."))


def _action_use_backdrop(context, arguments: dict) -> str:
    """Tool use_backdrop: one of the person's paintings (by its words) as the background, or none."""
    from core.art_studio import find, use_as_backdrop

    words = str(arguments.get("picture") or "").strip().lower()
    if words in ("", "none", "nothing", "off", "no background", "remove", "take it down"):
        try:
            use_as_backdrop(context, "")
        except ValueError as problem:
            return str(problem)
        return "The background is down. \"Undo\" puts it back."
    item = find(context, words)
    if item is None:
        return "I don't have a painting like that yet. Want me to paint one?"
    strength = arguments.get("strength")
    try:
        use_as_backdrop(context, item["id"], float(strength) if strength is not None else None)
    except (ValueError, TypeError) as problem:
        return str(problem)
    return f"Your background is the painting of {item['description'][:60]} now."


def _action_delete_picture(context, arguments: dict) -> str:
    """Tool delete_picture: one of the person's paintings, by its words (kept aside, so undo brings it back)."""
    from core.actions import ActionError
    from core.art_studio import _delete, find

    item = find(context, str(arguments.get("picture") or ""))
    if item is None:
        return "Which painting? Say a word from what it shows."
    try:
        return _delete(context, {"id": item["id"]})
    except ActionError as problem:
        return str(problem)


def register_art_actions(registry: AssistantActionRegistry) -> None:
    """Registers the painting tools: paint_picture, use_backdrop and delete_picture."""
    registry.register(AssistantAction(
        name="paint_picture", domain="accessibility",
        description="Paint a picture for MIA's look on this PC's graphics card from the user's description (a place or "
                    "scene: 'a fantasy castle village at dusk'); by default it becomes the user's background behind "
                    "every page and in the 3D room when it's done. use='portal' paints a portal picture instead.",
        parameters={"type": "object", "properties": {
            "description": {"type": "string", "description": "what to paint, in the user's words."},
            "use": {"type": "string", "description": "optional: 'background' (default) or 'portal'."},
            "as_background": {"type": "boolean", "description": "optional: put it up as the background (default true)."},
        }, "required": ["description"]},
        handler=_action_paint,
        trigger_phrases=("paint me", "paint a", "draw me", "generate a background", "generate an image", "make a background",
                         "background to show", "background show", "for my background", "as my background", "wallpaper"),
    ))
    registry.register(AssistantAction(
        name="use_backdrop", domain="accessibility",
        description="Use one of the user's paintings as their background (by a word from what it shows), or 'none' to "
                    "take the background down.",
        parameters={"type": "object", "properties": {
            "picture": {"type": "string", "description": "words from the painting's description, or 'none'."},
            "strength": {"type": "number", "description": "optional: how strongly it shows, 0.1 to 1."},
        }, "required": ["picture"]},
        handler=_action_use_backdrop,
        trigger_phrases=("use the painting", "as the background", "take the background down", "remove the background",
                         "no background", "background off"),
    ))
    registry.register(AssistantAction(
        name="delete_picture", domain="accessibility",
        description="Delete one of the user's paintings (by a word from what it shows).",
        parameters={"type": "object", "properties": {"picture": {"type": "string", "description": "words from it."}},
                    "required": ["picture"]},
        handler=_action_delete_picture,
        trigger_phrases=("delete the painting", "delete the picture", "remove the painting"),
    ))
