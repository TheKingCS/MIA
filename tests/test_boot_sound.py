"""
tests.test_boot_sound
========================

Unit tests for core.boot_sound — pure synthesis logic, no audio
hardware/I/O involved (see that module's docstring for why real
playback can't be verified in this dev sandbox). write_boot_sound_wav()
is exercised via a real tmp_path file write/read round trip, same
reasoning test_script_runner.py gives for using real filesystem
operations when no special hardware is needed.
"""

from __future__ import annotations

import wave

import numpy as np

from core.boot_sound import (
    _generate_ping,
    _generate_sweep,
    generate_boot_sound_samples,
    write_boot_sound_wav,
)


# ----------------------------------------------------------------------
# generate_boot_sound_samples — the combined sweep + ping
# ----------------------------------------------------------------------

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
    """Normalized to 0.85 peak, not 1.0 — leaves headroom rather than
    hitting the exact int16 boundary."""
    samples = generate_boot_sound_samples(duration_seconds=2.0, sample_rate=22050)
    assert np.abs(samples).max() < 32767


def test_starts_near_silence_growing_in():
    """The "growing" envelope fades in from silence — the very first
    samples should be much quieter than the loudest part of the clip."""
    samples = generate_boot_sound_samples(duration_seconds=3.9, sample_rate=22050)
    early = np.abs(samples[:200]).mean()
    loudest = np.abs(samples).max()
    assert early < loudest * 0.3


def test_ends_with_the_ping_decayed_to_near_silence():
    """The ping's own exponential decay means the very last samples are
    quiet, even though the ping's attack itself is one of the loudest
    moments in the whole clip — avoids an audible click when playback
    stops."""
    samples = generate_boot_sound_samples(duration_seconds=3.9, sample_rate=22050)
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


# ----------------------------------------------------------------------
# _generate_sweep — the "woooooooom"
# ----------------------------------------------------------------------

def test_sweep_has_no_fade_out_at_its_own_end():
    """The sweep hands off directly into the ping — it shouldn't fade
    to silence on its own, unlike the old single-envelope design.
    Compares RMS energy of the last 10% against the prior 10% (rather
    than a tiny fixed tail window against the global peak) since the
    pulsing envelope's own oscillation can naturally land near a low
    point at any arbitrary cutoff — a real fade-out shows up as a
    systematic drop across that whole final chunk, not a momentary dip."""
    sweep = _generate_sweep(duration_seconds=2.0, sample_rate=22050)
    chunk = len(sweep) // 10
    last_chunk_rms = np.sqrt(np.mean(sweep[-chunk:] ** 2))
    prior_chunk_rms = np.sqrt(np.mean(sweep[-2 * chunk : -chunk] ** 2))
    assert last_chunk_rms > prior_chunk_rms * 0.5


def test_sweep_correct_sample_count():
    sweep = _generate_sweep(duration_seconds=1.5, sample_rate=22050)
    assert len(sweep) == int(1.5 * 22050)


# ----------------------------------------------------------------------
# _generate_ping — the bright chime
# ----------------------------------------------------------------------

def test_ping_attack_is_near_the_loudest_point():
    """A bell-like ping is loudest right after its short attack, then
    decays — not a slow swell like the sweep."""
    ping = _generate_ping(duration_seconds=0.6, sample_rate=22050)
    attack_end = int(0.01 * 22050)
    early_peak = np.abs(ping[:attack_end]).max()
    overall_peak = np.abs(ping).max()
    assert early_peak >= overall_peak * 0.9


def test_ping_decays_to_near_silence():
    ping = _generate_ping(duration_seconds=0.6, sample_rate=22050)
    late = np.abs(ping[-50:]).mean()
    loudest = np.abs(ping).max()
    assert late < loudest * 0.1


def test_ping_correct_sample_count():
    ping = _generate_ping(duration_seconds=0.6, sample_rate=22050)
    assert len(ping) == int(0.6 * 22050)
