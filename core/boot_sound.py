"""
core.boot_sound
==================

Synthesizes the boot sequence's "growing pulsing energy" sound effect
— a rising-pitch power-up sweep with a pulsing amplitude envelope,
capped off with a bright high "ping" (the user's own description:
"like a woooooooom ping") — timed to feel like it belongs alongside
gui/presence_widget.py's breathing glow-orb animation playing at the
same time during boot (not phase-locked to it — the orb runs on its
own QTimer and this is pre-rendered audio, two independent systems —
but both use a similar few-second pulse period so they read as one
coherent "waking up" moment rather than two unrelated effects bolted
together).

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
non-silent audio data, no clipping, genuine sweep-then-ping shape) is
tested directly in `tests/test_boot_sound.py`; actually *hearing* it
play during boot needs real audio hardware.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 22050
_DURATION_SECONDS = 3.9
_START_FREQ_HZ = 110.0
_END_FREQ_HZ = 660.0
_PULSE_RATE_HZ = 0.8
# The tail end of the total duration is the "ping" — a short, bright
# chime — rather than the sweep just fading to silence.
_PING_FRACTION = 0.15
_PING_FREQ_HZ = 1568.0  # G6 — a clean, bright "success chime" pitch


def _generate_sweep(duration_seconds: float, sample_rate: int) -> np.ndarray:
    """The "woooooooom" — a rising-pitch power-up sweep with a pulsing
    amplitude envelope on top and a fade-in ("growing" from silence).
    No fade-out at its own end — it hands off directly to the ping."""
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
    growth = np.clip(t / (duration_seconds * 0.5), 0.0, 1.0)
    return tone * growth * pulse


def _generate_ping(duration_seconds: float, sample_rate: int) -> np.ndarray:
    """The "ping" — a short, bright bell-like chime: a fundamental plus
    two slightly-detuned/higher partials (the classic cheap-but-
    convincing way to synthesize a bell without real modal/physical
    synthesis), a fast exponential decay, and a very short linear
    attack (avoids an audible click from starting instantaneously at
    full amplitude)."""
    sample_count = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, sample_count, endpoint=False)

    tone = (
        np.sin(2 * np.pi * _PING_FREQ_HZ * t)
        + 0.5 * np.sin(2 * np.pi * _PING_FREQ_HZ * 2.01 * t)
        + 0.3 * np.sin(2 * np.pi * _PING_FREQ_HZ * 3.0 * t)
    )
    decay = np.exp(-t / (duration_seconds / 4))

    attack_sample_count = max(1, int(0.005 * sample_rate))
    attack = np.ones(sample_count)
    attack[:attack_sample_count] = np.linspace(0.0, 1.0, attack_sample_count)

    return tone * decay * attack


def generate_boot_sound_samples(
    duration_seconds: float = _DURATION_SECONDS, sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """
    Pure synthesis logic — testable without any audio hardware/I/O.
    Returns int16 mono samples: a rising-pitch "power up" sweep
    (`_generate_sweep()`) immediately followed by a bright high "ping"
    (`_generate_ping()`) — `_PING_FRACTION` of `duration_seconds` is the
    ping, the rest is the sweep, so callers passing a different total
    `duration_seconds` still get a proportionally-shaped result.
    """
    total_sample_count = int(duration_seconds * sample_rate)
    ping_sample_count = int(total_sample_count * _PING_FRACTION)
    sweep_sample_count = total_sample_count - ping_sample_count

    sweep = _generate_sweep(sweep_sample_count / sample_rate, sample_rate)
    ping = _generate_ping(ping_sample_count / sample_rate, sample_rate)
    audio = np.concatenate([sweep, ping])[:total_sample_count]

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.85  # normalize, leaving headroom rather than hitting full scale
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
