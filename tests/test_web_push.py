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

import core.push_subscription_manager as push_subscription_manager_module
import core.web_push as web_push_module
from core.app_context import AppContext
from core.event_bus import EventBus
from core.push_subscription_manager import PushSubscriptionManager
from core.web_push import get_or_create_vapid_keys, send_web_push


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


@pytest.fixture
def subscriptions(isolated_paths) -> PushSubscriptionManager:
    context = AppContext(config=_FakeConfig(), events=EventBus())
    return PushSubscriptionManager(context)


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
