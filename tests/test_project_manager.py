"""
tests.test_project_manager
=============================

Unit tests for core.project_manager. Isolates _DATA_DIR/_PROJECTS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_expedition_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.project_manager as project_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.project_manager import ProjectManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    projects_file = data_dir / "projects.json"
    monkeypatch.setattr(project_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(project_manager_module, "_PROJECTS_FILE", projects_file)
    return data_dir, projects_file


def _make_manager() -> ProjectManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ProjectManager(context)


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
