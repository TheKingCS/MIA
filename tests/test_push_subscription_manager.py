"""
tests.test_push_subscription_manager
=======================================

Unit tests for core.push_subscription_manager — same isolation pattern
as tests/test_notification_manager.py (monkeypatch _DATA_DIR/_*_FILE
into tmp_path, a minimal fake config since these tests never touch it).
"""

from __future__ import annotations

import pytest

import core.push_subscription_manager as push_subscription_manager_module
from core.app_context import AppContext
from core.event_bus import EventBus
from core.push_subscription_manager import PushSubscriptionManager


class _FakeConfig:
    def get(self, key: str, default=None):
        return default


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(push_subscription_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(push_subscription_manager_module, "_SUBSCRIPTIONS_FILE", data_dir / "push_subscriptions.json")


def _make_context() -> AppContext:
    context = AppContext(config=_FakeConfig(), events=EventBus())
    context.push_subscriptions = PushSubscriptionManager(context)
    return context


def test_add_subscription_persists_and_returns_it(isolated_paths):
    context = _make_context()
    sub = context.push_subscriptions.add_subscription("profile1", "https://push.example/ep1", "p256dh1", "auth1")
    assert sub.profile_id == "profile1"
    assert sub.endpoint == "https://push.example/ep1"
    assert sub.created_at

    reloaded = PushSubscriptionManager(context)
    assert len(reloaded.all_subscriptions()) == 1
    assert reloaded.all_subscriptions()[0].endpoint == "https://push.example/ep1"


def test_add_subscription_replaces_existing_same_endpoint(isolated_paths):
    context = _make_context()
    context.push_subscriptions.add_subscription("profile1", "https://push.example/ep1", "old_key", "old_auth")
    context.push_subscriptions.add_subscription("profile1", "https://push.example/ep1", "new_key", "new_auth")
    subs = context.push_subscriptions.all_subscriptions()
    assert len(subs) == 1
    assert subs[0].p256dh_key == "new_key"


def test_subscriptions_for_profile_filters_by_profile(isolated_paths):
    context = _make_context()
    context.push_subscriptions.add_subscription("profile1", "https://push.example/ep1", "k1", "a1")
    context.push_subscriptions.add_subscription("profile2", "https://push.example/ep2", "k2", "a2")
    subs = context.push_subscriptions.subscriptions_for_profile("profile1")
    assert len(subs) == 1
    assert subs[0].endpoint == "https://push.example/ep1"


def test_remove_subscription_deletes_matching_endpoint(isolated_paths):
    context = _make_context()
    context.push_subscriptions.add_subscription("profile1", "https://push.example/ep1", "k1", "a1")
    context.push_subscriptions.remove_subscription("https://push.example/ep1")
    assert context.push_subscriptions.all_subscriptions() == []


def test_all_subscriptions_empty_by_default(isolated_paths):
    context = _make_context()
    assert context.push_subscriptions.all_subscriptions() == []
