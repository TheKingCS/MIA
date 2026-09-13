"""
tests.test_web_push
======================

Unit tests for core.web_push. The actual push-service HTTP call
(pywebpush.webpush) is mocked throughout — this is the standard,
correct way to test Web Push code without a real browser/push service
(see core/web_push.py's own docstring and the Mobile Phase 1 plan).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests
from pywebpush import WebPushException

import core.notification_manager as notification_manager_module
import core.push_subscription_manager as push_subscription_manager_module
import core.web_push as web_push_module
from core.app_context import AppContext
from core.event_bus import EventBus
from core.push_subscription_manager import PushSubscriptionManager
from core.notification_manager import Notification
from core.web_push import (
    get_or_create_vapid_keys,
    register_notification_relay,
    send_web_push,
)
from core.web_push import _relay_notification_to_all_subscriptions


class _FakeConfig:
    def get(self, key: str, default=None):
        return default


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(web_push_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(web_push_module, "_VAPID_KEYS_FILE", data_dir / "vapid_keys.json")
    monkeypatch.setattr(push_subscription_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(push_subscription_manager_module, "_SUBSCRIPTIONS_FILE", data_dir / "push_subscriptions.json")
    monkeypatch.setattr(notification_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(notification_manager_module, "_NOTIFICATIONS_FILE", data_dir / "notifications.json")


@pytest.fixture
def subscriptions(isolated_paths) -> PushSubscriptionManager:
    context = AppContext(config=_FakeConfig(), events=EventBus())
    return PushSubscriptionManager(context)


@pytest.fixture
def context(isolated_paths) -> AppContext:
    ctx = AppContext(config=_FakeConfig(), events=EventBus())
    ctx.push_subscriptions = PushSubscriptionManager(ctx)
    return ctx


def test_get_or_create_vapid_keys_generates_once_and_persists(isolated_paths):
    private1, public1 = get_or_create_vapid_keys()
    assert len(private1) > 0
    assert "BEGIN" not in private1  # DER-base64, not PEM — see this module's own note on why
    assert len(public1) > 0

    private2, public2 = get_or_create_vapid_keys()
    assert (private1, public1) == (private2, public2)


def test_get_or_create_vapid_keys_private_key_is_usable_by_pywebpush(isolated_paths):
    """Regression test for a real bug caught in this feature's own
    manual end-to-end verification: pywebpush.webpush() (via
    py_vapid.Vapid.from_string()) rejects a PEM-formatted private key
    string outright — only base64url DER round-trips."""
    from py_vapid import Vapid

    private1, _ = get_or_create_vapid_keys()
    Vapid.from_string(private1)  # raises if the format is wrong


def test_send_web_push_success(isolated_paths, subscriptions, monkeypatch):
    sub = subscriptions.add_subscription("profile1", "https://push.example/ep1", "p256dh", "auth")
    mock_webpush = MagicMock(return_value="ok")
    monkeypatch.setattr(web_push_module, "webpush", mock_webpush)

    result = send_web_push(sub, "Title", "Message", subscriptions)

    assert result is True
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["subscription_info"] == sub.as_webpush_subscription_info()
    assert "Title" in call_kwargs["data"]
    assert subscriptions.all_subscriptions() == [sub]  # untouched on success


def test_send_web_push_removes_subscription_on_410_gone(isolated_paths, subscriptions, monkeypatch):
    sub = subscriptions.add_subscription("profile1", "https://push.example/ep1", "p256dh", "auth")
    fake_response = MagicMock(status_code=410)
    monkeypatch.setattr(
        web_push_module, "webpush",
        MagicMock(side_effect=WebPushException("gone", response=fake_response)),
    )

    result = send_web_push(sub, "Title", "Message", subscriptions)

    assert result is False
    assert subscriptions.all_subscriptions() == []


def test_send_web_push_keeps_subscription_on_other_failure_status(isolated_paths, subscriptions, monkeypatch):
    sub = subscriptions.add_subscription("profile1", "https://push.example/ep1", "p256dh", "auth")
    fake_response = MagicMock(status_code=500)
    monkeypatch.setattr(
        web_push_module, "webpush",
        MagicMock(side_effect=WebPushException("server error", response=fake_response)),
    )

    result = send_web_push(sub, "Title", "Message", subscriptions)

    assert result is False
    assert subscriptions.all_subscriptions() == [sub]


def test_send_web_push_malformed_subscription_keys_returns_false_without_removing(isolated_paths, subscriptions):
    """Regression test for a real bug caught in this feature's own
    manual end-to-end verification: pywebpush raises a bare
    binascii/ValueError (not WebPushException) when a subscription's
    p256dh/auth keys aren't valid base64 — this must degrade
    gracefully like every other send failure, not propagate as a 500."""
    sub = subscriptions.add_subscription("profile1", "https://push.example/ep1", "not-valid-base64!!!", "also-not-valid!!!")
    result = send_web_push(sub, "Title", "Message", subscriptions)
    assert result is False
    assert subscriptions.all_subscriptions() == [sub]


def test_send_web_push_unreachable_service_returns_false(isolated_paths, subscriptions, monkeypatch):
    sub = subscriptions.add_subscription("profile1", "https://push.example/ep1", "p256dh", "auth")
    monkeypatch.setattr(
        web_push_module, "webpush",
        MagicMock(side_effect=requests.exceptions.ConnectionError("network down")),
    )

    result = send_web_push(sub, "Title", "Message", subscriptions)

    assert result is False
    assert subscriptions.all_subscriptions() == [sub]  # not a "gone" signal, don't remove


# ----------------------------------------------------------------------
# Notification -> push relay (Mobile access, Phase 2)
# ----------------------------------------------------------------------

def _notification(title="MIA", message="Something happened") -> Notification:
    return Notification(notification_id="n1", title=title, message=message)


def test_relay_sends_to_every_registered_subscription(context, monkeypatch):
    context.push_subscriptions.add_subscription("profile1", "https://push.example/ep1", "k1", "a1")
    context.push_subscriptions.add_subscription("profile2", "https://push.example/ep2", "k2", "a2")
    mock_webpush = MagicMock(return_value="ok")
    monkeypatch.setattr(web_push_module, "webpush", mock_webpush)

    _relay_notification_to_all_subscriptions(context, _notification(title="Overdue", message="Mower inspection is overdue"))

    assert mock_webpush.call_count == 2
    sent_endpoints = {call.kwargs["subscription_info"]["endpoint"] for call in mock_webpush.call_args_list}
    assert sent_endpoints == {"https://push.example/ep1", "https://push.example/ep2"}
    assert all("Overdue" in call.kwargs["data"] for call in mock_webpush.call_args_list)


def test_relay_is_a_noop_with_no_subscriptions(context, monkeypatch):
    mock_webpush = MagicMock()
    monkeypatch.setattr(web_push_module, "webpush", mock_webpush)

    _relay_notification_to_all_subscriptions(context, _notification())

    mock_webpush.assert_not_called()


def test_relay_is_a_noop_when_push_subscriptions_unavailable(monkeypatch):
    ctx = AppContext(config=_FakeConfig(), events=EventBus())
    ctx.push_subscriptions = None  # e.g. server.enabled was never turned on
    mock_webpush = MagicMock()
    monkeypatch.setattr(web_push_module, "webpush", mock_webpush)

    _relay_notification_to_all_subscriptions(ctx, _notification())  # must not raise

    mock_webpush.assert_not_called()


def test_register_notification_relay_fires_on_a_real_notify_call(context, monkeypatch):
    """End-to-end through the real event: context.notifications.notify()
    -> "notification.created" -> the relay -> send_web_push(). Runs the
    background thread synchronously for the test (real threading would
    make this test racy) — the relay's own docstring covers why a
    background thread is used at all in production."""
    from core.notification_manager import NotificationManager

    context.notifications = NotificationManager(context)

    class _SynchronousThread:
        def __init__(self, target, args=(), daemon=None, name=None):
            self._target, self._args = target, args

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(web_push_module.threading, "Thread", _SynchronousThread)

    context.push_subscriptions.add_subscription("profile1", "https://push.example/ep1", "k1", "a1")
    mock_webpush = MagicMock(return_value="ok")
    monkeypatch.setattr(web_push_module, "webpush", mock_webpush)

    register_notification_relay(context)
    context.notifications.notify(title="Low Battery", message="12% remaining")

    mock_webpush.assert_called_once()
    assert "Low Battery" in mock_webpush.call_args.kwargs["data"]
