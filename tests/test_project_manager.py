"""
tests.test_project_manager
=============================

Unit tests for core.project_manager. Isolates _DATA_DIR/_PROJECTS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_expedition_manager.py's isolated_paths).
"""

from __future__ import annotations

import json

import pytest

import core.project_manager as project_manager_module
import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.gamification import SkillWeight
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.skill_manager import SkillManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    projects_file = data_dir / "projects.json"
    monkeypatch.setattr(project_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(project_manager_module, "_PROJECTS_FILE", projects_file)
    # Needed once a test constructs a real ProfileManager/SkillManager
    # too (skill-crediting tests below) — same reasoning as every other
    # manager test file's own isolated_paths fixture.
    import core.config_manager as config_manager_module

    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    return data_dir, projects_file


def _make_manager() -> ProjectManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ProjectManager(context)


def _make_manager_with_profile_and_skills(data_dir, skill_ids: list[str]) -> ProjectManager:
    """"My Hero's Path" Phase 2 tests need a real active profile and
    real skill definitions — a skill_weights entry pointing to an
    unknown skill_id is silently dropped by SkillManager.add_skill_xp()
    by design, so a test proving XP actually lands needs the skill
    defined first, same pattern as test_mission_manager.py's own
    _make_context_with_profiles_and_skills()."""
    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = ProjectManager(context)
    context.projects = manager
    context.profiles = ProfileManager(context)
    context.profiles.create_profile(name="Alex", make_active=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "skill_definitions.json").write_text(
        json.dumps({"skills": [{"skill_id": sid, "name": sid, "category": "Test"} for sid in skill_ids]})
    )
    context.skills = SkillManager(context)
    return manager


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_projects() == []


def test_add_project_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_project(
        name="Garage Rewire",
        status="Active",
        due_date="2026-08-14",
        description="Replace the old fuse box.",
    )

    reloaded = _make_manager()
    projects = reloaded.all_projects()
    assert len(projects) == 1
    assert projects[0].project_id == added.project_id
    assert projects[0].name == "Garage Rewire"
    assert projects[0].status == "Active"
    assert projects[0].due_date == "2026-08-14"
    assert projects[0].description == "Replace the old fuse box."
    assert projects[0].created_at
    assert projects[0].updated_at == projects[0].created_at


def test_add_project_defaults_to_planning_status(isolated_paths):
    manager = _make_manager()
    added = manager.add_project(name="No status given")
    assert added.status == "Planning"


def test_update_project_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    project = manager.add_project(name="Original")
    project.created_at = "2020-01-01T00:00:00"
    project.updated_at = "2020-01-01T00:00:00"

    manager.update_project(project.project_id, name="Renamed", status="Complete")

    assert project.name == "Renamed"
    assert project.status == "Complete"
    assert project.created_at == "2020-01-01T00:00:00"  # untouched
    assert project.updated_at != "2020-01-01T00:00:00"  # bumped


def test_update_project_rejects_created_at(isolated_paths):
    manager = _make_manager()
    project = manager.add_project(name="X")
    with pytest.raises(ValueError):
        manager.update_project(project.project_id, created_at="hacked")


def test_update_project_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_project("does-not-exist", name="X")


def test_update_project_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    project = manager.add_project(name="X")
    with pytest.raises(ValueError):
        manager.update_project(project.project_id, bogus_field="X")


def test_delete_project_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    project = manager.add_project(name="Gone soon")

    manager.delete_project(project.project_id)
    assert manager.get_project(project.project_id) is None

    manager.delete_project(project.project_id)  # already gone — must not raise


def test_get_project_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_project("does-not-exist") is None


def test_all_projects_sorted_by_due_date_with_blank_last(isolated_paths):
    manager = _make_manager()
    manager.add_project(name="No due date")
    manager.add_project(name="Later", due_date="2026-09-01")
    manager.add_project(name="Earlier", due_date="2026-07-01")

    ordered = [p.name for p in manager.all_projects()]
    assert ordered == ["Earlier", "Later", "No due date"]


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, projects_file = isolated_paths
    data_dir.mkdir(parents=True)
    projects_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_projects() == []


# ----------------------------------------------------------------------
# intent_id — connective-infrastructure pass (2026-09-11)
# ----------------------------------------------------------------------

def test_add_project_with_intent_id_persists(isolated_paths):
    manager = _make_manager()
    added = manager.add_project(name="Aquaponics Pilot", intent_id="intent1")

    reloaded = _make_manager()
    assert reloaded.get_project(added.project_id).intent_id == "intent1"


def test_add_project_intent_id_defaults_to_none(isolated_paths):
    manager = _make_manager()
    added = manager.add_project(name="X")
    assert added.intent_id is None


def test_project_with_no_intent_id_key_deserializes_to_none(isolated_paths):
    """Backward compatibility: old projects.json rows with no intent_id
    key at all must still deserialize cleanly."""
    data_dir, projects_file = isolated_paths
    data_dir.mkdir(parents=True, exist_ok=True)
    projects_file.write_text(json.dumps([{"project_id": "p1", "name": "Old Project"}]))
    manager = _make_manager()
    assert manager.get_project("p1").intent_id is None


# ----------------------------------------------------------------------
# skill_weights + completion crediting — "My Hero's Path" Phase 2
# ----------------------------------------------------------------------

def test_completing_a_project_credits_skill_weights(isolated_paths):
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics", "fabrication"])
    project = manager.add_project(
        name="Aquaponics Pilot",
        skill_weights=[SkillWeight("aquaponics", 120), SkillWeight("fabrication", 40)],
    )

    manager.update_project(project.project_id, status="Complete")

    active = manager.context.profiles.get_active_profile()
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 120
    assert manager.context.skills.get_progress(active.profile_id, "fabrication").total_xp == 40


def test_completing_a_project_with_no_skill_weights_credits_nothing(isolated_paths):
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics"])
    project = manager.add_project(name="X")

    manager.update_project(project.project_id, status="Complete")  # must not raise

    active = manager.context.profiles.get_active_profile()
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 0


def test_recompleting_a_project_does_not_double_credit(isolated_paths):
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics"])
    project = manager.add_project(name="X", skill_weights=[SkillWeight("aquaponics", 100)])

    manager.update_project(project.project_id, status="Complete")
    manager.update_project(project.project_id, status="Active")
    manager.update_project(project.project_id, status="Complete")

    active = manager.context.profiles.get_active_profile()
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 100


def test_recompleting_a_project_after_reactivating_does_not_double_credit(isolated_paths):
    """The real exploit vector this flag exists to close: unlike
    Mission's status, a Project can cycle Complete -> Active -> Complete
    again. Re-completing after reactivating must not re-grant."""
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics"])
    project = manager.add_project(name="X", skill_weights=[SkillWeight("aquaponics", 100)])

    manager.update_project(project.project_id, status="Complete")
    manager.update_project(project.project_id, status="Active")
    manager.update_project(project.project_id, status="Complete")

    active = manager.context.profiles.get_active_profile()
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 100


def test_reactivating_and_recompleting_after_a_retroactive_tag_does_not_recredit_it(isolated_paths):
    """A weight added retroactively while already Complete gets credited
    immediately (its own test above) — a LATER reactivate+recomplete
    cycle must not credit it a second time either."""
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics", "fabrication"])
    project = manager.add_project(name="X", skill_weights=[SkillWeight("aquaponics", 100)])
    manager.update_project(project.project_id, status="Complete")
    manager.add_skill_weight(project.project_id, "fabrication", 30)

    manager.update_project(project.project_id, status="Active")
    manager.update_project(project.project_id, status="Complete")

    active = manager.context.profiles.get_active_profile()
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 100
    assert manager.context.skills.get_progress(active.profile_id, "fabrication").total_xp == 30


def test_completing_a_project_with_skill_weights_and_no_skills_service_does_not_crash(isolated_paths):
    manager = _make_manager()
    project = manager.add_project(name="X", skill_weights=[SkillWeight("aquaponics", 100)])
    manager.update_project(project.project_id, status="Complete")  # must not raise


def test_project_skill_weights_persist_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_project(name="X", skill_weights=[SkillWeight("aquaponics", 100)])

    reloaded = _make_manager()
    project = reloaded.all_projects()[0]
    assert project.skill_weights == [SkillWeight("aquaponics", 100)]


def test_project_with_no_skill_weights_key_deserializes_to_empty_list(isolated_paths):
    """Backward compatibility: old projects.json rows with no
    skill_weights key at all must still deserialize cleanly."""
    data_dir, projects_file = isolated_paths
    data_dir.mkdir(parents=True, exist_ok=True)
    projects_file.write_text(json.dumps([{"project_id": "p1", "name": "Old Project"}]))
    manager = _make_manager()
    assert manager.get_project("p1").skill_weights == []


# ----------------------------------------------------------------------
# add_skill_weight — retroactive tagging
# ----------------------------------------------------------------------

def test_add_skill_weight_before_completion_waits_for_completion(isolated_paths):
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics"])
    project = manager.add_project(name="X")

    manager.add_skill_weight(project.project_id, "aquaponics", 50)

    active = manager.context.profiles.get_active_profile()
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 0

    manager.update_project(project.project_id, status="Complete")
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 50


def test_add_skill_weight_after_completion_credits_immediately(isolated_paths):
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics", "fabrication"])
    project = manager.add_project(name="X", skill_weights=[SkillWeight("aquaponics", 100)])
    manager.update_project(project.project_id, status="Complete")

    manager.add_skill_weight(project.project_id, "fabrication", 30)

    active = manager.context.profiles.get_active_profile()
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 100
    assert manager.context.skills.get_progress(active.profile_id, "fabrication").total_xp == 30


def test_add_skill_weight_after_completion_does_not_recredit_earlier_weights(isolated_paths):
    """The whole point of retroactive tagging: adding ONE new weight to
    an already-complete Project must never re-grant the weights that
    were already credited when it first completed."""
    data_dir, _ = isolated_paths
    manager = _make_manager_with_profile_and_skills(data_dir, ["aquaponics", "fabrication"])
    project = manager.add_project(name="X", skill_weights=[SkillWeight("aquaponics", 100)])
    manager.update_project(project.project_id, status="Complete")

    manager.add_skill_weight(project.project_id, "fabrication", 30)

    active = manager.context.profiles.get_active_profile()
    # aquaponics must still read exactly 100 -- not 200 from a second grant
    assert manager.context.skills.get_progress(active.profile_id, "aquaponics").total_xp == 100


def test_add_skill_weight_unknown_project_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.add_skill_weight("does-not-exist", "aquaponics", 10)


def test_add_skill_weight_appends_to_the_list_regardless_of_status(isolated_paths):
    manager = _make_manager()
    project = manager.add_project(name="X")
    manager.add_skill_weight(project.project_id, "aquaponics", 10)
    assert manager.get_project(project.project_id).skill_weights == [SkillWeight("aquaponics", 10)]
