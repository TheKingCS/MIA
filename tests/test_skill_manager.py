"""
tests.test_skill_manager
===========================

Unit tests for core.skill_manager.SkillManager — isolates _DATA_DIR/
_SKILL_DEFINITIONS_FILE/_SKILL_PROGRESS_FILE into a tmp_path scratch
area, same monkeypatch pattern as every other manager test file.
Definitions are written directly to the isolated file per test (not
the real seeded data/skill_definitions.json) so tests don't depend on
that file's real content.
"""

from __future__ import annotations

import json

import pytest

import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.skill_manager import SkillManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    return data_dir


def _write_definitions(data_dir, skills: list[dict]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "skill_definitions.json").write_text(json.dumps({"skills": skills}))


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


class _FakeNotifications:
    """Same "fake just what's used" shape as
    tests/test_gamification.py's own _FakeNotifications — records
    every notify() call so achievement-firing tests can assert on
    title/message/source without a real NotificationManager."""

    def __init__(self):
        self.calls: list[dict] = []

    def notify(self, title, message, level="info", source="system"):
        self.calls.append({"title": title, "message": message, "level": level, "source": source})


# ------------------------------------------------------------------
# Definitions
# ------------------------------------------------------------------

def test_all_skills_empty_when_no_definitions_file(isolated_paths):
    context = _make_context()
    manager = SkillManager(context)
    assert manager.all_skills() == []


def test_all_skills_loads_from_definitions_file(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    manager = SkillManager(context)
    skills = manager.all_skills()
    assert len(skills) == 1
    assert skills[0].skill_id == "strength"
    assert skills[0].name == "Strength"
    assert skills[0].category == "Body"


def test_get_skill_returns_none_for_unknown_id(isolated_paths):
    context = _make_context()
    manager = SkillManager(context)
    assert manager.get_skill("does-not-exist") is None


def test_categories_derived_live_and_sorted(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "python", "name": "Python", "category": "Technology"},
            {"skill_id": "strength", "name": "Strength", "category": "Body"},
            {"skill_id": "linux", "name": "Linux", "category": "Technology"},
        ],
    )
    context = _make_context()
    manager = SkillManager(context)
    assert manager.categories() == ["Body", "Technology"]


def test_skills_in_category_filters_correctly(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "python", "name": "Python", "category": "Technology"},
            {"skill_id": "strength", "name": "Strength", "category": "Body"},
        ],
    )
    context = _make_context()
    manager = SkillManager(context)
    tech = manager.skills_in_category("Technology")
    assert [s.skill_id for s in tech] == ["python"]


# ------------------------------------------------------------------
# Progress / add_skill_xp
# ------------------------------------------------------------------

def test_get_progress_untrained_skill_returns_zero_xp(isolated_paths):
    context = _make_context()
    manager = SkillManager(context)
    progress = manager.get_progress("p1", "strength")
    assert progress.total_xp == 0


