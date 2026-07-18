"""
tests.test_voice_manager
==========================

Unit tests for core.voice_manager's VoiceManager delegation and
graceful-degradation logic. Uses fake STT/TTS backends (same shape as
test_llm_manager.py's mocked urlopen) rather than loading the real
Vosk/Piper models, so this suite stays fast and independent of
voice_models/ being present. The real Piper -> Vosk round trip (and
the "no PortAudio" recording/playback degrade path) were verified
manually against the actual libraries, since they need real model
files / real system behavior this suite deliberately avoids depending
on for a fast, portable test run.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from core.app_context import AppContext
from core.voice_manager import VoiceManager, VoiceUnavailableError, apply_playback_volume


class _FakeConfig:
    """Minimal stand-in for ConfigManager — `.get(key, default)` plus
    `.set()`/`.save()` for the voice-switching tests below."""

    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides
        self.saved = False

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)

    def set(self, key: str, value) -> None:
        self._overrides[key] = value

    def save(self) -> None:
        self.saved = True


class _FakeSTTBackend:
    available = True

    def __init__(self, text: str = "hello", fail: bool = False) -> None:
        self._text = text
        self._fail = fail

    def transcribe(self, wav_path: Path) -> str:
        if self._fail:
            raise VoiceUnavailableError("boom")
        return self._text


class _FakeTTSBackend:
    available = True

    def __init__(self, fail: bool = False) -> None:
        self._fail = fail
        self.synthesized: list = []

    def synthesize(self, text: str, output_path: Path) -> None:
        if self._fail:
            raise VoiceUnavailableError("boom")
        self.synthesized.append((text, output_path))


def _make_manager() -> VoiceManager:
    context = AppContext(config=_FakeConfig({}), events=None)
    return VoiceManager(context)


def test_transcribe_returns_backend_text():
    manager = _make_manager()
    manager._stt = _FakeSTTBackend(text="turn on the light")
    assert manager.transcribe(Path("/tmp/x.wav")) == "turn on the light"


def test_transcribe_returns_none_when_backend_unavailable():
    manager = _make_manager()
    manager._stt = _FakeSTTBackend(fail=True)
    assert manager.transcribe(Path("/tmp/x.wav")) is None


def test_synthesize_returns_output_path_on_success():
    manager = _make_manager()
    fake_tts = _FakeTTSBackend()
    manager._tts = fake_tts
    result = manager.synthesize("hello", Path("/tmp/out.wav"))
    assert result == Path("/tmp/out.wav")
    assert fake_tts.synthesized == [("hello", Path("/tmp/out.wav"))]


def test_synthesize_returns_none_when_backend_unavailable():
    manager = _make_manager()
    manager._tts = _FakeTTSBackend(fail=True)
    assert manager.synthesize("hello", Path("/tmp/out.wav")) is None


def test_is_stt_available_reflects_backend():
    manager = _make_manager()
    manager._stt = _FakeSTTBackend()
    assert manager.is_stt_available() is True


def test_start_recording_false_when_sounddevice_unavailable(monkeypatch):
    import core.voice_manager as voice_manager_module

    monkeypatch.setattr(voice_manager_module, "_sd", None)
    manager = _make_manager()
    assert manager.start_recording() is False


def test_play_false_when_sounddevice_unavailable(monkeypatch):
    import core.voice_manager as voice_manager_module

    monkeypatch.setattr(voice_manager_module, "_sd", None)
    manager = _make_manager()
    assert manager.play(Path("/tmp/x.wav")) is False


def test_stop_recording_returns_none_when_never_started():
    manager = _make_manager()
    assert manager.stop_recording() is None


def test_list_available_voices_only_returns_files_present_on_disk(tmp_path, monkeypatch):
    import core.voice_manager as voice_manager_module

    monkeypatch.setattr(voice_manager_module, "_VOICE_MODELS_DIR", tmp_path)
    (tmp_path / "en_US-lessac-low.onnx").write_bytes(b"")
    (tmp_path / "en_US-amy-low.onnx").write_bytes(b"")

    manager = _make_manager()
    available_ids = {option.voice_id for option in manager.list_available_voices()}
    assert available_ids == {"en_US-lessac-low", "en_US-amy-low"}


def test_set_voice_switches_and_persists_when_model_present(tmp_path, monkeypatch):
    import core.voice_manager as voice_manager_module

    monkeypatch.setattr(voice_manager_module, "_VOICE_MODELS_DIR", tmp_path)
    (tmp_path / "en_US-lessac-low.onnx").write_bytes(b"")
    (tmp_path / "en_US-ryan-medium.onnx").write_bytes(b"")

    config = _FakeConfig({})
    context = AppContext(config=config, events=None)
    manager = VoiceManager(context)

    assert manager.set_voice("en_US-ryan-medium") is True
    assert manager.current_voice_id == "en_US-ryan-medium"
    assert config.get("voice.tts_voice_id") == "en_US-ryan-medium"
    assert config.saved is True


def test_set_voice_returns_false_and_makes_no_change_when_model_missing(tmp_path, monkeypatch):
    import core.voice_manager as voice_manager_module

    monkeypatch.setattr(voice_manager_module, "_VOICE_MODELS_DIR", tmp_path)
    (tmp_path / "en_US-lessac-low.onnx").write_bytes(b"")

    manager = _make_manager()
    assert manager.set_voice("en_US-amy-low") is False
    assert manager.current_voice_id == "en_US-lessac-low"


# ----------------------------------------------------------------------
# apply_playback_volume — pure gain logic, no audio hardware needed
# ----------------------------------------------------------------------

def test_apply_playback_volume_at_1x_returns_audio_unchanged():
    audio = np.array([100, -200, 300], dtype=np.int16)
    result = apply_playback_volume(audio, 1.0)
    assert np.array_equal(result, audio)


def test_apply_playback_volume_amplifies_quiet_audio():
    audio = np.array([100, -200, 300], dtype=np.int16)
    result = apply_playback_volume(audio, 2.0)
    assert list(result) == [200, -400, 600]


def test_apply_playback_volume_attenuates_below_1x():
    audio = np.array([1000, -1000], dtype=np.int16)
    result = apply_playback_volume(audio, 0.5)
    assert list(result) == [500, -500]


def test_apply_playback_volume_clips_rather_than_wraps_on_overflow():
    # A bare (audio * volume).astype(int16) would wrap 32767*2 around to
    # a negative number instead of clipping — this is exactly the bug
    # apply_playback_volume() exists to avoid.
    audio = np.array([32767, -32768], dtype=np.int16)
    result = apply_playback_volume(audio, 2.0)
    assert list(result) == [32767, -32768]


def test_apply_playback_volume_result_stays_int16():
    audio = np.array([100, 200], dtype=np.int16)
    result = apply_playback_volume(audio, 1.4)
    assert result.dtype == np.int16
