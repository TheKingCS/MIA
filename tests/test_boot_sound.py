"""
tests.test_boot_sound
========================

Unit tests for core.boot_sound.generate_boot_sound_samples() — pure
synthesis logic, no audio hardware/I/O involved (see that module's
docstring for why real playback can't be verified in this dev
sandbox). write_boot_sound_wav() is exercised via a real tmp_path file
write/read round trip, same reasoning test_script_runner.py gives for
using real filesystem operations when no special hardware is needed.
"""

from __future__ import annotations

import wave

import numpy as np

from core.boot_sound import generate_boot_sound_samples, write_boot_sound_wav


def test_generates_correct_sample_count():
    samples = generate_boot_sound_samples(duration_seconds=2.0, sample_rate=22050)
    assert len(samples) == int(2.0 * 22050)


def test_generates_int16_samples():
    samples = generate_boot_sound_samples(duration_seconds=1.0, sample_rate=22050)
    assert samples.dtype == np.int16


def test_generates_real_non_silent_audio():
    samples = generate_boot_sound_samples(duration_seconds=1.0, sample_rate=22050)
    assert np.abs(samples).max() > 0


def test_does_not_clip_full_scale():
    """Normalized to 0.8 peak, not 1.0 — leaves headroom rather than
    hitting the exact int16 boundary."""
    samples = generate_boot_sound_samples(duration_seconds=2.0, sample_rate=22050)
    assert np.abs(samples).max() < 32767


def test_starts_near_silence_growing_in():
    """The "growing" envelope fades in from silence — the very first
    samples should be much quieter than the loudest part of the clip."""
    samples = generate_boot_sound_samples(duration_seconds=3.5, sample_rate=22050)
    early = np.abs(samples[:200]).mean()
    loudest = np.abs(samples).max()
    assert early < loudest * 0.3


def test_ends_near_silence_fading_out():
    """The fade-out avoids an audible click when playback stops."""
    samples = generate_boot_sound_samples(duration_seconds=3.5, sample_rate=22050)
    late = np.abs(samples[-50:]).mean()
    loudest = np.abs(samples).max()
    assert late < loudest * 0.2


def test_different_durations_produce_different_lengths():
    short = generate_boot_sound_samples(duration_seconds=1.0, sample_rate=22050)
    long = generate_boot_sound_samples(duration_seconds=2.0, sample_rate=22050)
    assert len(long) == 2 * len(short)


def test_write_boot_sound_wav_produces_a_real_readable_wav_file(tmp_path):
    output_path = tmp_path / "boot_sound.wav"
    write_boot_sound_wav(output_path, duration_seconds=1.0, sample_rate=22050)

    assert output_path.exists()
    with wave.open(str(output_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 22050
        assert wf.getnframes() == 22050
