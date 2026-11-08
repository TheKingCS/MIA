"""
core.web_voice
================

MIA's voice from the web's Settings and by voice (DEC-0125: the voice, the AI
voice effect and the volume were on the desktop's Settings only). Device-wide,
like the model: one voice for this computer, so only its owner changes it.

- `voice_page(context)`: the voices installed (Kokoro's first, then Piper's
  with a model file), the one speaking now, the effect and the volume.
- `choose(context, voice_id, effect, volume)`: changes any of the three and
  says what changed, or why not (a voice whose model isn't here).

Not an action with undo: the running voice engine is swapped in memory, so
putting back the config file alone wouldn't put back the voice. To go back,
pick the old voice again; the page shows which it was.
"""

from __future__ import annotations

from typing import Optional

DEFAULT_VOLUME = 1.0


def voice_page(context) -> dict:
    """The voices for the page: {"available", "voices": [{id, name, engine}], "current", "effect", "volume"} (volume as
    a percent); not available when there's no voice on this computer."""
    voice = getattr(context, "voice", None)
    if voice is None:
        return {"available": False}
    config = getattr(context, "config", None)
    try:
        voices = [{"id": v.voice_id, "name": v.display_name, "engine": v.engine} for v in voice.list_available_voices()]
    except Exception:
        voices = []
    volume = float(config.get("voice.playback_volume", DEFAULT_VOLUME)) if config is not None else DEFAULT_VOLUME
    return {"available": True, "voices": voices, "current": voice.current_voice_id,
            "effect": bool(config.get("voice.ai_voice_effect", True)) if config is not None else True,
            "volume": round(volume * 100)}


def choose(context, voice_id: Optional[str] = None, effect: Optional[bool] = None,
           volume: Optional[int] = None) -> dict:
    """Changes MIA's voice, the AI voice effect (Piper voices only) and the volume (0 to 150 percent), each only when
    given; {"said": what changed} or {"error": why not}."""
    voice = getattr(context, "voice", None)
    config = getattr(context, "config", None)
    if voice is None or config is None:
        return {"error": "There's no voice on this computer."}
    said = []
    if voice_id:
        names = {v.voice_id: v.display_name for v in voice.list_available_voices()}
        if voice_id not in names:
            return {"error": "That voice isn't installed on this computer."}
        if voice_id != voice.current_voice_id:
            if not voice.set_voice(voice_id):
                return {"error": f"{names[voice_id]}'s model file is missing."}
            said.append(f"MIA speaks as {names[voice_id]} now")
    if effect is not None and bool(effect) != bool(config.get("voice.ai_voice_effect", True)):
        config.set("voice.ai_voice_effect", bool(effect))
        said.append("the AI voice effect is " + ("on" if effect else "off"))
    if volume is not None:
        level = max(0, min(150, int(volume)))
        if abs(level / 100 - float(config.get("voice.playback_volume", DEFAULT_VOLUME))) > 0.004:
            config.set("voice.playback_volume", level / 100)
            said.append(f"the volume is {level}%")
    if effect is not None or volume is not None:
        config.save()
    if not said:
        return {"said": "Nothing changed."}
    text = "; ".join(said)
    return {"said": text[:1].upper() + text[1:] + "."}
