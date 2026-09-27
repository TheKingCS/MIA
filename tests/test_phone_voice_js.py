"""
tests.test_phone_voice_js
============================

Runs server/static/voice.js (the phone's microphone/end-of-speech/WAV
code) under Node via tests/js/voice_harness.js, and checks the WAV it
produces against the server's own validator — so the phone and the
computer at home are proven to agree on the audio format. Skipped when
Node isn't installed.
"""

from __future__ import annotations

import base64
import io
import json
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from server.app import validate_voice_wav

_HARNESS = Path(__file__).resolve().parent / "js" / "voice_harness.js"
_NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(_NODE is None, reason="Node.js not installed")


def _run(scenario: str) -> dict:
    out = subprocess.run([_NODE, str(_HARNESS), scenario], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(out.stdout)


def test_encoded_wav_is_16k_mono_pcm_and_accepted_by_the_server():
    result = _run("wav")
    audio = base64.b64decode(result["base64"])
    validate_voice_wav(audio)
    with wave.open(io.BytesIO(audio), "rb") as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getnframes() == result["samples"] == 16000  # 1 s at 48 kHz -> 16 kHz


def test_speech_then_silence_ends_the_utterance_with_pre_roll():
    result = _run("speech")
    assert "speech" in result["states"]
    assert result["states"][-1] == "done"
    # 1.5 s of speech plus pre-roll and trailing silence, never less than the speech itself.
    assert result["utteranceSamples"] >= 48000 * 1.5


def test_short_noise_burst_is_not_treated_as_speech():
    result = _run("cough")
    assert result["utteranceSamples"] is None
    assert result["states"][-1] == "idle"


def test_long_speech_is_cut_at_the_maximum_length():
    result = _run("max")
    assert result["states"][-1] == "done"
    assert result["utteranceSamples"] <= 48000 * 2.2


def test_speech_is_still_detected_over_steady_background_noise():
    result = _run("noisy")
    assert result["states"][-1] == "done"
    assert result["utteranceSamples"] >= 48000 * 1.5
