"""
tests.test_discovery_manager
================================

Unit tests for core.discovery_manager. Isolates _DATA_DIR/file
constants for discovery_manager, skill_manager, mission_manager,
project_manager, and intent_manager into a shared tmp_path scratch
area, same monkeypatch pattern as tests/test_pathway_manager.py.
"""

from __future__ import annotations

import json

import pytest

import core.discovery_manager as discovery_manager_module
import core.intent_manager as intent_manager_module
import core.mission_manager as mission_manager_module
import core.project_manager as project_manager_module
import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.discovery_manager import DiscoveryManager
from core.event_bus import EventBus
from core.intent_manager import IntentManager
from core.mission_manager import MissionManager
from core.project_manager import ProjectManager
from core.skill_manager import SkillManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(discovery_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(discovery_manager_module, "_PROPOSALS_FILE", data_dir / "mission_proposals.json")
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(project_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(project_manager_module, "_PROJECTS_FILE", data_dir / "projects.json")
    monkeypatch.setattr(intent_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(intent_manager_module, "_INTENTS_FILE", data_dir / "intents.json")
    return data_dir


def _write_skill_definitions(data_dir) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "skill_definitions.json").write_text(json.dumps({
        "skills": [
            {"skill_id": "carpentry", "name": "Carpentry", "category": "Construction"},
            {"skill_id": "framing", "name": "Framing", "category": "Construction",
             "prerequisite_skill_ids": ["carpentry"]},
        ]
    }))


def _make_context(with_projects_and_intents: bool = True) -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.skills = SkillManager(context)
    context.missions = MissionManager(context)
    if with_projects_and_intents:
        context.projects = ProjectManager(context)
        context.intents = IntentManager(context)
    return context


def _make_manager(context: AppContext) -> DiscoveryManager:
    manager = DiscoveryManager(context)
    context.discovery = manager
    return manager


_WELL_FORMED_REPLY = (
    "Mission: Build a Grow Tower\n"
    "Summary: Construct a vertical grow tower for the garden.\n"
    "Difficulty: NORMAL\n"
    "Skills: carpentry:20, framing:10\n"
    "Rationale: This builds directly on your carpentry progress and introduces framing."
)


# ------------------------------------------------------------------
# build_discovery_prompt
# ------------------------------------------------------------------

def test_prompt_shows_frontier_skill_when_no_progress_yet(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)

    prompt = manager.build_discovery_prompt("p1")

    assert "carpentry" in prompt
    assert "framing" not in prompt.split("You may ONLY reference")[0]  # framing is locked, not listed as available
    assert "Skills the user has already trained" not in prompt


def test_prompt_shows_trained_and_newly_unlocked_frontier_skill(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    context.skills.add_skill_xp("p1", "carpentry", 20)

    prompt = manager.build_discovery_prompt("p1")

    assert "Skills the user has already trained" in prompt
    assert "Carpentry" in prompt
    assert "20 XP" in prompt
    assert "Skills available to start next" in prompt
    assert "Framing" in prompt


def test_prompt_includes_active_project_and_primary_intent(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    context.intents.add_intent("Homestead Independence", primary=True)
    context.projects.add_project("Build a greenhouse", status="Active")
    manager = _make_manager(context)

    prompt = manager.build_discovery_prompt("p1")

    assert "Homestead Independence" in prompt
    assert "Build a greenhouse" in prompt


def test_prompt_includes_recently_completed_missions(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    mission = context.missions.add_mission(name="Build a Birdhouse")
    context.missions.update_mission(mission.mission_id, status="completed")
    manager = _make_manager(context)

    prompt = manager.build_discovery_prompt("p1")

    assert "Recently completed missions" in prompt
    assert "Build a Birdhouse" in prompt


def test_prompt_degrades_gracefully_with_no_projects_or_intents_wired(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context(with_projects_and_intents=False)
    manager = _make_manager(context)

    prompt = manager.build_discovery_prompt("p1")  # must not raise

    assert "carpentry" in prompt


# ------------------------------------------------------------------
# parse_and_validate_proposal
# ------------------------------------------------------------------

def test_well_formed_reply_parses_correctly(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)

    proposal = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)

    assert proposal is not None
    assert proposal.name == "Build a Grow Tower"
    assert proposal.summary == "Construct a vertical grow tower for the garden."
    assert proposal.difficulty == "NORMAL"
    assert proposal.status == "pending"
    assert proposal.profile_id == "p1"
    assert {(w.skill_id, w.xp) for w in proposal.skill_rewards} == {("carpentry", 20), ("framing", 10)}
    assert proposal.reward_xp == 30
    assert proposal.reward_credits == 10
    assert "carpentry" in proposal.rationale.lower() or "framing" in proposal.rationale.lower()


def test_unknown_skill_id_discards_whole_proposal(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = _WELL_FORMED_REPLY.replace("carpentry:20, framing:10", "carpentry:20, plumbing:10")

    assert manager.parse_and_validate_proposal("p1", reply) is None


def test_missing_mission_line_discards_proposal(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = "\n".join(line for line in _WELL_FORMED_REPLY.splitlines() if not line.startswith("Mission:"))

    assert manager.parse_and_validate_proposal("p1", reply) is None


def test_missing_skills_line_discards_proposal(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = "\n".join(line for line in _WELL_FORMED_REPLY.splitlines() if not line.startswith("Skills:"))

    assert manager.parse_and_validate_proposal("p1", reply) is None


def test_missing_rationale_discards_proposal(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = "\n".join(line for line in _WELL_FORMED_REPLY.splitlines() if not line.startswith("Rationale:"))

    assert manager.parse_and_validate_proposal("p1", reply) is None


def test_garbage_difficulty_defaults_to_normal_rather_than_discarding(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = _WELL_FORMED_REPLY.replace("Difficulty: NORMAL", "Difficulty: super hard")

    proposal = manager.parse_and_validate_proposal("p1", reply)

    assert proposal is not None
    assert proposal.difficulty == "NORMAL"


def test_out_of_range_xp_discards_proposal(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = _WELL_FORMED_REPLY.replace("carpentry:20, framing:10", "carpentry:500, framing:10")

    assert manager.parse_and_validate_proposal("p1", reply) is None


def test_malformed_skill_entry_discards_proposal(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = _WELL_FORMED_REPLY.replace("carpentry:20, framing:10", "carpentry, framing:10")

    assert manager.parse_and_validate_proposal("p1", reply) is None


def test_multiline_rationale_is_captured_in_full(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    reply = _WELL_FORMED_REPLY + "\nand it fits your active greenhouse project well."

    proposal = manager.parse_and_validate_proposal("p1", reply)

    assert proposal is not None
    assert "greenhouse project" in proposal.rationale


def test_none_or_empty_raw_text_returns_none(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)

    assert manager.parse_and_validate_proposal("p1", None) is None
    assert manager.parse_and_validate_proposal("p1", "") is None


def test_easy_and_hard_difficulty_map_to_different_reward_credits(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)

    easy = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY.replace("NORMAL", "EASY"))
    hard = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY.replace("NORMAL", "HARD"))

    assert easy.reward_credits == 5
    assert hard.reward_credits == 20


# ------------------------------------------------------------------
# record / accept / reject
# ------------------------------------------------------------------

def test_record_pending_proposal_refuses_a_second_concurrent_pending(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    first = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(first)

    second = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    result = manager.record_pending_proposal(second)

    assert result is None
    assert manager.pending_proposal_for("p1").proposal_id == first.proposal_id


def test_accept_proposal_creates_a_real_mission(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    proposal = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(proposal)

    mission = manager.accept_proposal("p1", proposal.proposal_id)

    assert mission is not None
    assert mission.name == "Build a Grow Tower"
    assert mission.assigned_by == "mia"
    assert mission.reward_xp == 30
    assert {(w.skill_id, w.xp) for w in mission.skill_rewards} == {("carpentry", 20), ("framing", 10)}
    assert context.missions.get_mission(mission.mission_id) is not None

    resolved = manager.get_proposal(proposal.proposal_id)
    assert resolved.status == "accepted"
    assert resolved.mission_id == mission.mission_id


def test_accept_proposal_for_wrong_profile_returns_none(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    proposal = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(proposal)

    assert manager.accept_proposal("someone-else", proposal.proposal_id) is None


def test_accept_proposal_twice_only_creates_one_mission(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    proposal = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(proposal)
    manager.accept_proposal("p1", proposal.proposal_id)

    second_result = manager.accept_proposal("p1", proposal.proposal_id)

    assert second_result is None
    assert len(context.missions.all_missions()) == 1


def test_reject_proposal_never_creates_a_mission(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    proposal = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(proposal)

    manager.reject_proposal("p1", proposal.proposal_id)

    assert manager.get_proposal(proposal.proposal_id).status == "rejected"
    assert context.missions.all_missions() == []
    assert manager.pending_proposal_for("p1") is None


def test_rejecting_frees_up_a_new_proposal_for_the_same_profile(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    first = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(first)
    manager.reject_proposal("p1", first.proposal_id)

    second = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    result = manager.record_pending_proposal(second)

    assert result is not None
    assert manager.pending_proposal_for("p1").proposal_id == second.proposal_id


def test_proposals_persist_across_a_fresh_load(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    proposal = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(proposal)

    reloaded = DiscoveryManager(context)

    assert reloaded.pending_proposal_for("p1") is not None
    assert reloaded.pending_proposal_for("p1").proposal_id == proposal.proposal_id


def test_proposals_are_independent_per_profile(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    manager = _make_manager(context)
    p1_proposal = manager.parse_and_validate_proposal("p1", _WELL_FORMED_REPLY)
    manager.record_pending_proposal(p1_proposal)

    p2_proposal = manager.parse_and_validate_proposal("p2", _WELL_FORMED_REPLY)
    result = manager.record_pending_proposal(p2_proposal)

    assert result is not None
    assert manager.pending_proposal_for("p1") is not None
    assert manager.pending_proposal_for("p2") is not None
