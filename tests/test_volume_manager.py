"""
tests.test_volume_manager
============================

Unit tests for core.volume_manager. parse_amixer_output() is tested
directly against captured-shape amixer text (pure, deterministic — no
real amixer binary involved, same reasoning as test_power_manager.py
mocking psutil). AmixerVolumeBackend/VolumeManager are tested against
monkeypatched subprocess.run().
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import core.volume_manager as volume_manager_module
from core.app_context import AppContext
from core.volume_manager import (
    AmixerVolumeBackend,
    VolumeManager,
    VolumeStatus,
    VolumeUnavailableError,
    parse_amixer_output,
)


def _make_manager() -> VolumeManager:
    context = AppContext(config=None, events=None)
    return VolumeManager(context)


# ----------------------------------------------------------------------
# parse_amixer_output (pure)
# ----------------------------------------------------------------------

_SAMPLE_MONO_OUTPUT = """Simple mixer control 'Master',0
  Capabilities: pswitch pswitch-joined pvolume pvolume-joined
  Playback channels: Mono
  Limits: Playback 0 - 65536
  Mono: Playback 32768 [50%] [on]
"""

_SAMPLE_STEREO_MUTED_OUTPUT = """Simple mixer control 'Master',0
  Capabilities: pswitch pswitch-joined pvolume pvolume-joined
  Playback channels: Front Left - Front Right
  Limits: Playback 0 - 65536
  Front Left: Playback 0 [0%] [off]
  Front Right: Playback 0 [0%] [off]
"""


def test_parses_mono_output():
    status = parse_amixer_output(_SAMPLE_MONO_OUTPUT)
    assert status == VolumeStatus(percent=50, muted=False)


def test_parses_stereo_muted_output():
    status = parse_amixer_output(_SAMPLE_STEREO_MUTED_OUTPUT)
    assert status == VolumeStatus(percent=0, muted=True)


def test_returns_none_for_unrecognizable_output():
    assert parse_amixer_output("amixer: Unable to find simple control 'Master',0") is None


def test_returns_none_for_empty_output():
    assert parse_amixer_output("") is None


# ----------------------------------------------------------------------
# AmixerVolumeBackend (subprocess mocked)
# ----------------------------------------------------------------------

def test_backend_read_raises_when_amixer_missing(monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(volume_manager_module.subprocess, "run", _raise)
    backend = AmixerVolumeBackend()
    try:
        backend.read()
        assert False, "expected VolumeUnavailableError"
    except VolumeUnavailableError:
        pass


def test_backend_read_raises_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        volume_manager_module.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="no such control"),
    )
    backend = AmixerVolumeBackend()
    try:
        backend.read()
        assert False, "expected VolumeUnavailableError"
    except VolumeUnavailableError:
        pass


def test_backend_read_succeeds(monkeypatch):
    monkeypatch.setattr(
        volume_manager_module.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=_SAMPLE_MONO_OUTPUT, stderr=""),
    )
    backend = AmixerVolumeBackend()
    assert backend.read() == VolumeStatus(percent=50, muted=False)


def test_backend_set_volume_invokes_amixer_with_percent(monkeypatch):
    calls = []
    monkeypatch.setattr(
        volume_manager_module.subprocess,
        "run",
        lambda args, **k: calls.append(args) or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    backend = AmixerVolumeBackend()
    backend.set_volume(75)
    assert calls == [["amixer", "set", "75%", "Master"]]


def test_backend_toggle_mute_invokes_amixer_toggle(monkeypatch):
    calls = []
    monkeypatch.setattr(
        volume_manager_module.subprocess,
        "run",
        lambda args, **k: calls.append(args) or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    backend = AmixerVolumeBackend()
    backend.toggle_mute()
    assert calls == [["amixer", "set", "toggle", "Master"]]


def test_backend_read_raises_on_timeout(monkeypatch):
    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="amixer", timeout=2.0)

    monkeypatch.setattr(volume_manager_module.subprocess, "run", _raise)
    backend = AmixerVolumeBackend()
    try:
        backend.read()
        assert False, "expected VolumeUnavailableError"
    except VolumeUnavailableError:
        pass


# ----------------------------------------------------------------------
# VolumeManager (degrade-gracefully wrapper)
# ----------------------------------------------------------------------

def test_manager_is_available_false_when_backend_unavailable():
    manager = _make_manager()

    class _AlwaysFails:
        def read(self):
            raise VolumeUnavailableError("no amixer")

        def set_volume(self, percent):
            raise VolumeUnavailableError("no amixer")

        def toggle_mute(self):
            raise VolumeUnavailableError("no amixer")

    manager._backend = _AlwaysFails()
    assert manager.is_available() is False
    assert manager.read() is None
    assert manager.set_volume(50) is False
    assert manager.toggle_mute() is False


def test_manager_reflects_working_backend():
    manager = _make_manager()

    class _Working:
        def __init__(self):
            self.set_calls = []

        def read(self):
            return VolumeStatus(percent=60, muted=False)

        def set_volume(self, percent):
            self.set_calls.append(percent)

        def toggle_mute(self):
            pass

    backend = _Working()
    manager._backend = backend
    assert manager.is_available() is True
    assert manager.read() == VolumeStatus(percent=60, muted=False)
    assert manager.set_volume(80) is True
    assert backend.set_calls == [80]
    assert manager.toggle_mute() is True


def test_manager_set_volume_clamps_to_valid_range():
    manager = _make_manager()

    class _Recording:
        def __init__(self):
            self.set_calls = []

        def read(self):
            return VolumeStatus(percent=0, muted=False)

        def set_volume(self, percent):
            self.set_calls.append(percent)

        def toggle_mute(self):
            pass

    backend = _Recording()
    manager._backend = backend
    manager.set_volume(150)
    manager.set_volume(-20)
    assert backend.set_calls == [100, 0]
