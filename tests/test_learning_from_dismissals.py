"""
Learning from being ignored (core/communication_gate.py): closing MIA's
messages of one kind with their X pauses that kind for a while; urgent
ones never pause; the owner can bring a kind back.
"""

from datetime import datetime, timedelta

import pytest

import core.communication_gate as gate_module
import core.config_manager as config_module
import core.notification_manager as notification_module
from core.app_context import AppContext
from core.assistant_comm_actions import _action_get_held_back_messages, _action_resume_message_topic
from core.communication_gate import ACT, DROP, TIMELY, URGENT, Candidate, CommunicationGate, paused_topics
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.notification_manager import NotificationManager

DAY1 = datetime(2026, 9, 21, 9, 0)


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(gate_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(gate_module, "_LOG_FILE", tmp_path / "communication_log.json")
    monkeypatch.setattr(notification_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(notification_module, "_NOTIFICATIONS_FILE", tmp_path / "notifications.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = NotificationManager(context)
    context.communication = CommunicationGate(context)
    return context


def budget_nudge(day):
    return Candidate(topic="budget_nudge", title="Budget check-in", message=f"Day {day}: groceries at 80%.",
                     urgency=TIMELY, fingerprint=f"budget-{day}")


def send_and_dismiss(ctx, days, dismiss=True):
    for day in days:
        now = DAY1 + timedelta(days=day)
        ctx.communication.clock = lambda now=now: now + timedelta(hours=1)  # dismissed an hour later
        ctx.communication.offer(budget_nudge(day), now)
        if dismiss:
            newest = ctx.notifications.list_all()[0]
            ctx.notifications.dismiss(newest.notification_id)


def test_three_dismissals_pause_that_kind(ctx):
    send_and_dismiss(ctx, [0, 1])
    assert ctx.communication.paused(DAY1 + timedelta(days=2)) == []  # two isn't a pattern
    send_and_dismiss(ctx, [2])
    [pause] = ctx.communication.paused(DAY1 + timedelta(days=3))
    assert pause["topic"] == "budget_nudge" and pause["label"] == "Budget check-in"
    [decision] = ctx.communication.offer(budget_nudge(3), DAY1 + timedelta(days=3))
    assert decision.action == DROP and "taking a break" in decision.reason
    # Other kinds, and urgent ones, still go out.
    other = Candidate(topic="calendar_digest", title="Today", message="2 events", urgency=TIMELY)
    assert ctx.communication.offer(other, DAY1 + timedelta(days=3, hours=2))[0].action == ACT
    urgent = Candidate(topic="budget_nudge", title="Bill due today", message="Electric $120", urgency=URGENT)
    assert ctx.communication.offer(urgent, DAY1 + timedelta(days=3, hours=4))[0].action == ACT


def test_the_break_ends_on_its_own(ctx):
    send_and_dismiss(ctx, [0, 1, 2])
    assert ctx.communication.paused(DAY1 + timedelta(days=17)) == []


def test_messages_left_alone_dont_count(ctx):
    send_and_dismiss(ctx, [0, 1])
    send_and_dismiss(ctx, [2, 3], dismiss=False)
    assert ctx.communication.paused(DAY1 + timedelta(days=4)) == []  # 2 of the last 4


def test_clear_all_and_late_dismissals_dont_count(ctx):
    send_and_dismiss(ctx, [0, 1, 2], dismiss=False)
    ctx.notifications.clear_all()
    assert ctx.communication.paused(DAY1 + timedelta(days=3)) == []
    log = [{"at": (DAY1 + timedelta(days=d)).isoformat(), "topic": "tip", "action": ACT, "urgency": "ambient",
            "dismissed_at": (DAY1 + timedelta(days=d + 5)).isoformat()} for d in range(3)]
    assert paused_topics(log, DAY1 + timedelta(days=9)) == {}  # closed days later: not a reaction


def test_bringing_a_kind_back(ctx, monkeypatch):
    send_and_dismiss(ctx, [0, 1, 2])
    real_now = DAY1 + timedelta(days=3)
    ctx.communication.clock = lambda: real_now
    held = _action_get_held_back_messages(ctx, {})
    assert "taking a break from them: Budget check-in until Oct 07" in held
    assert _action_resume_message_topic(ctx, {"topic": "the budget check-ins"}) == "Okay, I'll tell you about Budget check-in again."
    assert ctx.communication.paused(real_now) == []
    assert _action_resume_message_topic(ctx, {}) == "I'm not taking a break from anything right now."
    assert CommunicationGate(ctx).paused(real_now) == []  # persisted
