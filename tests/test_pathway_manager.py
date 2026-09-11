"""
tests.test_pathway_manager
=============================

Unit tests for core.pathway_manager. Isolates _DATA_DIR/_PATHWAYS_FILE/
_PROGRESS_FILE plus core.mission_manager's own file constants (Pathway
tests need a real MissionManager — start_pathway() creates real
Missions) into a tmp_path scratch area, same monkeypatch pattern as
every other manager test file.
"""

from __future__ import annotations

import json

import pytest

import core.mission_manager as mission_manager_module
import core.pathway_manager as pathway_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.mission_manager import MissionManager
from core.pathway_manager import PathwayManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(pathway_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(pathway_manager_module, "_PATHWAYS_FILE", data_dir / "mission_pathways.json")
    monkeypatch.setattr(pathway_manager_module, "_PROGRESS_FILE", data_dir / "pathway_progress.json")
    return data_dir


def _write_pathways(data_dir, pathways: list[dict]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "mission_pathways.json").write_text(json.dumps({"pathways": pathways}))


_TWO_STEP_PATHWAY = {
    "pathway_id": "test_path",
    "skill_id": "carpentry",
    "name": "Test Pathway",
    "steps": [
        {"name": "Step One", "skill_rewards": [{"skill_id": "carpentry", "xp": 10}]},
        {"name": "Step Two", "skill_rewards": [{"skill_id": "carpentry", "xp": 20}]},
    ],
}


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.missions = MissionManager(context)
    return context


def _make_manager(context: AppContext) -> PathwayManager:
    manager = PathwayManager(context)
    context.pathways = manager
    return manager


class _FakeNotifications:
    def __init__(self):
        self.calls: list[dict] = []

    def notify(self, title, message, level="info", source="system"):
        self.calls.append({"title": title, "message": message, "level": level, "source": source})


# ------------------------------------------------------------------
# Definitions
# ------------------------------------------------------------------

def test_all_pathways_empty_when_no_file_exists(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.all_pathways() == []


def test_all_pathways_loads_from_file(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)
    pathways = manager.all_pathways()
    assert len(pathways) == 1
    assert pathways[0].pathway_id == "test_path"
    assert len(pathways[0].steps) == 2


def test_get_pathway_returns_none_for_unknown_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.get_pathway("does-not-exist") is None


def test_pathways_for_skill_filters_correctly(isolated_paths):
    other = dict(_TWO_STEP_PATHWAY, pathway_id="other", skill_id="gardening")
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY, other])
    context = _make_context()
    manager = _make_manager(context)
    assert [p.pathway_id for p in manager.pathways_for_skill("carpentry")] == ["test_path"]


# ------------------------------------------------------------------
# start_pathway
# ------------------------------------------------------------------

def test_start_pathway_creates_the_first_mission(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)

    mission = manager.start_pathway("p1", "test_path")

    assert mission is not None
    assert mission.name == "Step One"
    assert mission.assigned_by == "mia"
    assert context.missions.get_mission(mission.mission_id) is not None


def test_start_pathway_records_progress(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)

    mission = manager.start_pathway("p1", "test_path")

    progress = manager.status_for("p1", "test_path")
    assert progress is not None
    assert progress.status == "active"
    assert progress.current_step_index == 0
    assert progress.current_mission_id == mission.mission_id


def test_start_pathway_persists_across_a_fresh_load(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)
    manager.start_pathway("p1", "test_path")

    reloaded = PathwayManager(context)
    assert reloaded.status_for("p1", "test_path") is not None


