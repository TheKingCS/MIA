"""MIA's voice from Settings and by voice (core/web_voice.py, core/assistant_voice_choice_actions.py): the voices
installed, switching one, the AI voice effect and the volume; only the PC's owner changes them."""

from __future__ import annotations

from types import SimpleNamespace

import core.person_settings as person_settings
from core.web_voice import choose, voice_page


class FakeVoice:
    """A voice manager with two voices installed and one whose model file has gone."""

    def __init__(self):
        self.current_voice_id = "kokoro:af_heart"

    def list_available_voices(self):
        return [SimpleNamespace(voice_id="kokoro:af_heart", display_name="Heart (American)", engine="kokoro"),
                SimpleNamespace(voice_id="kokoro:bf_emma", display_name="Emma (British)", engine="kokoro"),
                SimpleNamespace(voice_id="gone", display_name="Gone", engine="piper")]

    def set_voice(self, voice_id):
        if voice_id == "gone":
            return False
        self.current_voice_id = voice_id
        return True


class Config(dict):
    """A config that remembers what was set and whether it was saved."""

    saved = False

    def set(self, key, value):
        self[key] = value

    def save(self):
        self.saved = True


def home():
    return SimpleNamespace(voice=FakeVoice(), config=Config())


def test_the_voices_and_switching_one_with_its_effect_and_volume():
    assert voice_page(SimpleNamespace(voice=None)) == {"available": False}
    ctx = home()
    page = voice_page(ctx)
    assert page["current"] == "kokoro:af_heart" and page["effect"] and page["volume"] == 100 and len(page["voices"]) == 3
    assert choose(ctx, "kokoro:bf_emma") == {"said": "MIA speaks as Emma (British) now."}
    assert choose(ctx, "nope") == {"error": "That voice isn't installed on this computer."}
    assert choose(ctx, "gone") == {"error": "Gone's model file is missing."}
    assert choose(ctx, effect=False, volume=200) == {"said": "The AI voice effect is off; the volume is 150%."}
    assert ctx.config.saved and ctx.config["voice.playback_volume"] == 1.5
    assert choose(ctx, "kokoro:bf_emma") == {"said": "Nothing changed."}


def test_by_voice_only_the_owner_changes_it(monkeypatch):
    from core.assistant_voice_choice_actions import _list, _set

    ctx = home()
    monkeypatch.setattr(person_settings, "person_id", lambda c: "me")
    monkeypatch.setattr(person_settings, "_is_first_account", lambda c, pid: False)
    assert _set(ctx, {"voice": "emma"}) == "My voice is the PC owner's to change."
    assert _list(ctx, {}).startswith("I can speak as Heart (American), Emma (British), Gone. I'm Heart (American) now.")
    monkeypatch.setattr(person_settings, "_is_first_account", lambda c, pid: True)
    assert _set(ctx, {"voice": "the british one emma"}) == "MIA speaks as Emma (British) now."
