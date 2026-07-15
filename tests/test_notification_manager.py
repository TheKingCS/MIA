"""
tests.test_notification_manager
===================================

Unit tests for core.notification_manager — previously untested (a
real, pre-existing gap, not something this file tries to backfill in
full). Added now specifically to cover notify()'s new
"notifications.enabled" gate (2026-07-15 "ForMIA" design handoff's
Quick Bus widget) — the first real, non-cosmetic behavior that
toggle drives.

Isolates _DATA_DIR/_NOTIFICATIONS_FILE into a tmp_path scratch area,
same monkeypatch pattern as tests/test_mission_manager.py's
isolated_paths. Uses a fake config (get/set only, no real ConfigManager
needed) since these tests only ever read the flag, never save it.
"""

from __future__ import annotations

import pytest

import core.notification_manager as notification_manager_module
from core.app_context import AppContext
from core.event_bus import EventBus
from core.notification_manager import NotificationManager


class _FakeConfig:
    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(notification_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(notification_manager_module, "_NOTIFICATIONS_FILE", data_dir / "notifications.json")


def _make_context(config_overrides: dict | None = None) -> AppContext:
    context = AppContext(config=_FakeConfig(config_overrides or {}), events=EventBus())
    context.notifications = NotificationManager(context)
    return context


def test_notify_creates_and_returns_notification_by_default(isolated_paths):
    context = _make_context()
    result = context.notifications.notify(title="Test", message="hello")
    assert result is not None
    assert result.title == "Test"
    assert len(context.notifications.list_all()) == 1


def test_notify_returns_none_and_creates_nothing_when_disabled(isolated_paths):
    context = _make_context({"notifications.enabled": False})
    result = context.notifications.notify(title="Test", message="hello")
    assert result is None
    assert context.notifications.list_all() == []


def test_notify_publishes_event_only_when_enabled(isolated_paths):
    context = _make_context({"notifications.enabled": False})
    received = []
    context.events.subscribe("notification.created", lambda **kwargs: received.append(kwargs))
    context.notifications.notify(title="Test", message="hello")
    assert received == []
