"""
Slice C, "Know when to speak" (core/communication_gate.py): every rule
with a fake clock, the persisted gate with delivery and deferral, the
daily checks routed through it, and a scripted day.
"""

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import core.communication_gate as gate_module
import core.config_manager as config_module
import core.conversation_manager as conversation_module
from core.app_context import AppContext
from core.communication_gate import (
    ACT, AMBIENT, DEFER, DROP, TIMELY, URGENT, Candidate, CommunicationGate, GateState, compose_digest, decide_batch,
)
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.event_bus import EventBus

SETTINGS = {"daily_budget": 5, "min_spacing_minutes": 90, "repeat_days": 7}
MORNING = datetime(2026, 9, 28, 7, 0)


def c(topic, urgency=AMBIENT, message=None, **kw):
    return Candidate(topic=topic, title=topic.title(), message=message or f"{topic} message", urgency=urgency, **kw)


def sent(at, candidate, urgency=None, digest_id=""):
    return {"at": at.isoformat(timespec="seconds"), "key": candidate.key(), "topic": candidate.topic,
            "urgency": urgency or candidate.urgency, "digest_id": digest_id}


# ------------------------------------------------------------------ pure rules


def test_single_candidate_goes_alone():
    [d] = decide_batch([c("tip")], MORNING, GateState(), SETTINGS)
    assert (d.action, d.delivered_as) == (ACT, "alone")


def test_a_batch_becomes_one_digest():
    decisions = decide_batch([c("calendar", TIMELY), c("budget", TIMELY), c("tip")], MORNING, GateState(), SETTINGS)
    assert {d.action for d in decisions} == {ACT} and {d.delivered_as for d in decisions} == {"digest"}


def test_repeat_within_window_is_dropped_then_allowed():
    tip = c("tip")
    state = GateState(sent=[sent(MORNING - timedelta(days=3), tip)])
    [d] = decide_batch([c("tip")], MORNING, state, SETTINGS)
    assert d.action == DROP and d.reason.startswith("nothing new since")
    state = GateState(sent=[sent(MORNING - timedelta(days=8), tip)])
    assert decide_batch([c("tip")], MORNING, state, SETTINGS)[0].action == ACT


def test_changed_facts_are_not_a_repeat():
    state = GateState(sent=[sent(MORNING - timedelta(days=1), c("budget", TIMELY, "Electric due in 3 days"))])
    [d] = decide_batch([c("budget", TIMELY, "Electric due in 2 days")], MORNING, state, SETTINGS)
    assert d.action == ACT


def test_daily_budget_defers_timely_and_drops_ambient():
    earlier = [sent(MORNING + timedelta(hours=h), c(f"x{h}")) for h in range(5)]
    now = MORNING + timedelta(hours=8)
    timely, ambient = decide_batch([c("calendar", TIMELY), c("tip")], now, GateState(sent=earlier), SETTINGS)
    assert timely.action == DEFER and timely.candidate.not_before == "2026-09-29T07:00:00"
    assert ambient.action == DROP and "limit is 5" in ambient.reason


def test_a_digest_counts_once_against_the_budget():
    digest = [sent(MORNING, c(f"d{i}"), digest_id="dg1") for i in range(4)]
    others = [sent(MORNING + timedelta(hours=h), c(f"x{h}")) for h in (2, 4, 6)]
    [d] = decide_batch([c("tip")], MORNING + timedelta(hours=8), GateState(sent=digest + others), SETTINGS)
    assert d.action == ACT  # 4 sends so far, not 7


def test_spacing_between_messages():
    state = GateState(sent=[sent(MORNING, c("first"))])
    timely, ambient = decide_batch([c("calendar", TIMELY), c("tip")], MORNING + timedelta(minutes=60), state, SETTINGS)
    assert timely.action == DEFER and timely.candidate.not_before == "2026-09-28T08:30:00"
    assert ambient.action == DROP
    assert decide_batch([c("tip")], MORNING + timedelta(minutes=91), state, SETTINGS)[0].action == ACT


def test_urgent_always_goes_out():
    earlier = [sent(MORNING + timedelta(minutes=m), c(f"x{m}")) for m in range(5)]
    state = GateState(sent=earlier, user_busy=True)
    [d] = decide_batch([c("bill due today", URGENT)], MORNING + timedelta(minutes=10), state, SETTINGS)
    assert (d.action, d.reason) == (ACT, "urgent")


