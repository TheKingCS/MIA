"""
tests.test_data_recovery
============================

Unit tests for core.data_recovery.notify_data_corruption.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_recovery import notify_data_corruption
from core.event_bus import EventBus


class _FakeNotifications:
    """Notifications that are only remembered, so a test can see what was raised."""
    def __init__(self):
        """None raised yet."""
        self.calls = []

    def notify(self, title, message, level="info", source="system"):
        """Remembers a notification."""
        self.calls.append({"title": title, "message": message, "level": level, "source": source})


def test_notify_data_corruption_raises_a_real_notification():
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = _FakeNotifications()

    notify_data_corruption(context, "skill_progress.json")

    assert len(context.notifications.calls) == 1
    call = context.notifications.calls[0]
    assert "skill_progress.json" in call["message"]
    assert call["level"] == "warning"


def test_notify_data_corruption_with_no_notifications_service_does_not_raise():
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = None
    notify_data_corruption(context, "skill_progress.json")  # must not raise


class _BrokenNotifications:
    """Notifications that always fail, to show a damaged-file warning never takes MIA down with it."""
    def notify(self, *args, **kwargs):
        """Fails, as a broken notification pipeline would."""
        raise RuntimeError("simulated failure inside the notification pipeline itself")


def test_notify_data_corruption_never_raises_even_if_notify_itself_fails():
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = _BrokenNotifications()
    notify_data_corruption(context, "skill_progress.json")  # must not raise
