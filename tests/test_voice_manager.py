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

from core.app_context import AppContext
from core.voice_manager import VoiceManager, VoiceUnavailableError


class _FakeConfig:
    """Minimal stand-in for ConfigManager, just enough for `.get(key, default)`."""

    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


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
