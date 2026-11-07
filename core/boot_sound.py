"""
core.boot_sound
==================

**Six to choose from** (2026-11-07, Zac: "an odd ping... sample some
sounds and I will pick"): `startup_samples()` makes each of
core/startup_sounds.py's choices (a warm chord, rising chimes, a reactor
power-up, a soft swell, a ready tone, and the original below); Settings
plays and picks one (`sound.startup`), or Off.

The original: the boot sequence's "growing pulsing energy" sound effect
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


# ------------------------------------------------------------------ the startup sounds to choose from (2026-11-07)
#
# Zac: "the start up noise... its an odd ping. Sample some sounds and I will pick a good start up sound, and make it a
# togglable setting." Each is synthesized here like the original (no files to fetch or license), at CD-ish quality,
# and chosen in Settings (`sound.startup`, the device's: it plays before anyone signs in; "off" for none).

RATE = 44100

from core.startup_sounds import DEFAULT_STARTUP, STARTUP_SOUNDS, startup_choice  # noqa: E402,F401  (the names)


def _t(seconds: float, rate: int = RATE) -> np.ndarray:
    """Pure logic. The time of each sample over a span."""
    return np.arange(int(seconds * rate)) / rate


def _envelope(n: int, attack: float, release: float, rate: int = RATE) -> np.ndarray:
    """Pure logic. A rise over `attack` seconds and an exponential fall to near silence over `release` seconds."""
    out = np.ones(n)
    a = min(n, max(1, int(attack * rate)))
    out[:a] = np.linspace(0.0, 1.0, a) ** 1.5
    tail = np.arange(n) / rate
    return out * np.exp(-np.maximum(0.0, tail - attack) * (4.6 / max(release, 0.05)))


def _room(signal: np.ndarray, rate: int = RATE, mix: float = 0.28) -> np.ndarray:
    """Pure logic. A little space around a sound: a few decaying echoes, as a small room would give."""
    out = signal.copy()
    for delay, gain in ((0.029, 0.42), (0.041, 0.36), (0.067, 0.28), (0.089, 0.22), (0.131, 0.15)):
        d = int(delay * rate)
        out[d:] += signal[:-d] * gain * mix * 2
    return out


def _bell(freq: float, seconds: float, rate: int = RATE) -> np.ndarray:
    """Pure logic. A soft bell: a fundamental with gently inharmonic partials, a quick strike and a long fall."""
    t = _t(seconds, rate)
    tone = (np.sin(2 * np.pi * freq * t) + 0.32 * np.sin(2 * np.pi * freq * 2.01 * t)
            + 0.12 * np.sin(2 * np.pi * freq * 3.98 * t) * np.exp(-t * 6))
    return tone * _envelope(len(t), 0.006, seconds * 0.9, rate)


def _pad(freqs: tuple, seconds: float, attack: float, rate: int = RATE) -> np.ndarray:
    """Pure logic. A warm sustained chord: each note a few soft harmonics, slightly detuned pairs for width."""
    t = _t(seconds, rate)
    out = np.zeros(len(t))
    for f in freqs:
        for detune in (0.998, 1.002):
            for h, amp in ((1, 1.0), (2, 0.35), (3, 0.12)):
                out += amp * np.sin(2 * np.pi * f * detune * h * t)
    return out * _envelope(len(t), attack, seconds - attack, rate)


def _place(total: np.ndarray, part: np.ndarray, at: float, rate: int = RATE) -> None:
    """Adds a sound into a longer one, starting `at` seconds in."""
    start = int(at * rate)
    end = min(len(total), start + len(part))
    total[start:end] += part[:end - start]


def _warm_chord() -> np.ndarray:
    """An A major chord with a ninth, its notes arriving one after another and settling."""
    out = np.zeros(int(3.2 * RATE))
    for i, f in enumerate((220.0, 329.63, 440.0, 493.88, 554.37)):
        _place(out, _pad((f,), 3.0 - i * 0.08, 0.35), i * 0.08)
    return _room(out)


def _rising_chimes() -> np.ndarray:
    """Four soft bells climbing an A major arpeggio, the last one ringing."""
    out = np.zeros(int(2.6 * RATE))
    for i, f in enumerate((659.25, 880.0, 1108.73, 1318.51)):
        _place(out, _bell(f, 1.9 if i == 3 else 1.1) * (0.8 if i < 3 else 1.0), i * 0.17)
    return _room(out, mix=0.35)


def _reactor() -> np.ndarray:
    """A low hum and a filtered rush rising together, settling into a deep steady tone with a faint shimmer."""
    seconds = 2.8
    t = _t(seconds)
    rise = np.clip(t / 1.3, 0, 1) ** 2
    pitch = 55 + 55 * rise
    phase = 2 * np.pi * np.cumsum(pitch) / RATE
    hum = (np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase)) * (0.25 + 0.75 * rise)
    noise = np.random.default_rng(7).standard_normal(len(t))
    for _ in range(3):  # a gentle low-pass: averaging neighbours
        noise = np.convolve(noise, np.ones(24) / 24, mode="same")
    rush = noise * 6 * np.sin(np.pi * np.clip(t / 1.5, 0, 1))
    shimmer = 0.15 * np.sin(2 * np.pi * 880 * t) * np.clip((t - 1.3) / 0.4, 0, 1)
    out = (hum + rush + shimmer) * _envelope(len(t), 0.05, seconds, RATE) ** 0.25
    out *= np.clip((seconds - t) / 0.9, 0, 1)  # a slow fade at the end
    return _room(out, mix=0.2)


def _soft_swell() -> np.ndarray:
    """A D major chord swelling up and gently away, with a high sparkle as it peaks."""
    out = _pad((293.66, 369.99, 440.0, 587.33), 3.0, 1.1)
    _place(out, _bell(1760.0, 1.4) * 0.25, 1.0)
    return _room(out)


def _ready_tone() -> np.ndarray:
    """Two friendly notes, low then high, like a device saying it's ready."""
    out = np.zeros(int(1.9 * RATE))
    _place(out, _bell(392.0, 0.6) * 0.9 + 0, 0.0)
    _place(out, _bell(587.33, 1.5), 0.22)
    return _room(out, mix=0.3)


_MAKERS = {"warm_chord": _warm_chord, "rising_chimes": _rising_chimes, "reactor": _reactor,
           "soft_swell": _soft_swell, "ready_tone": _ready_tone}


def startup_samples(sound_id: str) -> tuple[np.ndarray, int]:
    """Pure logic. One startup sound as int16 mono samples and its sample rate (KeyError for an unknown id)."""
    if sound_id == "power_up":
        return generate_boot_sound_samples(), SAMPLE_RATE
    audio = _MAKERS[sound_id]()
    fade = min(len(audio), int(0.05 * RATE))
    audio[-fade:] *= np.linspace(1.0, 0.0, fade)  # never ends on a click
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.8
    return (audio * 32767).astype(np.int16), RATE


def write_startup_wav(sound_id: str, output_path: Path) -> Path:
    """Writes one startup sound to a .wav file (KeyError for an unknown id)."""
    samples, rate = startup_samples(sound_id)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(samples.tobytes())
    return output_path
