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
