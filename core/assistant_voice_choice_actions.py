"""
core.assistant_voice_choice_actions
======================================

MIA's own voice, by voice (DEC-0125; the same change as Settings' Voice,
core/web_voice.py): "which voices do you have?", "switch to the British
voice", "turn your voice effect off", "speak louder". Device-wide, so only the
PC's owner changes it; anyone can ask which voices there are.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _owner(context) -> bool:
    """Whether the person talking is the PC's owner (the first account)."""
    from core.person_settings import _is_first_account, person_id

    return _is_first_account(context, person_id(context) or "")


def _list(context, arguments: dict) -> str:
    """Tool list_mia_voices: the voices installed, and which one is speaking."""
    from core.web_voice import voice_page

    page = voice_page(context)
    if not page["available"] or not page["voices"]:
        return "There are no voices installed on this computer."
    now = next((v["name"] for v in page["voices"] if v["id"] == page["current"]), "")
    return f"I can speak as {', '.join(v['name'] for v in page['voices'])}." + (f" I'm {now} now." if now else "")


def _set(context, arguments: dict) -> str:
    """Tool set_mia_voice: a voice named by its words, the AI voice effect on or off, the volume (percent)."""
    from core.assistant_cooking_actions import find_recipe
    from core.web_voice import choose, voice_page

    if not _owner(context):
        return "My voice is the PC owner's to change."
    page = voice_page(context)
    if not page["available"]:
        return "There's no voice on this computer."
    voice_id = None
    if str(arguments.get("voice") or "").strip():
        from types import SimpleNamespace

        found = find_recipe([SimpleNamespace(name=v["name"], id=v["id"]) for v in page["voices"]], str(arguments["voice"]))
        if found is None:
            return "I don't have that voice. " + _list(context, {})
        voice_id = found.id
    volume = arguments.get("volume")
    done = choose(context, voice_id, arguments.get("effect"), int(volume) if volume not in (None, "") else None)
    return done.get("said") or done.get("error", "")


def register_voice_choice_actions(registry) -> None:
    """Registers list_mia_voices and set_mia_voice."""
    s = {"type": "string"}
    registry.register(AssistantAction(
        name="list_mia_voices", domain="accessibility",
        description="The voices MIA can speak with on this computer, and which one she's using.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_list,
        trigger_phrases=("which voices", "what voices", "your voices", "voices do you have"),
    ))
    registry.register(AssistantAction(
        name="set_mia_voice", domain="accessibility",
        description="Change MIA's own speaking voice, turn her AI voice effect on or off, or set her volume.",
        parameters={"type": "object", "properties": {
            "voice": {**s, "description": "The voice by its name or a word of it, only if they named one."},
            "effect": {"type": "boolean", "description": "The AI voice effect on (true) or off (false), only if said."},
            "volume": {"type": "integer", "description": "Volume in percent, 0 to 150, only if said."}}, "required": []},
        handler=_set,
        trigger_phrases=("change your voice", "switch your voice", "use the voice", "voice effect", "speak louder",
                         "speak quieter", "your volume"),
    ))
