"""
tests.test_profile_manager
=============================

Unit tests for the birthday field added to core.profile_manager.Profile
(2026-07-14 aesthetic pass part 5) — not a full ProfileManager test
suite (none existed before this addition; out of scope to backfill
here). Isolates config_manager's _CONFIG_FILE into a tmp_path scratch
area, same "config.save() is a real write too" lesson milestone 5.14
already learned elsewhere in this project.
"""

from __future__ import annotations

import pytest

import core.config_manager as config_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.leveling import XP_PER_PRESTIGE_CYCLE
from core.profile_manager import ProfileManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")


def _make_manager() -> ProfileManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ProfileManager(context)


class _FakeNotifications:
    """Same "fake just what's used" shape as
    tests/test_gamification.py's own _FakeNotifications — records
    every notify() call so achievement-firing tests can assert on
    title/message/source without a real NotificationManager."""

    def __init__(self):
        self.calls: list[dict] = []

    def notify(self, title, message, level="info", source="system"):
        self.calls.append({"title": title, "message": message, "level": level, "source": source})


def test_new_profile_has_no_birthday_by_default(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert profile.birthday is None


def test_set_birthday(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert manager.set_birthday(profile.profile_id, "1990-03-03") is True

    reloaded = manager.list_profiles()[0]
    assert reloaded.birthday == "1990-03-03"


def test_set_birthday_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.set_birthday(profile.profile_id, "1990-03-03")

    reloaded_manager = _make_manager()
    assert reloaded_manager.list_profiles()[0].birthday == "1990-03-03"


def test_set_birthday_unknown_profile_returns_false(isolated_paths):
    manager = _make_manager()
    assert manager.set_birthday("does-not-exist", "1990-03-03") is False


def test_get_active_profile_includes_birthday(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex", make_active=True)
    manager.set_birthday(profile.profile_id, "1990-03-03")

    active = manager.get_active_profile()
    assert active.birthday == "1990-03-03"


def test_add_xp_accumulates(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert manager.add_xp(profile.profile_id, 100) == 100
    assert manager.add_xp(profile.profile_id, 50) == 150

    reloaded = manager.list_profiles()[0]
    assert reloaded.total_xp == 150


def test_add_xp_unknown_profile_returns_none(isolated_paths):
    manager = _make_manager()
    assert manager.add_xp("does-not-exist", 100) is None


def test_add_credits_accumulates(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert manager.add_credits(profile.profile_id, 25) == 25
    assert manager.add_credits(profile.profile_id, 25) == 50

    reloaded = manager.list_profiles()[0]
    assert reloaded.total_credits == 50


def test_add_credits_unknown_profile_returns_none(isolated_paths):
    manager = _make_manager()
    assert manager.add_credits("does-not-exist", 25) is None


def test_add_xp_publishes_profile_xp_changed(isolated_paths):
    """2026-09-11 gamification pass — a real, previously-missing event,
    added so any UI showing Level/XP outside the Missions module (e.g.
    gui/main_window.py's header badge) can refresh live."""
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    received = []
    manager.context.events.subscribe("profile.xp_changed", lambda **kwargs: received.append(kwargs))

    manager.add_xp(profile.profile_id, 100)

    assert received == [{"profile_id": profile.profile_id}]


def test_add_credits_publishes_profile_xp_changed(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    received = []
    manager.context.events.subscribe("profile.xp_changed", lambda **kwargs: received.append(kwargs))

    manager.add_credits(profile.profile_id, 25)

    assert received == [{"profile_id": profile.profile_id}]


def test_add_xp_unknown_profile_does_not_publish(isolated_paths):
    manager = _make_manager()
    received = []
    manager.context.events.subscribe("profile.xp_changed", lambda **kwargs: received.append(kwargs))

    manager.add_xp("does-not-exist", 100)

    assert received == []


def test_new_profile_starts_with_zero_xp_and_credits(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert profile.total_xp == 0
    assert profile.total_credits == 0


# ------------------------------------------------------------------
# rename_profile (2026-09-10, Settings' "Rename Profile" button)
# ------------------------------------------------------------------

def test_rename_profile_updates_name(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert manager.rename_profile(profile.profile_id, "Alexandra") is True

    reloaded = manager.list_profiles()[0]
    assert reloaded.name == "Alexandra"


def test_rename_profile_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.rename_profile(profile.profile_id, "Alexandra")

    reloaded_manager = _make_manager()
    assert reloaded_manager.list_profiles()[0].name == "Alexandra"


def test_rename_profile_strips_whitespace(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.rename_profile(profile.profile_id, "  Alexandra  ")
    assert manager.list_profiles()[0].name == "Alexandra"


def test_rename_profile_rejects_blank_name(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert manager.rename_profile(profile.profile_id, "   ") is False
    assert manager.list_profiles()[0].name == "Alex"


def test_rename_profile_unknown_profile_returns_false(isolated_paths):
    manager = _make_manager()
    assert manager.rename_profile("does-not-exist", "Alexandra") is False


def test_rename_profile_publishes_event(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")

    received = {}
    manager.context.events.subscribe(
        "profile.renamed",
        lambda profile_id, old_name, new_name: received.update(
            profile_id=profile_id, old_name=old_name, new_name=new_name
        ),
    )
    manager.rename_profile(profile.profile_id, "Alexandra")

    assert received == {"profile_id": profile.profile_id, "old_name": "Alex", "new_name": "Alexandra"}


def test_rename_profile_preserves_other_fields(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex", password="hunter2")
    manager.set_birthday(profile.profile_id, "1990-03-03")
    manager.add_xp(profile.profile_id, 100)

    manager.rename_profile(profile.profile_id, "Alexandra")

    reloaded = manager.list_profiles()[0]
    assert reloaded.name == "Alexandra"
    assert reloaded.has_password is True
    assert reloaded.birthday == "1990-03-03"
    assert reloaded.total_xp == 100


# ------------------------------------------------------------------
# Achievements/Milestones (2026-09-11) — profile level-up notification
# ------------------------------------------------------------------

def test_add_xp_fires_level_up_notification(isolated_paths):
    manager = _make_manager()
    manager.context.notifications = _FakeNotifications()
    profile = manager.create_profile(name="Alex")

    # Level 1 needs 100 XP -- 130 crosses into level 2.
    manager.add_xp(profile.profile_id, 130)

    level_up_calls = [c for c in manager.context.notifications.calls if c["source"] == "achievements"]
    assert len(level_up_calls) == 1
    assert level_up_calls[0]["title"] == "\U00002B50 Level up!"
    assert level_up_calls[0]["message"] == "You reached Level 2!"


def test_add_xp_does_not_fire_level_up_when_staying_in_the_same_level(isolated_paths):
    manager = _make_manager()
    manager.context.notifications = _FakeNotifications()
    profile = manager.create_profile(name="Alex")

    manager.add_xp(profile.profile_id, 50)  # well under the 100 XP needed for level 2

    assert manager.context.notifications.calls == []


def test_add_xp_with_no_notifications_service_does_not_crash(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, 500)  # must not raise, context.notifications is None


# ------------------------------------------------------------------
# Prestige (2026-09-14)
# ------------------------------------------------------------------

def test_new_profile_has_prestige_tier_zero_by_default(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    assert profile.prestige_tier == 0


def test_prestige_succeeds_when_eligible(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)

    assert manager.prestige(profile.profile_id) == 1
    reloaded = manager.list_profiles()[0]
    assert reloaded.prestige_tier == 1


def test_prestige_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)
    manager.prestige(profile.profile_id)

    reloaded_manager = _make_manager()
    assert reloaded_manager.list_profiles()[0].prestige_tier == 1


def test_prestige_rejected_when_not_yet_eligible(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE - 1)

    assert manager.prestige(profile.profile_id) is None
    reloaded = manager.list_profiles()[0]
    assert reloaded.prestige_tier == 0


def test_prestige_unknown_profile_returns_none(isolated_paths):
    manager = _make_manager()
    assert manager.prestige("does-not-exist") is None


def test_prestige_publishes_profile_prestiged(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)
    received = []
    manager.context.events.subscribe("profile.prestiged", lambda **kwargs: received.append(kwargs))

    manager.prestige(profile.profile_id)

    assert received == [{"profile_id": profile.profile_id, "new_tier": 1}]


def test_add_xp_crossing_the_prestige_ceiling_reports_level_100_not_101(isolated_paths):
    """Real gap caught while testing prestige() itself: add_xp()'s own
    level-up check used to run on the raw, uncapped compute_level_progress()
    — a grant landing exactly on the prestige-cycle ceiling would report
    "Level 101!", a level that doesn't exist anywhere in the capped
    display model (compute_prestige_level_progress() itself caps at a
    maxed-out level 100 until a real Prestige action). Fixed by having
    add_xp()'s own crossed_a_level() check use the prestige-aware
    function instead."""
    manager = _make_manager()
    manager.context.notifications = _FakeNotifications()
    profile = manager.create_profile(name="Alex")

    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)

    level_up_calls = [c for c in manager.context.notifications.calls if "Level" in c.get("message", "")]
    assert len(level_up_calls) == 1
    assert level_up_calls[0]["message"] == "You reached Level 100!"


def test_prestige_notifies_with_the_right_color(isolated_paths):
    """Earning exactly the prestige-cycle ceiling legitimately fires
    its own "Level 100!" notification from add_xp() too (a real level
    crossing) — prestige()'s own notification is a second, separate
    one, not a replacement for it."""
    manager = _make_manager()
    manager.context.notifications = _FakeNotifications()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)

    manager.prestige(profile.profile_id)

    prestige_calls = [c for c in manager.context.notifications.calls if "green" in c["message"]]
    assert len(prestige_calls) == 1
    assert prestige_calls[0]["source"] == "achievements"


def test_prestige_with_no_notifications_service_does_not_crash(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)
    manager.prestige(profile.profile_id)  # must not raise, context.notifications is None


def test_prestige_twice_reaches_tier_two(isolated_paths):
    manager = _make_manager()
    profile = manager.create_profile(name="Alex")
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)
    manager.prestige(profile.profile_id)
    manager.add_xp(profile.profile_id, XP_PER_PRESTIGE_CYCLE)

    assert manager.prestige(profile.profile_id) == 2