def test_start_pathway_unknown_id_returns_none(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.start_pathway("p1", "does-not-exist") is None


def test_start_pathway_with_no_steps_returns_none(isolated_paths):
    empty = dict(_TWO_STEP_PATHWAY, pathway_id="empty", steps=[])
    _write_pathways(isolated_paths, [empty])
    context = _make_context()
    manager = _make_manager(context)
    assert manager.start_pathway("p1", "empty") is None


def test_start_pathway_refuses_a_second_concurrent_start(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)
    manager.start_pathway("p1", "test_path")

    second = manager.start_pathway("p1", "test_path")

    assert second is None
    assert len(context.missions.all_missions()) == 1


def test_start_pathway_is_independent_per_profile(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)
    manager.start_pathway("p1", "test_path")

    mission_for_p2 = manager.start_pathway("p2", "test_path")

    assert mission_for_p2 is not None
    assert len(context.missions.all_missions()) == 2


def test_start_pathway_with_no_missions_service_returns_none(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = _make_manager(context)
    assert manager.start_pathway("p1", "test_path") is None


# ------------------------------------------------------------------
# Advancing via the real "mission.completed" event
# ------------------------------------------------------------------

def test_completing_the_current_mission_advances_to_the_next_step(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = _make_manager(context)
    first_mission = manager.start_pathway("p1", "test_path")

    context.missions.update_mission(first_mission.mission_id, status="completed")

    progress = manager.status_for("p1", "test_path")
    assert progress.status == "active"
    assert progress.current_step_index == 1
    assert progress.current_mission_id != first_mission.mission_id
    next_mission = context.missions.get_mission(progress.current_mission_id)
    assert next_mission.name == "Step Two"

    unlock_calls = [c for c in context.notifications.calls if c["source"] == "pathways"]
    assert len(unlock_calls) == 1
    assert unlock_calls[0]["title"] == "\U0001F513 New Mission Unlocked!"
    assert unlock_calls[0]["message"] == "Step Two"


def test_completing_the_last_step_marks_the_pathway_completed(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    context.notifications = _FakeNotifications()
    manager = _make_manager(context)
    first_mission = manager.start_pathway("p1", "test_path")
    context.missions.update_mission(first_mission.mission_id, status="completed")
    progress = manager.status_for("p1", "test_path")
    second_mission_id = progress.current_mission_id

    context.missions.update_mission(second_mission_id, status="completed")

    progress = manager.status_for("p1", "test_path")
    assert progress.status == "completed"
    assert len(context.missions.all_missions()) == 2  # no third mission created

    complete_calls = [c for c in context.notifications.calls if c["title"] == "\U0001F3C6 Pathway complete!"]
    assert len(complete_calls) == 1
    assert complete_calls[0]["source"] == "pathways"


def test_an_unrelated_missions_completion_does_not_affect_any_pathway(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)
    manager.start_pathway("p1", "test_path")
    unrelated = context.missions.add_mission(name="Unrelated Mission")

    context.missions.update_mission(unrelated.mission_id, status="completed")

    progress = manager.status_for("p1", "test_path")
    assert progress.status == "active"
    assert progress.current_step_index == 0


def test_a_completed_pathway_can_be_started_again(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)
    first_mission = manager.start_pathway("p1", "test_path")
    context.missions.update_mission(first_mission.mission_id, status="completed")
    progress = manager.status_for("p1", "test_path")
    context.missions.update_mission(progress.current_mission_id, status="completed")
    assert manager.status_for("p1", "test_path").status == "completed"

    restarted = manager.start_pathway("p1", "test_path")

    assert restarted is not None
    assert restarted.name == "Step One"
    assert manager.status_for("p1", "test_path").status == "active"


# ------------------------------------------------------------------
# status_for
# ------------------------------------------------------------------

def test_status_for_returns_none_when_never_started(isolated_paths):
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY])
    context = _make_context()
    manager = _make_manager(context)
    assert manager.status_for("p1", "test_path") is None


def test_progress_for_profile_lists_all_of_that_profiles_pathways(isolated_paths):
    other = dict(_TWO_STEP_PATHWAY, pathway_id="other")
    _write_pathways(isolated_paths, [_TWO_STEP_PATHWAY, other])
    context = _make_context()
    manager = _make_manager(context)
    manager.start_pathway("p1", "test_path")
    manager.start_pathway("p1", "other")
    manager.start_pathway("p2", "test_path")

    assert len(manager.progress_for_profile("p1")) == 2
    assert len(manager.progress_for_profile("p2")) == 1
