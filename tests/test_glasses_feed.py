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
