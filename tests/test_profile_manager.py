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
from core.profile_manager import ProfileManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")


def _make_manager() -> ProfileManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ProfileManager(context)


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
