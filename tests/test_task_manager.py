"""
tests.test_task_manager
==========================

Unit tests for core.task_manager. Isolates _DATA_DIR/_TASKS_FILE into a
tmp_path scratch area (same monkeypatch pattern as
test_trip_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.task_manager as task_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.task_manager import TaskManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    tasks_file = data_dir / "tasks.json"
    monkeypatch.setattr(task_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(task_manager_module, "_TASKS_FILE", tasks_file)
    return data_dir, tasks_file


def _make_manager() -> TaskManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return TaskManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.tasks_for_project("proj1") == []


def test_add_task_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_task(
        project_id="proj1",
        title="Buy new fuse box",
        due_date="2026-08-14",
        notes="Home Depot has them in stock.",
    )

    reloaded = _make_manager()
    tasks = reloaded.tasks_for_project("proj1")
    assert len(tasks) == 1
    assert tasks[0].task_id == added.task_id
    assert tasks[0].title == "Buy new fuse box"
    assert tasks[0].done is False
    assert tasks[0].due_date == "2026-08-14"
    assert tasks[0].notes == "Home Depot has them in stock."
    assert tasks[0].created_at
    assert tasks[0].updated_at == tasks[0].created_at


def test_tasks_for_project_only_returns_matching_project(isolated_paths):
    manager = _make_manager()
    manager.add_task(project_id="proj1", title="A")
    manager.add_task(project_id="proj2", title="B")

    titles = [t.title for t in manager.tasks_for_project("proj1")]
    assert titles == ["A"]


def test_update_task_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    task = manager.add_task(project_id="proj1", title="Original")
    task.created_at = "2020-01-01T00:00:00"
    task.updated_at = "2020-01-01T00:00:00"

    manager.update_task(task.task_id, title="Renamed", done=True)

    assert task.title == "Renamed"
    assert task.done is True
    assert task.created_at == "2020-01-01T00:00:00"  # untouched
    assert task.updated_at != "2020-01-01T00:00:00"  # bumped


def test_update_task_rejects_created_at(isolated_paths):
    manager = _make_manager()
    task = manager.add_task(project_id="proj1", title="X")
    with pytest.raises(ValueError):
        manager.update_task(task.task_id, created_at="hacked")


def test_update_task_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_task("does-not-exist", title="X")


def test_update_task_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    task = manager.add_task(project_id="proj1", title="X")
    with pytest.raises(ValueError):
        manager.update_task(task.task_id, bogus_field="X")


def test_toggle_done_flips_done_state(isolated_paths):
    manager = _make_manager()
    task = manager.add_task(project_id="proj1", title="X")
    assert task.done is False

    manager.toggle_done(task.task_id)
    assert manager.get_task(task.task_id).done is True

    manager.toggle_done(task.task_id)
    assert manager.get_task(task.task_id).done is False


def test_toggle_done_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.toggle_done("does-not-exist")


def test_delete_task_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    task = manager.add_task(project_id="proj1", title="Gone soon")

    manager.delete_task(task.task_id)
    assert manager.get_task(task.task_id) is None

    manager.delete_task(task.task_id)  # already gone — must not raise


def test_get_task_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_task("does-not-exist") is None


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, tasks_file = isolated_paths
    data_dir.mkdir(parents=True)
    tasks_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.tasks_for_project("proj1") == []
