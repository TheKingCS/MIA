"""
core.boot_sound
==================

Synthesizes the boot sequence's "growing pulsing energy" sound effect
— a rising-pitch power-up tone with a pulsing amplitude envelope,
timed to feel like it belongs alongside gui/presence_widget.py's
breathing glow-orb animation playing at the same time during boot (not
phase-locked to it — the orb runs on its own QTimer and this is
pre-rendered audio, two independent systems — but both use a similar
few-second pulse period so they read as one coherent "waking up"
moment rather than two unrelated effects bolted together).

Generated programmatically with numpy rather than bundling or fetching
an audio file: this project's offline-first stance already avoids
network-fetched assets, and synthesizing the effect sidesteps any
licensing question a found sound effect would raise (same reasoning
`assets/fonts/NOTICE.md` exists for the *opposite* case — fonts where a
real license situation genuinely exists and needed documenting). numpy
is already a dependency (`core/voice_manager.py`'s `play()` already
uses it) — nothing new added.

**Genuinely unverifiable end-to-end in this dev sandbox** — confirmed,
not assumed: `core/voice_manager.py`'s own docstring already
establishes this sandbox has no system PortAudio and no audio hardware
at all. The generated waveform itself (duration, sample rate, real
non-silent audio data, no clipping) is tested directly in
`tests/test_boot_sound.py`; actually *hearing* it play during boot
needs real audio hardware.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 22050
_DURATION_SECONDS = 3.5
_START_FREQ_HZ = 110.0
_END_FREQ_HZ = 440.0
_PULSE_RATE_HZ = 0.8


def generate_boot_sound_samples(
    duration_seconds: float = _DURATION_SECONDS, sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """
    Pure synthesis logic — testable without any audio hardware/I/O.
    Returns int16 mono samples: a rising-pitch tone (a "power up"
    sweep, `_START_FREQ_HZ` -> `_END_FREQ_HZ`) with a pulsing amplitude
    envelope on top, an overall fade-in ("growing" from silence) and a
    short fade-out at the very end (avoids an audible click from
    stopping mid-waveform).
    """
    sample_count = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, sample_count, endpoint=False)

    # Cumulative phase for a proper frequency sweep — naively computing
    # sin(2*pi*freq(t)*t) produces a discontinuous, wrong-sounding
    # sweep once freq varies with t; integrating instantaneous
    # frequency into phase first is the correct way to synthesize a
    # chirp/sweep tone.
    instantaneous_freq = _START_FREQ_HZ + (_END_FREQ_HZ - _START_FREQ_HZ) * (t / duration_seconds)
    phase = 2 * np.pi * np.cumsum(instantaneous_freq) / sample_rate
    # A second harmonic (double frequency, quieter) gives the tone more
    # body than a bare sine, without needing real synthesizer/filter code.
    tone = np.sin(phase) + 0.4 * np.sin(2 * phase)

    pulse = 0.6 + 0.4 * np.sin(2 * np.pi * _PULSE_RATE_HZ * t)
    growth = np.clip(t / (duration_seconds * 0.6), 0.0, 1.0)
    fade_out = np.clip((duration_seconds - t) / 0.3, 0.0, 1.0)
    envelope = growth * pulse * fade_out

    audio = tone * envelope
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.8  # normalize, leaving headroom rather than hitting full scale
    return (audio * 32767).astype(np.int16)


def write_boot_sound_wav(
    output_path: Path, duration_seconds: float = _DURATION_SECONDS, sample_rate: int = SAMPLE_RATE
) -> Path:
    """Writes the synthesized boot sound to a real .wav file — same
    `wave` module pattern `core/voice_manager.py` already uses for
    recorded audio."""
    samples = generate_boot_sound_samples(duration_seconds, sample_rate)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    return output_path
