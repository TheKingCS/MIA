"""
Q-0002 (approved 2026-10-05, H-0011): when a child triggers the safety
floor, the child gets the safety reply and is told plainly that a parent
will be told; each guardian gets a minimal, direct alert (who and when,
never what was written); it's recorded for audit in the child's and the
guardians' own histories; and alerts don't flood. Plus Q-0001: a missed
daily is recorded gently, with no points lost.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from core import safety_escalation
from core.child_accounts import make_child
from core.conversation_manager import ConversationManager
from core.gamification import SkillWeight
from core.life_events import LifeEventLog, PersonalLifeEventLog, events_for
from core.safety_floor import safety_reply
from core.safety_escalation import CHILD_NOTICE, alert_text, escalate
from core.talk_it_out import pre_turn
from tests.engine_world import build_world

DANGER = "I want to kill myself"


class _Inbox:
    """A guardian's notifications, as the real NotificationManager is called."""

    def __init__(self):
        self.sent = []

    def notify(self, title, message, level="info", source="system", always=False):
        self.sent.append((title, message, level, source, always))
        return object()


@pytest.fixture
def family(tmp_path, monkeypatch):
    monkeypatch.setattr(safety_escalation, "_last_alert", {})
    world = build_world(tmp_path, monkeypatch)
    kid = world.profiles.create_profile("Ari", make_active=False)
    make_child(world, kid.profile_id, [world.me.profile_id, world.other.profile_id])
    inboxes = {world.me.profile_id: _Inbox(), world.other.profile_id: _Inbox()}
    world.personal_data = SimpleNamespace(
        folder=lambda pid: tmp_path / "profiles" / pid,
        view=lambda pid: SimpleNamespace(notifications=inboxes.get(pid)),
    )
    world.kid, world.inboxes = kid, inboxes
    return world


def test_the_child_is_told_plainly():
    reply = safety_reply(child=True)
    assert CHILD_NOTICE in reply and "won't see what you wrote" in reply
    assert CHILD_NOTICE not in safety_reply()


def test_the_alert_says_who_and_when_and_nothing_more():
    title, message = alert_text("Ari", datetime(2026, 10, 5, 21, 7))
    assert title == "Safety alert"
    assert message.startswith("Ari was shown MIA's safety support message at 9:07 PM on Oct 5.")
    assert "doesn't share what they wrote" in message


def test_both_guardians_alerted_directly_and_it_is_recorded(family, tmp_path):
    assert escalate(family, family.kid.profile_id) == 2
    for inbox in family.inboxes.values():
        [(title, message, level, source, always)] = inbox.sent
        assert (title, level, source, always) == ("Safety alert", "critical", "safety", True)
        assert DANGER not in message
    child_log = PersonalLifeEventLog(family, tmp_path / "profiles" / family.kid.profile_id)
    assert [e.type for e in child_log.all_events()] == ["safety_escalation"]
    guardian_log = PersonalLifeEventLog(family, tmp_path / "profiles" / family.me.profile_id)
    assert [e.type for e in guardian_log.all_events()] == ["safety_escalation"]
    assert family.life_events.all_events() == []  # never in the shared household history


def test_no_flood_but_every_trigger_is_recorded(family, tmp_path):
    assert escalate(family, family.kid.profile_id) == 2
    assert escalate(family, family.kid.profile_id) == 0  # within 30 minutes
    child_log = PersonalLifeEventLog(family, tmp_path / "profiles" / family.kid.profile_id)
    assert len(child_log.all_events()) == 2


def test_a_childs_danger_message_escalates_through_the_real_turn(family, tmp_path):
    family.profiles.set_active_profile(family.kid.profile_id)
    family.conversations = ConversationManager(family, data_dir=tmp_path / "convo")
    conversation = family.conversations.create_conversation()
    result = pre_turn(family, conversation, DANGER)
    assert CHILD_NOTICE in result.fixed_reply
    assert all(len(inbox.sent) == 1 for inbox in family.inboxes.values())


def test_an_adults_danger_message_does_not_alert_anyone(family, tmp_path):
    family.profiles.set_active_profile(family.other.profile_id)
    family.conversations = ConversationManager(family, data_dir=tmp_path / "convo")
    result = pre_turn(family, family.conversations.create_conversation(), DANGER)
    assert result.fixed_reply and CHILD_NOTICE not in result.fixed_reply
    assert all(inbox.sent == [] for inbox in family.inboxes.values())


def test_escalation_never_breaks_the_reply(family):
    family.personal_data = None  # no way to notify on this MIA
    assert escalate(family, family.kid.profile_id) == 0
    assert escalate(family, None) == 0


def test_safety_alerts_stay_out_of_feeds(family):
    from core.context_assembler import assemble_life_state_v2
    from core.life_events import describe

    family.profiles.set_active_profile(family.me.profile_id)
    escalate(family, family.kid.profile_id)
    events = events_for(family)
    assert any(e.type == "safety_escalation" for e in events)
    assert "safety" not in describe(events).lower()
    latest = assemble_life_state_v2(family)["recent_wins"]["latest"]
    assert not any(e["type"] == "safety_escalation" for e in latest)


def test_a_missed_daily_is_recorded_gently(tmp_path, monkeypatch):
    """Q-0001: the streak starts again, nothing is lost, the miss is recorded once."""
    world = build_world(tmp_path, monkeypatch)
    today = date.today()
    template = world.recurring_missions.add_template(
        "Walk", "Walk for {target:g} minutes", 15, 0, 10, 25, (today - timedelta(days=3)).isoformat(),
        daily_skill_rewards=[SkillWeight("endurance", 5)])
    world.recurring_missions.ensure_current_missions(template, today - timedelta(days=1))  # yesterday, not done
    xp_before = world.profiles.get_profile(world.me.profile_id).total_xp
    world.recurring_missions.ensure_current_missions(template, today)
    world.recurring_missions.ensure_current_missions(template, today)  # idempotent: no second record
    device_log = LifeEventLog(world, world.device_dir)
    missed = [e for e in device_log.all_events() if e.type == "mission_missed"]
    assert len(missed) == 1 and "no points lost" in missed[0].summary
    assert world.profiles.get_profile(world.me.profile_id).total_xp == xp_before
