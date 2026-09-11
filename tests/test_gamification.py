"""
tests.test_gamification
==========================

Unit tests for core.gamification.grant_xp() — the shared "credit XP/
credits + raise a real notification" helper every routine-completion
hook (Workout/Kitchen/Maintenance/Budget) calls through. No Qt needed;
fakes stand in for context.profiles/context.notifications/context.skills,
same shape as tests/test_assistant_chat.py's own _FakeProfiles precedent.
"""

from __future__ import annotations

from core.gamification import SkillWeight, grant_xp


class _FakeProfile:
    def __init__(self, profile_id="p1"):
        self.profile_id = profile_id


class _FakeProfiles:
    def __init__(self, active=None):
        self._active = active
        self.xp_calls: list[tuple[str, int]] = []
        self.credit_calls: list[tuple[str, int]] = []

    def get_active_profile(self):
        return self._active

    def add_xp(self, profile_id, amount):
        self.xp_calls.append((profile_id, amount))
        return amount

    def add_credits(self, profile_id, amount):
        self.credit_calls.append((profile_id, amount))
        return amount


class _FakeNotifications:
    def __init__(self):
        self.calls: list[dict] = []

    def notify(self, title, message, level="info", source="system"):
        self.calls.append({"title": title, "message": message, "level": level, "source": source})


class _FakeSkills:
    def __init__(self):
        self.calls: list[tuple[str, str, int]] = []

    def add_skill_xp(self, profile_id, skill_id, amount):
        self.calls.append((profile_id, skill_id, amount))
        return amount


class _FakeContext:
    """A plain stand-in, not the real AppContext — grant_xp() only ever
    touches .profiles/.notifications/.skills, same "fake just what's
    used" precedent tests/test_assistant_chat.py's own _FakeContext
    already establishes, rather than constructing a real AppContext
    with None for its actually-required config/events fields."""

    def __init__(self, profiles=None, notifications=None, skills=None):
        self.profiles = profiles
        self.notifications = notifications
        self.skills = skills


def _make_context(profiles=None, notifications=None, skills=None) -> _FakeContext:
    return _FakeContext(profiles=profiles, notifications=notifications, skills=skills)


def test_grant_xp_credits_the_active_profile():
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    context = _make_context(profiles=profiles, notifications=_FakeNotifications())

    grant_xp(context, 10, "Title", "Message")

    assert profiles.xp_calls == [("p1", 10)]
    assert profiles.credit_calls == []


def test_grant_xp_credits_optional_credits_too():
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    context = _make_context(profiles=profiles, notifications=_FakeNotifications())

    grant_xp(context, 10, "Title", "Message", credits=25)

    assert profiles.xp_calls == [("p1", 10)]
    assert profiles.credit_calls == [("p1", 25)]


def test_grant_xp_sends_a_notification_with_the_right_source():
    notifications = _FakeNotifications()
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    context = _make_context(profiles=profiles, notifications=notifications)

    grant_xp(context, 10, "\U0001F4AA Workout logged!", "Nice work.")

    assert len(notifications.calls) == 1
    call = notifications.calls[0]
    assert call["title"] == "\U0001F4AA Workout logged!"
    assert call["message"] == "Nice work."
    assert call["level"] == "info"
    assert call["source"] == "gamification"


def test_grant_xp_no_active_profile_does_not_raise():
    profiles = _FakeProfiles(active=None)
    notifications = _FakeNotifications()
    context = _make_context(profiles=profiles, notifications=notifications)

    grant_xp(context, 10, "Title", "Message")

    assert profiles.xp_calls == []
    # Still notifies — a real event happened even if no one's logged in to credit.
    assert len(notifications.calls) == 1


def test_grant_xp_no_profiles_service_does_not_raise():
    context = _make_context(profiles=None, notifications=_FakeNotifications())
    grant_xp(context, 10, "Title", "Message")  # must not raise


def test_grant_xp_no_notifications_service_does_not_raise():
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    context = _make_context(profiles=profiles, notifications=None)

    grant_xp(context, 10, "Title", "Message")  # must not raise

    assert profiles.xp_calls == [("p1", 10)]


def test_grant_xp_zero_amount_does_not_call_add_xp():
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    context = _make_context(profiles=profiles, notifications=_FakeNotifications())

    grant_xp(context, 0, "Title", "Message")

    assert profiles.xp_calls == []


# ------------------------------------------------------------------
# skill_weights — "My Hero's Path" (2026-09-11)
# ------------------------------------------------------------------

def test_grant_xp_credits_each_skill_weight():
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    skills = _FakeSkills()
    context = _make_context(profiles=profiles, notifications=_FakeNotifications(), skills=skills)

    grant_xp(
        context,
        10,
        "Title",
        "Message",
        skill_weights=[SkillWeight("strength", 10), SkillWeight("endurance", 4)],
    )

    assert skills.calls == [("p1", "strength", 10), ("p1", "endurance", 4)]


def test_grant_xp_skill_weights_none_calls_no_skill_xp():
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    skills = _FakeSkills()
    context = _make_context(profiles=profiles, notifications=_FakeNotifications(), skills=skills)

    grant_xp(context, 10, "Title", "Message")

    assert skills.calls == []


def test_grant_xp_skill_weights_no_skills_service_does_not_raise():
    profiles = _FakeProfiles(active=_FakeProfile("p1"))
    context = _make_context(profiles=profiles, notifications=_FakeNotifications(), skills=None)

    grant_xp(context, 10, "Title", "Message", skill_weights=[SkillWeight("strength", 10)])  # must not raise

    assert profiles.xp_calls == [("p1", 10)]


def test_grant_xp_skill_weights_no_active_profile_does_not_raise():
    profiles = _FakeProfiles(active=None)
    skills = _FakeSkills()
    context = _make_context(profiles=profiles, notifications=_FakeNotifications(), skills=skills)

    grant_xp(context, 10, "Title", "Message", skill_weights=[SkillWeight("strength", 10)])  # must not raise

    assert skills.calls == []
