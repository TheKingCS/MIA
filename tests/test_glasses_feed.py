"""
The glasses' Heads-Up screen (Zac, 2026-10-18): new notifications and
wins since the cursor, each once; the same moment shown once; money never
to a child.
"""

from datetime import datetime, timedelta

from core.glasses_feed import _split_title, feed
from tests.engine_world import build_world


def _world(tmp_path, monkeypatch):
    from core.notification_manager import NotificationManager

    world = build_world(tmp_path, monkeypatch)
    world.notifications = NotificationManager(world, data_dir=world.my_dir)
    return world


def test_split_title():
    assert _split_title("🎉 Mission complete!") == ("🎉", "Mission Complete")
    assert _split_title("Budget check-in") == ("✦", "Budget Check-in")


def test_cursor_then_new_cards(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    first = feed(world)
    assert first["items"] == [] and first["now"]
    since = (datetime.now() - timedelta(seconds=30)).isoformat(timespec="seconds")
    m = world.missions.add_mission("Fix the fence", reward_xp=40)
    world.missions.update_mission(m.mission_id, status="completed")
    debt = world.budget.add_debt("Car loan", 5000, 6.0, minimum_payment=300)
    from core import life_events

    life_events.record(world.budget, "debt_payment", "Paid $300.00 on Car loan", [f"debt:{debt.debt_id}"], {})
    got = feed(world, since, now=datetime.now() + timedelta(seconds=1))
    heads = [c["headline"] for c in got["items"]]
    assert "Mission Complete" in heads and "Debt Payment" in heads
    assert heads.count("Mission Complete") == 1  # the notification and the history: the same moment, once
    later = feed(world, got["now"], now=datetime.now() + timedelta(seconds=2))
    assert later["items"] == []  # each card once


def test_old_things_are_not_replayed(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    world.notifications.notify("🎉 Mission complete!", "Old news")
    cursor = feed(world, now=datetime.now() + timedelta(seconds=5))["now"]
    assert feed(world, cursor, now=datetime.now() + timedelta(seconds=6))["items"] == []


def test_orb_follows_and_runs_out():
    from core.glasses_feed import orb, set_orb

    now = datetime(2026, 10, 30, 9, 0, 0)
    assert orb("orb-nobody", now) == {"state": "idle"}
    assert set_orb("orb-a", "listening", now) == {"state": "listening"}
    assert orb("orb-a", now + timedelta(seconds=5)) == {"state": "listening"}
    assert orb("orb-b", now) == {"state": "idle"}  # one person's orb, not everyone's
    assert orb("orb-a", now + timedelta(seconds=31)) == {"state": "idle"}  # never stuck
    assert set_orb("orb-a", "thinking", now) and orb("orb-a", now + timedelta(seconds=60)) == {"state": "thinking"}
    assert set_orb("orb-a", "idle", now) and orb("orb-a", now) == {"state": "idle"}
    assert set_orb("orb-a", "dancing", now) is None


def test_orb_and_log_routes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world = _world(tmp_path, monkeypatch)
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.get("/api/glasses/orb").json() == {"state": "idle"}
    assert client.post("/api/glasses/orb", json={"state": "thinking"}).json() == {"state": "thinking"}
    assert client.get("/api/glasses/orb").json() == {"state": "thinking"}
    assert client.post("/api/glasses/orb", json={"state": "dancing"}).status_code == 400
    assert client.post("/api/glasses/orb", json={"state": "idle"}).status_code == 200
    assert client.get("/api/glasses/orb", headers={"Authorization": ""}).status_code == 401
    assert client.get("/api/talk/thread?limit=200").json()["messages"] == []
