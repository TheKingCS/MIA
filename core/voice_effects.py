"""
core.voice_effects
=====================

Post-processing DSP effects applied to Piper's raw synthesized audio —
2026-07-15, at the user's explicit request for M.I.A. to "sound like a
futuristic awesome AI companion device," not a plain human voice.
Deliberately pure `numpy` (already a dependency for `core/voice_manager.py`'s
recording/playback arrays) rather than reaching for a heavier audio
library — these are simple, well-established effects (ring modulation,
digital chorus), not anything needing real DSP filter design.

**Tuned deliberately subtle** — calibrated via `AskUserQuestion`
("JARVIS-like": mostly natural and clearly intelligible, a light
synthetic polish, not obviously robotic) over a stronger alternative
that was also offered. A too-strong ring-modulation mix genuinely hurts
intelligibility — this is a real, well-known trade-off in robotic-voice
effects, not just a taste call. **I can't judge audio quality myself,
only the person actually listening can** — treat the constants below
as a first pass to tune by ear, same "verify against the real thing"
discipline this project applies to everything else Voice-related.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

# Conservative by design — see module docstring. Raise these only after
# a human has actually listened and confirmed speech is still clearly
# intelligible at the new setting.
_RING_MOD_CARRIER_HZ = 40.0
_RING_MOD_MIX = 0.08
_CHORUS_DELAY_MS = 18.0
_CHORUS_MIX = 0.18


def apply_ring_modulation(samples: np.ndarray, sample_rate: int, carrier_hz: float, mix: float) -> np.ndarray:
    """Classic "robotic" texture — multiplies the signal by a carrier
    sine wave. `mix` is 0.0 (no effect) to 1.0 (fully ring-modulated,
    which reads as a broken radio, not "futuristic AI" — keep this
    low). Returns float64 samples, not yet clamped/converted back to
    int16 — apply_ai_voice_effect() does that once at the end of the
    whole chain."""
    t = np.arange(len(samples)) / sample_rate
    carrier = np.sin(2 * np.pi * carrier_hz * t)
    dry = samples.astype(np.float64)
    modulated = dry * carrier
    return (1 - mix) * dry + mix * modulated


def apply_chorus(samples: np.ndarray, sample_rate: int, delay_ms: float, mix: float) -> np.ndarray:
    """Subtle digital "doubling" — mixes in a short-delayed copy of the
    signal, same principle as a chorus/flange effect. Reads as a light
    synthetic shimmer at a low mix, not an audible echo. `samples` may
    already be float64 (chained after apply_ring_modulation)."""
    dry = samples.astype(np.float64)
    delay_samples = max(1, int(sample_rate * delay_ms / 1000))
    delayed = np.zeros_like(dry)
    if delay_samples < len(dry):
        delayed[delay_samples:] = dry[:-delay_samples]
    return (1 - mix) * dry + mix * delayed


def apply_ai_voice_effect(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """The "subtle, JARVIS-like" preset — light ring modulation + light
    chorus. Returns int16 PCM, peak-normalized against the original so
    mixing the effects in doesn't quietly change the volume or clip."""
    original_peak = np.max(np.abs(samples.astype(np.float64)))

    processed = apply_ring_modulation(samples, sample_rate, _RING_MOD_CARRIER_HZ, _RING_MOD_MIX)
    processed = apply_chorus(processed, sample_rate, _CHORUS_DELAY_MS, _CHORUS_MIX)

    processed_peak = np.max(np.abs(processed))
    if processed_peak > 0 and original_peak > 0:
        processed = processed * (original_peak / processed_peak)

    return np.clip(processed, -32768, 32767).astype(np.int16)


def apply_ai_voice_effect_to_wav_file(wav_path: Path) -> None:
    """Reads a mono 16-bit PCM WAV file (Piper's own output format),
    applies apply_ai_voice_effect(), and overwrites it in place — the
    actual integration point core/voice_manager.py calls after Piper
    synthesis. No-ops (logged via the caller, not here) on anything
    that isn't 16-bit mono, rather than guessing at a stereo/wide-sample
    mixdown Piper never actually produces."""
    with wave.open(str(wav_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())

    if channels != 1 or sample_width != 2:
        return

    samples = np.frombuffer(frames, dtype=np.int16)
    processed = apply_ai_voice_effect(samples, sample_rate)

    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(processed.tobytes())
