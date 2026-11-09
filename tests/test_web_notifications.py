"""Notifications on the web (core/web_notifications.py, DEC-0125): newest first, a tone for each level (amber for a
warning, red only for an error), why MIA sent the ones she sent on her own, Mark All Read and Dismiss as actions,
and the same by voice (core/assistant_notification_actions.py); and the reminders Waiting for the Internet, added
and taken off as actions (online.remind, online.forget)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.app_context import AppContext
from core.assistant_actions import AssistantActionRegistry
from core.assistant_notification_actions import register_notification_actions
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.notification_manager import NotificationManager
from core.web_notifications import notifications_page, tone_of


@pytest.fixture
def home(tmp_path):
    """A context with notifications in a temporary folder."""
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = NotificationManager(context, data_dir=tmp_path)
    return context


def run(context, kind, **params):
    """Checks then runs an action kind, as the screen's approve does."""
    action = ACTION_TYPES[kind]
    return action.describe(context, params), action.execute(context, params)


def test_tones_keep_their_meanings():
    assert (tone_of("warning"), tone_of("error"), tone_of("info"), tone_of("success")) == ("attention", "bad", "", "ok")


def test_notifications_are_listed_explained_read_and_dismissed(home):
    first = home.notifications.notify("Backup finished", "Saved.", source="system")
    blade = home.notifications.notify("The mower blade is due", "Tomorrow.", level="warning", source="maintenance")
    first.created_at, blade.created_at = "2026-11-07T10:00:00", "2026-11-07T17:02:00"
    home.communication = SimpleNamespace(entries_since=lambda since: [
        {"notification_id": blade.notification_id, "topic": "upkeep", "title": blade.title}])
    page = notifications_page(home)
    assert [i["title"] for i in page["items"]] == ["The mower blade is due", "Backup finished"] and page["unread"] == 2
    assert page["items"][0]["tone"] == "attention" and "because" in page["items"][0]["why"] and page["items"][1]["why"] == ""
    registry = AssistantActionRegistry()
    register_notification_actions(registry)
    said = registry._actions["list_notifications"].handler(home, {})
    assert said.startswith("2 new: The mower blade is due")
    assert run(home, "notification.read_all") == ("Mark 2 notifications read", "All read.")
    assert notifications_page(home)["unread"] == 0
    with pytest.raises(ActionError):
        run(home, "notification.read_all")
    assert registry._actions["mark_notifications_read"].handler(home, {}) == "Everything's already read."
    assert run(home, "notification.dismiss", notification_id=first.notification_id)[1] == "Dismissed “Backup finished”."
    assert [i["title"] for i in notifications_page(home)["items"]] == ["The mower blade is due"]


def test_reminders_waiting_for_the_internet_are_listed_added_and_taken_off(tmp_path):
    from types import SimpleNamespace

    from core.actions import ACTION_TYPES, ActionError
    from core.connectivity import OFFLINE
    from core.online_watch import OnlineReminders
    from core.web_notifications import waiting_for_internet

    ctx = SimpleNamespace(connectivity=SimpleNamespace(status=OFFLINE))
    ctx.online_reminders = OnlineReminders(ctx, data_dir=tmp_path)
    ACTION_TYPES["online.remind"].execute(ctx, {"what": "  sync the   bank "})
    ACTION_TYPES["online.remind"].execute(ctx, {"what": "upload the photos"})
    page = waiting_for_internet(ctx)
    assert page["state"] == "offline" and [r["what"] for r in page["items"]] == ["sync the bank", "upload the photos"]
    assert "upload the photos" in ACTION_TYPES["online.forget"].describe(ctx, {"index": 1})
    ACTION_TYPES["online.forget"].execute(ctx, {"index": 0})
    assert OnlineReminders(ctx, data_dir=tmp_path).pending() == ["upload the photos"]
    with pytest.raises(ActionError):
        ACTION_TYPES["online.forget"].describe(ctx, {"index": 5})
    with pytest.raises(ActionError):
        ACTION_TYPES["online.remind"].execute(ctx, {"what": " "})


def test_without_the_reminder_store_the_section_says_its_not_there():
    from types import SimpleNamespace

    from core.web_notifications import waiting_for_internet

    assert waiting_for_internet(SimpleNamespace()) == {"available": False, "state": "unknown", "items": []}