def test_busy_user_is_not_interrupted():
    timely, ambient = decide_batch([c("calendar", TIMELY), c("tip")], MORNING, GateState(user_busy=True), SETTINGS)
    assert timely.action == DEFER and timely.candidate.not_before == "2026-09-28T07:30:00"
    assert ambient.action == DROP and "middle of a conversation" in ambient.reason


def test_no_quiet_hours():
    """Owner's choice: Do Not Disturb on the phone handles nights."""
    [d] = decide_batch([c("tip")], datetime(2026, 9, 28, 2, 30), GateState(), SETTINGS)
    assert d.action == ACT


def test_compose_digest():
    assert compose_digest([c("tip")]) == ("Tip", "tip message")
    title, message = compose_digest([c("calendar"), c("budget")])
    assert title == "MIA has 2 things for you" and "Calendar: calendar message" in message and "Budget: budget message" in message


# ------------------------------------------------------------------ the persisted gate


class FakeNotifications:
    def __init__(self):
        self.sent = []

    def notify(self, title, message, level="info", source="system"):
        self.sent.append((title, message))


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(gate_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(gate_module, "_LOG_FILE", tmp_path / "communication_log.json")
    monkeypatch.setattr(conversation_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(conversation_module, "_CONVERSATIONS_FILE", tmp_path / "conversations.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = FakeNotifications()
    context.conversations = ConversationManager(context)
    context.communication = CommunicationGate(context)
    context.tmp = tmp_path
    return context


def test_offer_batch_delivers_one_message_and_logs_each(ctx):
    ctx.communication.offer_batch([c("calendar", TIMELY), c("tip")], MORNING)
    assert len(ctx.notifications.sent) == 1 and ctx.notifications.sent[0][0] == "MIA has 2 things for you"
    log = json.loads((ctx.tmp / "communication_log.json").read_text())["log"]
    assert [e["action"] for e in log] == [ACT, ACT] and log[0]["digest_id"] == log[1]["digest_id"] != ""


def test_deferred_is_retried_when_due_and_expired_is_dropped(ctx):
    ctx.communication.offer_batch([c("first")], MORNING)
    ctx.communication.offer_batch([
        c("calendar", TIMELY, expires="2026-09-28T23:59:59"),
        c("mission", TIMELY),
    ], MORNING + timedelta(minutes=30))
    assert len(ctx.notifications.sent) == 1 and len(ctx.communication.pending()) == 2

    ctx.communication.offer_batch([], MORNING + timedelta(minutes=60))  # not due yet
    assert len(ctx.notifications.sent) == 1
    ctx.communication.offer_batch([], MORNING + timedelta(minutes=95))  # due: both go out together
    assert ctx.notifications.sent[-1][0] == "MIA has 2 things for you" and ctx.communication.pending() == []

    ctx.communication.offer_batch([c("late", TIMELY, expires="2026-09-28T23:59:59")], MORNING + timedelta(minutes=100))
    assert ctx.communication.pending()  # waiting for spacing...
    ctx.communication.offer_batch([], datetime(2026, 9, 29, 9, 0))  # ...but by tomorrow it's stale
    assert ctx.communication.pending() == []
    assert ctx.communication.entries_for_day("2026-09-29")[0]["reason"] == "waited too long; it's no longer current"


def test_settings_come_from_config_and_limit_is_clamped(ctx):
    assert ctx.communication.settings() == SETTINGS
    assert ctx.communication.set_daily_budget(50) == 20 and ctx.communication.set_daily_budget(0) == 1
    assert ctx.config.get("communication.daily_budget") == 1


def test_mid_vent_counts_as_busy(ctx):
    conversation = ctx.conversations.get_or_create_active_conversation()
    conversation.mode = "listen"
    conversation.updated_at = MORNING.isoformat(timespec="seconds")
    [d] = ctx.communication.offer(c("tip"), MORNING + timedelta(minutes=10))
    assert d.action == DROP
    [d] = ctx.communication.offer(c("tip2"), MORNING + timedelta(minutes=45))  # the vent went quiet
    assert d.action == ACT


def test_log_survives_a_restart(ctx):
    ctx.communication.offer(c("tip"), MORNING)
    again = CommunicationGate(ctx)
    [d] = again.offer(c("tip"), MORNING + timedelta(hours=3))
    assert d.action == DROP  # it remembered saying it


# ------------------------------------------------------------------ a scripted day


def test_scripted_day(ctx):
    """7:00 the daily checks; 7:40 MIA assigns a mission; 12:15 a vent;
    12:30 another tick with a nudge; 16:00 the evening tick."""
    decisions = {}

    def run(label, when, *candidates):
        decisions[label] = [(d.candidate.topic, d.action) for d in ctx.communication.offer_batch(list(candidates), when)]

    run("07:00", MORNING,
        c("calendar_digest", TIMELY, "You have 1 event(s) today: Dentist"),
        c("budget_nudge", TIMELY, "Electric is due in 2 days."),
        c("smart_suggestion", AMBIENT, "Sarah's birthday is in 7 days."))
    run("07:40", MORNING + timedelta(minutes=40), c("mission_auto_assigned", TIMELY, "Frame the coop"))

    conversation = ctx.conversations.get_or_create_active_conversation()
    conversation.journal = True
    conversation.updated_at = "2026-09-28T12:15:00"
    run("12:30", datetime(2026, 9, 28, 12, 30), c("maintenance_insight", TIMELY, "Mower oil change is overdue."),
        c("walkthrough_suggestion", AMBIENT, "Try the Music module."))
    run("16:00", datetime(2026, 9, 28, 16, 0), c("checkin", AMBIENT, "How's everything going?"))

    assert decisions["07:00"] == [("calendar_digest", ACT), ("budget_nudge", ACT), ("smart_suggestion", ACT)]
    assert decisions["07:40"] == [("mission_auto_assigned", DEFER)]  # 90-minute spacing
    assert decisions["12:30"] == [  # the mission was due (8:30) but the user is journaling
        ("mission_auto_assigned", DEFER), ("maintenance_insight", DEFER), ("walkthrough_suggestion", DROP),
    ]
    assert decisions["16:00"] == [("mission_auto_assigned", ACT), ("maintenance_insight", ACT), ("checkin", ACT)]
    assert len(ctx.notifications.sent) == 2  # two messages all day, holding six things


# ------------------------------------------------------------------ the daily checks go through it


def test_daily_checks_are_merged_into_one_message(ctx, monkeypatch):
    from core.application import MIAApplication

    app = MIAApplication.__new__(MIAApplication)
    app.context = ctx
    app.module_manager = None
    for name in ("_check_birthday", "_check_calendar_digest", "_check_checkin", "_check_budget_nudge",
                 "_check_smart_suggestion", "_check_maintenance_insight", "_check_mission_insight",
                 "_check_pattern_insight", "_check_skill_pattern_insight", "_check_skill_decline_insight",
                 "_check_skill_momentum_insight", "_check_recurring_missions", "_check_rewards",
                 "_check_walkthrough_suggestion"):
        monkeypatch.setattr(app, name, lambda now, today: None)
    monkeypatch.setattr(app, "_check_calendar_digest", lambda now, today: app._offer("calendar_digest", "Today's calendar", "Dentist", TIMELY, daily=True))
    monkeypatch.setattr(app, "_check_budget_nudge", lambda now, today: app._offer("budget_nudge", "Budget check-in", "Electric due", TIMELY, daily=True))
    app._check_daily_occasions()
    assert len(ctx.notifications.sent) == 1 and "Dentist" in ctx.notifications.sent[0][1]
    entry = ctx.communication.entries_for_day()[0]
    assert entry["topic"] == "calendar_digest"


def test_mission_auto_assignment_goes_through_the_gate(ctx):
    from core.mission_manager import MissionManager

    offered = []
    ctx.communication.offer = lambda candidate, now=None: offered.append(candidate) or []
    manager = MissionManager.__new__(MissionManager)
    manager.context = ctx
    manager._notify_mission_auto_assigned(SimpleNamespace(name="Frame the coop", mission_id="m1"))
    assert offered[0].topic == "mission_auto_assigned" and offered[0].fingerprint == "m1"
    assert ctx.notifications.sent == []


# ------------------------------------------------------------------ tools


def test_held_back_and_limit_tools(ctx):
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    say = lambda name, **a: registry.execute(ctx, name, a)  # noqa: E731
    assert "haven't had anything to say" in say("get_held_back_messages")
    now = datetime.now().replace(microsecond=0)
    ctx.communication.offer(c("first"), now)
    ctx.communication.offer_batch([c("calendar", TIMELY), c("tip")], now + timedelta(seconds=1))
    reply = say("get_held_back_messages")
    assert reply.startswith("Today I spoke up 1 time (your limit is 5).")
    assert "Still waiting to tell you: Calendar: calendar message." in reply and "I let these go: Tip (" in reply
    assert say("set_message_limit", count=3).startswith("Okay: at most 3 times a day")
    assert say("set_message_limit", direction="less").startswith("Okay: at most 2 times a day")
    assert "at most 2 times a day" in say("set_message_limit")
