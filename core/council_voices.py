"""
core.council_voices
=====================

A voice for every council member (DEC-0082; `docs/COUNCIL_AND_CHRONICLES_REVIEW.md`
section 5). Each member in `work/agents.json` has a Kokoro voice (DEC-0051,
offline, Apache-2.0); the ones there are placeholders until Zac picks each by
ear in the dev window, which plays a sample and saves his choice.

- `sample(member, voice)`: a short sample in that voice, the member saying who
  it is, made on this PC and kept (`data/dev/voices/`) so a second listen
  costs nothing.
- `choose(member, voice)`: Zac's pick, saved to the member.
- No voice imitates a provider's own: Kokoro has voices named like OpenAI's
  product voices (alloy, echo, fable, nova, onyx, sky), and those are refused
  for members that run on Zac's ChatGPT account, so nobody hears ChatGPT's own
  voice and takes it for the real thing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.dev_store import DEV_DATA

SAMPLES = DEV_DATA / "voices"
PROVIDER_NAMED = {"codex": ("alloy", "echo", "fable", "nova", "onyx", "sky")}  # provider -> voice words it owns


class VoiceError(ValueError):
    """A voice that can't be used as asked."""


def voices(pack: Optional[Path] = None) -> list[str]:
    """The English Kokoro voices installed here ("af_heart", "bm_george"...), or [] without Kokoro."""
    try:
        import numpy as np

        from core.voice_manager import _kokoro_dir

        path = pack or next(Path(_kokoro_dir()).glob("voices*.bin"))
        return sorted(k for k in np.load(path).files if k[:2] in ("af", "am", "bf", "bm"))
    except (StopIteration, OSError, ValueError, ImportError):
        return []


def allowed(member: dict, voice: str) -> str:
    """Pure logic. Why a member may not have this voice, or ""."""
    name = voice.removeprefix("kokoro:")
    owned = PROVIDER_NAMED.get(member.get("provider", ""), ())
    if any(name.endswith("_" + word) for word in owned):
        return f"{name} shares its name with one of that provider's own voices; pick another."
    return ""


def _members() -> dict:
    """The council's members (core.council), imported late so this module loads without it."""
    from core.council import members

    return members()


def sample(member_name: str, voice: str = "", folder: Path = SAMPLES, synth=None) -> bytes:
    """A few seconds of the member saying who they are, in `voice` (their own if none), as WAV."""
    found = _members().get(member_name)
    if found is None:
        raise VoiceError(f"No council member called {member_name}.")
    voice = voice or found.get("voice") or "kokoro:af_heart"
    if not voice.startswith("kokoro:"):
        voice = "kokoro:" + voice
    if voice.removeprefix("kokoro:") not in voices() and synth is None:
        raise VoiceError(f"{voice} isn't installed here.")
    why = allowed(found, voice)
    if why:
        raise VoiceError(why)
    text = f"I'm {found['name']}. {found.get('about') or 'A member of the council'}."
    key = hashlib.sha256(f"{voice}|{text}".encode("utf-8")).hexdigest()[:16]
    path = Path(folder) / f"{voice.removeprefix('kokoro:')}-{key}.wav"
    if not path.exists():
        Path(folder).mkdir(parents=True, exist_ok=True)
        if synth is None:
            from core.voice_catalog import VoiceOption
            from core.voice_manager import KokoroBackend

            synth = KokoroBackend(VoiceOption(voice, voice, engine="kokoro")).synthesize
        synth(text, path)
    return path.read_bytes()


def choose(member_name: str, voice: str, registry: Optional[Path] = None) -> dict:
    """Zac's pick for a member, saved in work/agents.json."""
    from core.work_agents import REGISTRY

    path = Path(registry or REGISTRY)
    data = json.loads(path.read_text(encoding="utf-8"))
    members = data.get("members") or {}
    if member_name not in members or member_name.startswith("_"):
        raise VoiceError(f"No council member called {member_name}.")
    voice = voice if voice.startswith("kokoro:") else "kokoro:" + voice
    why = allowed(members[member_name], voice)
    if why:
        raise VoiceError(why)
    members[member_name]["voice"] = voice
    members[member_name]["voice_chosen_by"] = "zac"
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return members[member_name]