def test_add_skill_xp_accumulates(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    manager = SkillManager(context)

    assert manager.add_skill_xp("p1", "strength", 10) == 10
    assert manager.add_skill_xp("p1", "strength", 5) == 15
    assert manager.get_progress("p1", "strength").total_xp == 15


def test_add_skill_xp_persists_across_a_fresh_load(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    manager = SkillManager(context)
    manager.add_skill_xp("p1", "strength", 10)

    reloaded = SkillManager(context)
    assert reloaded.get_progress("p1", "strength").total_xp == 10


def test_add_skill_xp_unknown_skill_returns_none_and_does_not_persist(isolated_paths):
    context = _make_context()
    manager = SkillManager(context)
    assert manager.add_skill_xp("p1", "does-not-exist", 10) is None
    assert manager.get_progress("p1", "does-not-exist").total_xp == 0


def test_add_skill_xp_is_per_profile(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    manager = SkillManager(context)
    manager.add_skill_xp("p1", "strength", 10)

    assert manager.get_progress("p1", "strength").total_xp == 10
    assert manager.get_progress("p2", "strength").total_xp == 0


def test_add_skill_xp_publishes_profile_skill_xp_changed(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    manager = SkillManager(context)
    received = []
    context.events.subscribe("profile.skill_xp_changed", lambda **kwargs: received.append(kwargs))

    manager.add_skill_xp("p1", "strength", 10)

    assert received == [{"profile_id": "p1", "skill_id": "strength"}]


def test_add_skill_xp_unknown_skill_does_not_publish(isolated_paths):
    context = _make_context()
    manager = SkillManager(context)
    received = []
    context.events.subscribe("profile.skill_xp_changed", lambda **kwargs: received.append(kwargs))

    manager.add_skill_xp("p1", "does-not-exist", 10)

    assert received == []


def test_progress_for_profile_only_includes_trained_skills(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "strength", "name": "Strength", "category": "Body"},
            {"skill_id": "python", "name": "Python", "category": "Technology"},
        ],
    )
    context = _make_context()
    manager = SkillManager(context)
    manager.add_skill_xp("p1", "strength", 10)

    progress = manager.progress_for_profile("p1")
    assert [p.skill_id for p in progress] == ["strength"]


# ------------------------------------------------------------------
# is_unlocked — derived from prerequisite skills having any XP
# ------------------------------------------------------------------

def test_is_unlocked_true_when_no_prerequisites(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    manager = SkillManager(context)
    assert manager.is_unlocked("p1", "strength") is True


def test_is_unlocked_false_when_prerequisite_untrained(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "3d_printing", "name": "3D Printing", "category": "Maker"},
            {
                "skill_id": "cad",
                "name": "CAD",
                "category": "Maker",
                "prerequisite_skill_ids": ["3d_printing"],
            },
        ],
    )
    context = _make_context()
    manager = SkillManager(context)
    assert manager.is_unlocked("p1", "cad") is False


def test_is_unlocked_true_once_prerequisite_has_any_xp(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "3d_printing", "name": "3D Printing", "category": "Maker"},
            {
                "skill_id": "cad",
                "name": "CAD",
                "category": "Maker",
                "prerequisite_skill_ids": ["3d_printing"],
            },
        ],
    )
    context = _make_context()
    manager = SkillManager(context)
    manager.add_skill_xp("p1", "3d_printing", 1)
    assert manager.is_unlocked("p1", "cad") is True


def test_is_unlocked_requires_all_prerequisites_when_multiple(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "automation", "name": "Automation", "category": "Technology"},
            {"skill_id": "fabrication", "name": "Fabrication", "category": "Maker"},
            {
                "skill_id": "robotics",
                "name": "Robotics",
                "category": "Technology",
                "prerequisite_skill_ids": ["automation", "fabrication"],
            },
        ],
    )
    context = _make_context()
    manager = SkillManager(context)
    manager.add_skill_xp("p1", "automation", 1)
    assert manager.is_unlocked("p1", "robotics") is False

    manager.add_skill_xp("p1", "fabrication", 1)
    assert manager.is_unlocked("p1", "robotics") is True


def test_add_skill_xp_grants_even_when_locked(isolated_paths):
    """A real activity's XP is real evidence of what happened and must
    never be silently dropped just because the skill tree hasn't
    "revealed" that node yet — is_unlocked() is a display concern, not
    a gate on add_skill_xp()."""
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "3d_printing", "name": "3D Printing", "category": "Maker"},
            {
                "skill_id": "cad",
                "name": "CAD",
                "category": "Maker",
                "prerequisite_skill_ids": ["3d_printing"],
            },
        ],
    )
    context = _make_context()
    manager = SkillManager(context)
    assert manager.is_unlocked("p1", "cad") is False

    assert manager.add_skill_xp("p1", "cad", 10) == 10
    assert manager.get_progress("p1", "cad").total_xp == 10


