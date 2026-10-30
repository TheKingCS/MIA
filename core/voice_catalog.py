"""
core.voice_catalog
=====================

The curated set of selectable Piper TTS voices — 2026-07-15, at the
user's explicit request: "I want to be able to pick through different
voices for MIA" Piper's full voice library (`rhasspy/piper-voices`
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

**2026-10-29 (DEC-0051): Kokoro.** `KOKORO_CATALOG` is the computer's
voice: Kokoro-82M (Apache-2.0, offline, 24 kHz), one model file and one
voice pack shared by every Kokoro voice, in `voice_models/kokoro/`.
`VOICE_CATALOG` stays Piper's: the fallback, and the phone's and Pi's.
"""

from __future__ import annotations

from dataclasses import dataclass

_HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


@dataclass(frozen=True)
class VoiceOption:
    voice_id: str  # matches the .onnx / .onnx.json filename stem in voice_models/ ("kokoro:<name>" for Kokoro)
    display_name: str
    hf_path: str = ""  # path segment under _HF_BASE, no file extension (Piper only)
    engine: str = "piper"  # "piper" | "kokoro"

    @property
    def kokoro_name(self) -> str:
        """The voice's name inside Kokoro's voice pack ("af_heart")."""
        return self.voice_id.split(":", 1)[1] if self.engine == "kokoro" else ""

    @property
    def kokoro_lang(self) -> str:
        """Kokoro's first letter is the accent: a = American, b = British."""
        return "en-gb" if self.kokoro_name.startswith("b") else "en-us"

    @property
    def onnx_url(self) -> str:
        return f"{_HF_BASE}/{self.hf_path}.onnx"

    @property
    def onnx_json_url(self) -> str:
        return f"{_HF_BASE}/{self.hf_path}.onnx.json"


#: Piper's default: the fallback when Kokoro isn't installed or fails.
PIPER_DEFAULT_VOICE_ID = "en_US-lessac-low"
#: MIA's voice (DEC-0051).
DEFAULT_VOICE_ID = "kokoro:af_heart"

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


_KOKORO_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
#: (url, filename under voice_models/kokoro/) for the two files every Kokoro voice shares.
KOKORO_FILES = (
    (f"{_KOKORO_RELEASE}/kokoro-v1.0.onnx", "kokoro-v1.0.onnx"),
    (f"{_KOKORO_RELEASE}/voices-v1.0.bin", "voices-v1.0.bin"),
)

# Kokoro's best-graded English voices, the recommended one first.
KOKORO_CATALOG: dict[str, VoiceOption] = {
    option.voice_id: option for option in (
        VoiceOption("kokoro:af_heart", "Heart (US, recommended)", engine="kokoro"),
        VoiceOption("kokoro:af_bella", "Bella (US, bright)", engine="kokoro"),
        VoiceOption("kokoro:af_nicole", "Nicole (US, soft)", engine="kokoro"),
        VoiceOption("kokoro:af_sarah", "Sarah (US)", engine="kokoro"),
        VoiceOption("kokoro:bf_emma", "Emma (British)", engine="kokoro"),
        VoiceOption("kokoro:bf_isabella", "Isabella (British)", engine="kokoro"),
        VoiceOption("kokoro:am_michael", "Michael (US)", engine="kokoro"),
        VoiceOption("kokoro:bm_george", "George (British)", engine="kokoro"),
    )
}


def find_voice(voice_id: str):
    """The catalog entry for `voice_id`, Kokoro's or Piper's, or None."""
    return KOKORO_CATALOG.get(voice_id) or VOICE_CATALOG.get(voice_id)
