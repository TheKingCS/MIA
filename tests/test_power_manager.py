"""
tests.test_power_manager
===========================

Unit tests for core.power_manager. should_warn_low_battery() is tested
directly with constructed PowerStatus objects (pure, deterministic —
no psutil or real battery involved). PsutilBatteryBackend/PowerManager
are tested against monkeypatched psutil.sensors_battery(), same
approach as test_system_health.py mocking psutil calls.
"""

from __future__ import annotations

from types import SimpleNamespace

import core.power_manager as power_manager_module
from core.app_context import AppContext
from core.power_manager import PowerManager, PowerStatus, PsutilBatteryBackend, should_warn_low_battery


class _FakeConfig:
    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


class _FakeNotifications:
    def __init__(self) -> None:
        self.notified: list[dict] = []

    def notify(self, title, message, level="info", source="system"):
        self.notified.append({"title": title, "message": message, "level": level, "source": source})


def _make_manager(threshold: float = 20.0) -> tuple[PowerManager, _FakeNotifications]:
    notifications = _FakeNotifications()
    context = AppContext(config=_FakeConfig({"power.low_battery_threshold_percent": threshold}), events=None)
    context.notifications = notifications
    return PowerManager(context), notifications


# ----------------------------------------------------------------------
# should_warn_low_battery (pure)
# ----------------------------------------------------------------------

def test_warns_when_low_and_unplugged_and_not_already_warned():
    status = PowerStatus(percent=15.0, plugged_in=False, seconds_left=600)
    assert should_warn_low_battery(status, threshold_percent=20.0, already_warned=False) is True


def test_does_not_warn_again_if_already_warned():
    status = PowerStatus(percent=15.0, plugged_in=False, seconds_left=600)
    assert should_warn_low_battery(status, threshold_percent=20.0, already_warned=True) is False


def test_does_not_warn_when_plugged_in():
    status = PowerStatus(percent=15.0, plugged_in=True, seconds_left=None)
    assert should_warn_low_battery(status, threshold_percent=20.0, already_warned=False) is False


def test_does_not_warn_when_above_threshold():
    status = PowerStatus(percent=50.0, plugged_in=False, seconds_left=None)
    assert should_warn_low_battery(status, threshold_percent=20.0, already_warned=False) is False


def test_warns_at_exact_threshold():
    status = PowerStatus(percent=20.0, plugged_in=False, seconds_left=None)
    assert should_warn_low_battery(status, threshold_percent=20.0, already_warned=False) is True


# ----------------------------------------------------------------------
# PsutilBatteryBackend / PowerManager.read() / is_available()
# ----------------------------------------------------------------------

def test_backend_raises_when_no_battery(monkeypatch):
    monkeypatch.setattr(power_manager_module.psutil, "sensors_battery", lambda: None)
    backend = PsutilBatteryBackend()
    manager, _ = _make_manager()
    manager._backend = backend
    assert manager.read() is None
    assert manager.is_available() is False


def test_backend_reads_real_values(monkeypatch):
    monkeypatch.setattr(
        power_manager_module.psutil,
        "sensors_battery",
        lambda: SimpleNamespace(percent=73.0, secsleft=3600, power_plugged=False),
    )
    manager, _ = _make_manager()
    status = manager.read()
    assert status == PowerStatus(percent=73.0, plugged_in=False, seconds_left=3600)
    assert manager.is_available() is True


def test_backend_normalizes_unlimited_secsleft_to_none(monkeypatch):
    monkeypatch.setattr(
        power_manager_module.psutil,
        "sensors_battery",
        lambda: SimpleNamespace(
            percent=100.0, secsleft=power_manager_module.psutil.POWER_TIME_UNLIMITED, power_plugged=True
        ),
    )
    manager, _ = _make_manager()
    status = manager.read()
    assert status.seconds_left is None
    assert status.plugged_in is True


# ----------------------------------------------------------------------
# PowerManager.check_low_battery() (state machine)
# ----------------------------------------------------------------------

def test_check_low_battery_notifies_once_then_stays_quiet(monkeypatch):
    manager, notifications = _make_manager(threshold=20.0)
    monkeypatch.setattr(
        power_manager_module.psutil,
        "sensors_battery",
        lambda: SimpleNamespace(percent=10.0, secsleft=600, power_plugged=False),
    )

    manager.check_low_battery()
    manager.check_low_battery()
    manager.check_low_battery()

    assert len(notifications.notified) == 1
    assert notifications.notified[0]["level"] == "warning"


def test_check_low_battery_warns_again_after_recovering_and_dipping_again(monkeypatch):
    manager, notifications = _make_manager(threshold=20.0)

    monkeypatch.setattr(
        power_manager_module.psutil,
        "sensors_battery",
        lambda: SimpleNamespace(percent=10.0, secsleft=600, power_plugged=False),
    )
    manager.check_low_battery()
    assert len(notifications.notified) == 1

    monkeypatch.setattr(
        power_manager_module.psutil,
        "sensors_battery",
        lambda: SimpleNamespace(percent=80.0, secsleft=None, power_plugged=True),
    )
    manager.check_low_battery()
    assert len(notifications.notified) == 1  # recovering doesn't itself notify

    monkeypatch.setattr(
        power_manager_module.psutil,
        "sensors_battery",
        lambda: SimpleNamespace(percent=10.0, secsleft=600, power_plugged=False),
    )
    manager.check_low_battery()
    assert len(notifications.notified) == 2


def test_check_low_battery_does_nothing_when_no_battery(monkeypatch):
    manager, notifications = _make_manager()
    monkeypatch.setattr(power_manager_module.psutil, "sensors_battery", lambda: None)
    manager.check_low_battery()
    assert notifications.notified == []