# ------------------------------------------------------------------
# Achievements/Milestones (2026-09-11) — level-up + unlock notifications
# ------------------------------------------------------------------

def test_add_skill_xp_fires_level_up_notification(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = SkillManager(context)

    # Level 1 needs 20 XP -- 25 crosses into level 2.
    manager.add_skill_xp("p1", "strength", 25)

    level_up_calls = [c for c in context.notifications.calls if c["source"] == "achievements"]
    assert len(level_up_calls) == 1
    assert level_up_calls[0]["title"] == "\U0001F393 Skill level up!"
    assert level_up_calls[0]["message"] == "Strength reached Level 2!"


def test_add_skill_xp_does_not_fire_level_up_when_staying_in_the_same_level(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = SkillManager(context)

    manager.add_skill_xp("p1", "strength", 5)  # well under the 20 XP needed for level 2

    assert context.notifications.calls == []


def test_add_skill_xp_fires_unlock_notification_for_a_real_dependent(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "3d_printing", "name": "3D Printing", "category": "Maker"},
            {
                "skill_id": "cad",
                "name": "CAD",
                "category": "Maker",
                "prerequisite_skill_ids": ["3d_printing"],
            },
        ],
    )
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = SkillManager(context)

    manager.add_skill_xp("p1", "3d_printing", 1)  # first-ever XP -- unlocks CAD

    unlock_calls = [c for c in context.notifications.calls if c["title"] == "\U0001F513 New skill unlocked!"]
    assert len(unlock_calls) == 1
    assert unlock_calls[0]["message"] == "You've unlocked CAD — take a look."
    assert unlock_calls[0]["source"] == "achievements"


def test_add_skill_xp_does_not_fire_unlock_when_a_skill_has_no_dependents(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = SkillManager(context)

    manager.add_skill_xp("p1", "strength", 1)

    unlock_calls = [c for c in context.notifications.calls if "unlocked" in c["title"]]
    assert unlock_calls == []


def test_add_skill_xp_does_not_refire_unlock_on_a_second_grant(isolated_paths):
    """A dependent's unlock condition can only ever transition once
    (locked -> unlocked) since is_unlocked() only checks whether a
    prerequisite has ANY xp — a second grant to an already-trained
    prerequisite must not re-fire the unlock notification."""
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "3d_printing", "name": "3D Printing", "category": "Maker"},
            {
                "skill_id": "cad",
                "name": "CAD",
                "category": "Maker",
                "prerequisite_skill_ids": ["3d_printing"],
            },
        ],
    )
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = SkillManager(context)

    manager.add_skill_xp("p1", "3d_printing", 1)
    manager.add_skill_xp("p1", "3d_printing", 5)  # second grant to the same, already-trained skill

    unlock_calls = [c for c in context.notifications.calls if "unlocked" in c["title"]]
    assert len(unlock_calls) == 1


def test_add_skill_xp_does_not_fire_unlock_when_other_prerequisites_still_missing(isolated_paths):
    _write_definitions(
        isolated_paths,
        [
            {"skill_id": "automation", "name": "Automation", "category": "Technology"},
            {"skill_id": "fabrication", "name": "Fabrication", "category": "Maker"},
            {
                "skill_id": "robotics",
                "name": "Robotics",
                "category": "Technology",
                "prerequisite_skill_ids": ["automation", "fabrication"],
            },
        ],
    )
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = SkillManager(context)

    manager.add_skill_xp("p1", "automation", 1)  # fabrication still untrained -- robotics stays locked

    unlock_calls = [c for c in context.notifications.calls if "unlocked" in c["title"]]
    assert unlock_calls == []


def test_add_skill_xp_with_no_notifications_service_does_not_crash(isolated_paths):
    _write_definitions(isolated_paths, [{"skill_id": "strength", "name": "Strength", "category": "Body"}])
    context = _make_context()
    manager = SkillManager(context)
    manager.add_skill_xp("p1", "strength", 100)  # must not raise, context.notifications is None
