"""
tests.test_avatar_manager
============================

Unit tests for core.avatar_manager. list_devices()/is_available() are
tested against a monkeypatched QMediaDevices.videoInputs() (same
"mock the OS-level query, test our own mapping/decision logic"
reasoning as test_power_manager.py mocking psutil and
test_volume_manager.py mocking subprocess.run) — no real camera device
is involved, matching this dev sandbox having none at all. selected_device_id()/
set_selected_device_id() are tested against a fake config, same shape
as tests/test_dashboard_widgets.py.
"""

from __future__ import annotations

from PySide6.QtMultimedia import QMediaDevices

from core.app_context import AppContext
from core.avatar_manager import AvatarManager, CameraDeviceInfo
from core.event_bus import EventBus


class _FakeConfig:
    def __init__(self, overrides: dict | None = None) -> None:
        self._overrides = overrides or {}
        self.saved = False

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)

    def set(self, key: str, value) -> None:
        self._overrides[key] = value

    def save(self) -> None:
        self.saved = True


class _FakeCameraDevice:
    def __init__(self, device_id: bytes, description: str) -> None:
        self._device_id = device_id
        self._description = description

    def id(self):
        return self._device_id

    def description(self) -> str:
        return self._description


def _make_manager(overrides: dict | None = None) -> AvatarManager:
    context = AppContext(config=_FakeConfig(overrides), events=EventBus())
    return AvatarManager(context)


# ----------------------------------------------------------------------
# list_devices / is_available (QMediaDevices mocked)
# ----------------------------------------------------------------------

def test_list_devices_empty_when_no_cameras(monkeypatch):
    monkeypatch.setattr(QMediaDevices, "videoInputs", staticmethod(lambda: []))
    manager = _make_manager()
    assert manager.list_devices() == []
    assert manager.is_available() is False


def test_list_devices_maps_real_devices(monkeypatch):
    devices = [
        _FakeCameraDevice(b"cam-1", "Webcam"),
        _FakeCameraDevice(b"cam-2", "VMagicMirror Virtual Camera"),
    ]
    monkeypatch.setattr(QMediaDevices, "videoInputs", staticmethod(lambda: devices))
    manager = _make_manager()
    assert manager.list_devices() == [
        CameraDeviceInfo(device_id="cam-1", description="Webcam"),
        CameraDeviceInfo(device_id="cam-2", description="VMagicMirror Virtual Camera"),
    ]
    assert manager.is_available() is True


def test_list_devices_returns_empty_on_enumeration_error(monkeypatch):
    def _raise():
        raise RuntimeError("no multimedia backend")

    monkeypatch.setattr(QMediaDevices, "videoInputs", staticmethod(_raise))
    manager = _make_manager()
    assert manager.list_devices() == []
    assert manager.is_available() is False


# ----------------------------------------------------------------------
# selected_device_id / set_selected_device_id (config-backed)
# ----------------------------------------------------------------------

def test_selected_device_id_defaults_to_none():
    manager = _make_manager()
    assert manager.selected_device_id() is None


def test_selected_device_id_reflects_config():
    manager = _make_manager({"dashboard.avatar_camera_device": "cam-2"})
    assert manager.selected_device_id() == "cam-2"


def test_set_selected_device_id_persists_and_publishes():
    manager = _make_manager()
    published = []
    manager.context.events.subscribe("dashboard.avatar_device_changed", lambda: published.append(True))

    manager.set_selected_device_id("cam-2")

    assert manager.selected_device_id() == "cam-2"
    assert manager.context.config.saved is True
    assert published == [True]
