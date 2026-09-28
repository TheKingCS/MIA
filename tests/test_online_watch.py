"""
Offline awareness follow-ups (core/online_watch.py): noticing a settled
change of connection, telling the owner through the communication gate,
and "remind me when I'm back online".
"""

from types import SimpleNamespace

import pytest

import core.online_watch as online_module
from core.connectivity import OFFLINE, ONLINE, UNKNOWN
from core.online_watch import CAME_BACK, WENT_OFFLINE, OnlineReminders, OnlineWatch, remind_when_online_action


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(online_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(online_module, "_REMINDERS_FILE", tmp_path / "online_reminders.json")


def test_only_a_settled_change_is_news():
    watch = OnlineWatch()
    assert [watch.observe(s) for s in (ONLINE, ONLINE)] == [None, None]  # boot: not a change
    assert watch.observe(OFFLINE) is None  # one failed probe
    assert watch.observe(ONLINE) is None  # ...was a blip
    assert watch.observe(UNKNOWN) is None
    assert [watch.observe(OFFLINE), watch.observe(OFFLINE)] == [None, WENT_OFFLINE]
    assert watch.observe(OFFLINE) is None  # said once
    assert [watch.observe(ONLINE), watch.observe(ONLINE)] == [None, CAME_BACK]


def test_reminders_are_kept_until_delivered(tmp_path):
    ctx = SimpleNamespace(connectivity=SimpleNamespace(status=OFFLINE))
    ctx.online_reminders = OnlineReminders(ctx)
    action = remind_when_online_action()
    assert action.handler(ctx, {"what": "sync the bank accounts"}) == (
        "Okay, I'll remind you as soon as the internet is back: sync the bank accounts.")
    assert OnlineReminders(ctx).pending() == ["sync the bank accounts"]  # survives a restart
    assert ctx.online_reminders.take_all() == ["sync the bank accounts"]
    assert OnlineReminders(ctx).pending() == []
    ctx.connectivity.status = ONLINE
    assert "online right now" in action.handler(ctx, {"what": "send the photo"})


def test_the_app_tells_the_owner_and_delivers_reminders():
    from core.application import MIAApplication

    offered, notified = [], []
    monitor = SimpleNamespace(status=ONLINE)
    ctx = SimpleNamespace(
        connectivity=monitor, notifications=SimpleNamespace(notify=lambda title, message: notified.append(message)),
        communication=SimpleNamespace(offer=offered.append), online_reminders=None,
    )
    ctx.online_reminders = OnlineReminders(ctx)
    app = SimpleNamespace(context=ctx, _online_watch=OnlineWatch())
    check = lambda: MIAApplication._check_online(app)  # noqa: E731
    check(); check()  # settled online at boot: nothing to say
    monitor.status = OFFLINE
    check(); check()
    [went] = offered
    assert went.title.endswith("Offline") and went.urgency == "timely" and went.fingerprint.startswith("went_offline-")
    ctx.online_reminders.add("sync the bank accounts")
    monitor.status = ONLINE
    check(); check()
    assert offered[-1].title.endswith("Back online") and offered[-1].urgency == "ambient"
    assert notified == ["You asked me to remind you: sync the bank accounts"]
    assert ctx.online_reminders.pending() == []
