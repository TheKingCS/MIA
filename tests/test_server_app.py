"""
tests.test_server_app
========================

Unit tests for server.app — exercised via FastAPI's TestClient, a real
in-process HTTP client that needs no running server, no real network,
and no HTTPS (see the Mobile Phase 1 plan's verification section for
why this is a legitimate, complete way to verify this code from a
sandbox with no real browser/phone). pywebpush.webpush is mocked in
the push-test cases, same as tests/test_web_push.py.

Builds a real AppContext via core.core_runtime.build_core_context(),
same fixture pattern as tests/test_core_runtime.py — proving
server.app.create_app() works against the actual object
core/application.py hands it, not a hand-rolled stand-in. Also wires
context.push_subscriptions directly (build_core_context() doesn't —
that's core/application.py's job, gated by server.enabled).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import core.alarm_manager as alarm_manager_module
import core.activity_log_manager as activity_log_manager_module
import core.calendar_manager as calendar_manager_module
import core.config_manager as config_manager_module
import core.expedition_manager as expedition_manager_module
import core.inventory_manager as inventory_manager_module
import core.journal_manager as journal_manager_module
import core.mission_manager as mission_manager_module
import core.notification_manager as notification_manager_module
import core.push_subscription_manager as push_subscription_manager_module
import core.trip_manager as trip_manager_module
import core.user_memory_manager as user_memory_manager_module
import core.waypoint_manager as waypoint_manager_module
import core.web_push as web_push_module
import server.app as server_app_module
from core.config_manager import ConfigManager
from core.core_runtime import build_core_context
from core.event_bus import EventBus
from core.push_subscription_manager import PushSubscriptionManager


@pytest.fixture
def context(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(notification_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(notification_manager_module, "_NOTIFICATIONS_FILE", data_dir / "notifications.json")
    monkeypatch.setattr(calendar_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(calendar_manager_module, "_EVENTS_FILE", data_dir / "calendar_events.json")
    monkeypatch.setattr(alarm_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(alarm_manager_module, "_ALARMS_FILE", data_dir / "alarms.json")
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", data_dir / "journal_entries.json")
    monkeypatch.setattr(inventory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(inventory_manager_module, "_ITEMS_FILE", data_dir / "inventory_items.json")
    monkeypatch.setattr(waypoint_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(waypoint_manager_module, "_WAYPOINTS_FILE", data_dir / "waypoints.json")
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", data_dir / "expeditions.json")
    monkeypatch.setattr(trip_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(trip_manager_module, "_TRIPS_FILE", data_dir / "trips.json")
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(user_memory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(user_memory_manager_module, "_USER_MEMORIES_FILE", data_dir / "user_memories.json")
    monkeypatch.setattr(activity_log_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(activity_log_manager_module, "_ACTIVITY_LOG_FILE", data_dir / "activity_log.json")
    monkeypatch.setattr(push_subscription_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(push_subscription_manager_module, "_SUBSCRIPTIONS_FILE", data_dir / "push_subscriptions.json")
    monkeypatch.setattr(web_push_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(web_push_module, "_VAPID_KEYS_FILE", data_dir / "vapid_keys.json")

    ctx = build_core_context(ConfigManager(), EventBus())
    ctx.push_subscriptions = PushSubscriptionManager(ctx)
    ctx.profiles.create_profile("Alice", password="hunter2")
    return ctx


@pytest.fixture
def client(context) -> TestClient:
    app = server_app_module.create_app(context)
    return TestClient(app)


def _profile_id(context) -> str:
    return context.profiles.list_profiles()[0].profile_id


# ----------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------

def test_login_succeeds_with_correct_password(client, context):
    res = client.post("/api/login", json={"profile_id": _profile_id(context), "password": "hunter2"})
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Alice"
    assert body["token"]


def test_login_succeeds_with_profile_name_case_insensitive(client, context):
    res = client.post("/api/login", json={"profile_id": "aLiCe", "password": "hunter2"})
    assert res.status_code == 200
    assert res.json()["name"] == "Alice"


def test_login_fails_with_wrong_password(client, context):
    res = client.post("/api/login", json={"profile_id": _profile_id(context), "password": "wrong"})
    assert res.status_code == 401


def test_login_fails_with_unknown_profile(client):
    res = client.post("/api/login", json={"profile_id": "nonexistent", "password": "x"})
    assert res.status_code == 401


# ----------------------------------------------------------------------
# VAPID public key
# ----------------------------------------------------------------------

def test_vapid_public_key_returns_a_real_key(client):
    res = client.get("/api/vapid-public-key")
    assert res.status_code == 200
    assert len(res.json()["public_key"]) > 0


# ----------------------------------------------------------------------
# Push subscribe
# ----------------------------------------------------------------------

def test_push_subscribe_requires_auth(client):
    res = client.post("/api/push/subscribe", json={"endpoint": "https://push.example/ep1", "keys": {"p256dh": "a", "auth": "b"}})
    assert res.status_code == 401


def _login(client, context, password="hunter2") -> str:
    res = client.post("/api/login", json={"profile_id": _profile_id(context), "password": password})
    return res.json()["token"]


def test_push_subscribe_persists_a_real_subscription(client, context):
    token = _login(client, context)
    res = client.post(
        "/api/push/subscribe",
        json={"endpoint": "https://push.example/ep1", "keys": {"p256dh": "p256dh-key", "auth": "auth-key"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    stored = context.push_subscriptions.subscriptions_for_profile(_profile_id(context))
    assert len(stored) == 1
    assert stored[0].endpoint == "https://push.example/ep1"
    assert stored[0].p256dh_key == "p256dh-key"


# ----------------------------------------------------------------------
# Push test-send
# ----------------------------------------------------------------------

def test_push_test_requires_auth(client):
    res = client.post("/api/push/test")
    assert res.status_code == 401


def test_push_test_404_with_no_subscriptions(client, context):
    token = _login(client, context)
    res = client.post("/api/push/test", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_push_test_sends_via_webpush_with_the_right_subscription(client, context, monkeypatch):
    token = _login(client, context)
    client.post(
        "/api/push/subscribe",
        json={"endpoint": "https://push.example/ep1", "keys": {"p256dh": "p256dh-key", "auth": "auth-key"}},
        headers={"Authorization": f"Bearer {token}"},
    )

    mock_webpush = MagicMock(return_value="ok")
    monkeypatch.setattr(web_push_module, "webpush", mock_webpush)

    res = client.post("/api/push/test", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    assert res.json() == {"sent": 1, "attempted": 1}
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["subscription_info"]["endpoint"] == "https://push.example/ep1"
    assert call_kwargs["subscription_info"]["keys"] == {"p256dh": "p256dh-key", "auth": "auth-key"}
