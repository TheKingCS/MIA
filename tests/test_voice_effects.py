"""
tests.test_voice_effects
===========================

Unit tests for core.voice_effects' pure-numpy DSP functions. These
test shape/dtype/range invariants (no clipping, no silent volume
change, correct dtype) — not perceived audio quality, which no
automated test can judge; see that module's docstring.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from core.voice_effects import (
    apply_ai_voice_effect,
    apply_ai_voice_effect_to_wav_file,
    apply_chorus,
    apply_ring_modulation,
)

_SAMPLE_RATE = 16000


def _tone(seconds: float = 0.5, freq: float = 220.0, amplitude: int = 20000) -> np.ndarray:
    t = np.arange(int(_SAMPLE_RATE * seconds)) / _SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16)


def test_apply_ring_modulation_zero_mix_returns_original():
    samples = _tone()
    result = apply_ring_modulation(samples, _SAMPLE_RATE, carrier_hz=40.0, mix=0.0)
    assert np.allclose(result, samples.astype(np.float64))


def test_apply_ring_modulation_preserves_length():
    samples = _tone()
    result = apply_ring_modulation(samples, _SAMPLE_RATE, carrier_hz=40.0, mix=0.5)
    assert len(result) == len(samples)


def test_apply_ring_modulation_nonzero_mix_changes_signal():
    samples = _tone()
    result = apply_ring_modulation(samples, _SAMPLE_RATE, carrier_hz=40.0, mix=0.5)
    assert not np.allclose(result, samples.astype(np.float64))


def test_apply_chorus_zero_mix_returns_original():
    samples = _tone()
    result = apply_chorus(samples, _SAMPLE_RATE, delay_ms=18.0, mix=0.0)
    assert np.allclose(result, samples.astype(np.float64))


def test_apply_chorus_preserves_length():
    samples = _tone()
    result = apply_chorus(samples, _SAMPLE_RATE, delay_ms=18.0, mix=0.3)
    assert len(result) == len(samples)


def test_apply_ai_voice_effect_returns_int16():
    samples = _tone()
    result = apply_ai_voice_effect(samples, _SAMPLE_RATE)
    assert result.dtype == np.int16


def test_apply_ai_voice_effect_preserves_length():
    samples = _tone()
    result = apply_ai_voice_effect(samples, _SAMPLE_RATE)
    assert len(result) == len(samples)


def test_apply_ai_voice_effect_does_not_clip():
    samples = _tone(amplitude=32000)
    result = apply_ai_voice_effect(samples, _SAMPLE_RATE)
    assert np.max(np.abs(result)) <= 32767


def test_apply_ai_voice_effect_roughly_preserves_peak_volume():
    samples = _tone(amplitude=20000)
    result = apply_ai_voice_effect(samples, _SAMPLE_RATE)
    original_peak = np.max(np.abs(samples.astype(np.int64)))
    result_peak = np.max(np.abs(result.astype(np.int64)))
    # Peak-normalized against the original — should land close to it,
    # not silently much quieter or louder.
    assert abs(result_peak - original_peak) / original_peak < 0.05


def test_apply_ai_voice_effect_to_wav_file_round_trips(tmp_path):
    wav_path = tmp_path / "test.wav"
    samples = _tone()
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(_SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())

    apply_ai_voice_effect_to_wav_file(Path(wav_path))

    with wave.open(str(wav_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == _SAMPLE_RATE
        frames = wav_file.readframes(wav_file.getnframes())
    processed = np.frombuffer(frames, dtype=np.int16)
    assert len(processed) == len(samples)
    assert not np.allclose(processed, samples)


def test_apply_ai_voice_effect_to_wav_file_skips_stereo(tmp_path):
    wav_path = tmp_path / "stereo.wav"
    samples = _tone()
    stereo = np.repeat(samples, 2)  # interleaved L/R, same value
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(_SAMPLE_RATE)
        wav_file.writeframes(stereo.tobytes())

    original_bytes = wav_path.read_bytes()
    apply_ai_voice_effect_to_wav_file(Path(wav_path))
    assert wav_path.read_bytes() == original_bytes
