"""
core.voice_catalog
=====================

The curated set of selectable Piper TTS voices — 2026-07-15, at the
user's explicit request: "I want to be able to pick through different
voices for M.I.A." Piper's full voice library (`rhasspy/piper-voices`
on Hugging Face) has dozens of entries; this is a small, hand-picked
subset spanning a real spread of accent/character rather than every
option — same "curated, not exhaustive" discipline as
`gui/theme_manager.py`'s 4 themes. Add more entries here (not a new
mechanism) if a specific voice is wanted later.

Pure data, no Qt/network calls here. `deploy/download_voice_models.sh`
fetches every entry's `.onnx`/`.onnx.json` pair into `voice_models/` at
deploy time; `core/voice_manager.py`'s `VoiceManager.list_available_voices()`
reports which of these are actually present locally, since a fetch
isn't guaranteed to have run — this dev sandbox only ships the default
`en_US-lessac-low` pre-fetched (see `docs/KNOWN_ISSUES.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

_HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


@dataclass(frozen=True)
class VoiceOption:
    voice_id: str  # matches the .onnx / .onnx.json filename stem in voice_models/
    display_name: str
    hf_path: str  # path segment under _HF_BASE, no file extension

    @property
    def onnx_url(self) -> str:
        return f"{_HF_BASE}/{self.hf_path}.onnx"

    @property
    def onnx_json_url(self) -> str:
        return f"{_HF_BASE}/{self.hf_path}.onnx.json"


DEFAULT_VOICE_ID = "en_US-lessac-low"

VOICE_CATALOG: dict[str, VoiceOption] = {
    "en_US-lessac-low": VoiceOption(
        voice_id="en_US-lessac-low",
        display_name="Lessac (US, default)",
        hf_path="en/en_US/lessac/low/en_US-lessac-low",
    ),
    "en_US-amy-low": VoiceOption(
        voice_id="en_US-amy-low",
        display_name="Amy (US)",
        hf_path="en/en_US/amy/low/en_US-amy-low",
    ),
    "en_US-ryan-medium": VoiceOption(
        voice_id="en_US-ryan-medium",
        display_name="Ryan (US)",
        hf_path="en/en_US/ryan/medium/en_US-ryan-medium",
    ),
    "en_GB-alan-low": VoiceOption(
        voice_id="en_GB-alan-low",
        display_name="Alan (British)",
        hf_path="en/en_GB/alan/low/en_GB-alan-low",
    ),
    "en_GB-southern_english_female-low": VoiceOption(
        voice_id="en_GB-southern_english_female-low",
        display_name="Southern English Female (British)",
        hf_path="en/en_GB/southern_english_female/low/en_GB-southern_english_female-low",
    ),
}
