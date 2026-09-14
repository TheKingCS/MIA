"""
tests.test_context_assembler
================================

Unit/integration tests for core.context_assembler — the "Life State"
synthesis layer. Isolates every underlying manager's own data files
into a tmp_path scratch area, same monkeypatch pattern as
test_skill_patterns.py's own isolated_paths, extended to cover the
extra managers assemble_life_state() reads from (Mission, Maintenance,
Project, RecurringMission).
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

import core.config_manager as config_manager_module
import core.insight_manager as insight_manager_module
import core.maintenance_manager as maintenance_manager_module
import core.mission_manager as mission_manager_module
import core.profile_manager as profile_manager_module
import core.project_manager as project_manager_module
import core.recurring_mission_manager as recurring_mission_manager_module
import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.context_assembler import assemble_life_state, format_life_state_glance_line, format_life_state_summary
from core.event_bus import EventBus
from core.insight_manager import InsightManager
from core.maintenance_manager import MaintenanceManager
from core.mission_manager import MissionManager
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.recurring_mission_manager import RecurringMissionManager
from core.skill_manager import SkillManager

TODAY = date(2026, 9, 14)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_XP_LOG_FILE", data_dir / "skill_xp_log.json")
    monkeypatch.setattr(insight_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(insight_manager_module, "_INSIGHTS_FILE", data_dir / "insights.json")
    monkeypatch.setattr(insight_manager_module, "_RECOMMENDATIONS_FILE", data_dir / "recommendations.json")
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(maintenance_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(maintenance_manager_module, "_MAINTENANCE_FILE", data_dir / "maintenance.json")
    monkeypatch.setattr(project_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(project_manager_module, "_PROJECTS_FILE", data_dir / "projects.json")
    monkeypatch.setattr(recurring_mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(recurring_mission_manager_module, "_TEMPLATES_FILE", data_dir / "recurring_mission_templates.json")
    return data_dir


def _write_skill_definitions(data_dir, skills: list[dict]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "skill_definitions.json").write_text(json.dumps({"skills": skills}))


def _full_context(data_dir) -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.skills = SkillManager(context)
    context.insights = InsightManager(context)
    context.missions = MissionManager(context)
    context.maintenance = MaintenanceManager(context)
    context.projects = ProjectManager(context)
    context.recurring_missions = RecurringMissionManager(context)
    return context


# ------------------------------------------------------------------
# Graceful degradation
# ------------------------------------------------------------------

def test_assemble_life_state_with_no_services_returns_empty_snapshot(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.profile_id == "p1"
    assert snapshot.active_mission_count == 0
    assert snapshot.recurring_streaks == []
    assert snapshot.skills_growing == []
    assert snapshot.system_signals == []
    assert snapshot.overdue_maintenance_count == 0
    assert snapshot.active_project_count == 0


# ------------------------------------------------------------------
# Missions
# ------------------------------------------------------------------

def test_active_mission_count_includes_unattributed_missions(isolated_paths):
    context = _full_context(isolated_paths)
    context.missions.add_mission("Unattributed mission")
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.active_mission_count == 1


def test_active_mission_count_includes_assigned_and_participant_missions(isolated_paths):
    context = _full_context(isolated_paths)
    context.missions.add_mission("Zac's mission", profile_id="p1")
    context.missions.add_mission("Faith's mission", profile_id="p2")
    context.missions.add_mission("Group quest", participant_profile_ids=["p1", "p2"])
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.active_mission_count == 2  # Zac's own + the group quest, not Faith's


def test_active_mission_count_excludes_completed_missions(isolated_paths):
    context = _full_context(isolated_paths)
    mission = context.missions.add_mission("Done already")
    context.missions.update_mission(mission.mission_id, status="completed")
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.active_mission_count == 0


# ------------------------------------------------------------------
# Recurring streaks
# ------------------------------------------------------------------

def test_recurring_streaks_includes_a_real_completed_weekly_occurrence(isolated_paths):
    context = _full_context(isolated_paths)
    template = context.recurring_missions.add_template(
        name="Laundry",
        objective_description_template="Do {target:g} loads of laundry",
        base_target=3,
        target_increment_per_week=0,
        daily_reward_xp=10,
        weekly_bonus_reward_xp=0,
        start_date=TODAY.isoformat(),
        recurrence="weekly",
        category="Household",
    )
    mission, _ = context.recurring_missions.ensure_current_missions(template, TODAY)
    context.missions.update_mission(mission.mission_id, status="completed")

    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.recurring_streaks == [("Laundry", 1)]


def test_recurring_streaks_excludes_a_template_with_no_completed_occurrence(isolated_paths):
    context = _full_context(isolated_paths)
    context.recurring_missions.add_template(
        name="Laundry",
        objective_description_template="Do {target:g} loads of laundry",
        base_target=3,
        target_increment_per_week=0,
        daily_reward_xp=10,
        weekly_bonus_reward_xp=0,
        start_date=TODAY.isoformat(),
        recurrence="weekly",
        category="Household",
    )
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.recurring_streaks == []


# ------------------------------------------------------------------
# Skills
# ------------------------------------------------------------------

def test_skills_growing_declining_dormant(isolated_paths):
    _write_skill_definitions(isolated_paths, [
        {"skill_id": "baking", "name": "Baking", "category": "Cooking"},
        {"skill_id": "carpentry", "name": "Carpentry", "category": "Maker"},
    ])
    context = _full_context(isolated_paths)
    profile = context.profiles.create_profile(name="Alex")
    context.profiles.set_interview_answers(profile.profile_id, ["Maker"], "")

    # A real burst -> Cooking should show up as growing.
    context.skills.add_skill_xp(profile.profile_id, "baking", 40)
    context.skills._xp_log[-1].timestamp = (TODAY - timedelta(days=2)).isoformat()
    context.skills._save_xp_log()

    snapshot = assemble_life_state(context, profile.profile_id, TODAY)
    assert snapshot.skills_growing == ["Cooking"]
    assert snapshot.skills_dormant == ["Maker"]  # stated interest, zero real XP


def test_skills_declining_flags_a_real_stale_category(isolated_paths):
    _write_skill_definitions(isolated_paths, [{"skill_id": "carpentry", "name": "Carpentry", "category": "Maker"}])
    context = _full_context(isolated_paths)
    profile = context.profiles.create_profile(name="Alex")
    context.skills.add_skill_xp(profile.profile_id, "carpentry", 20)
    context.skills._progress[(profile.profile_id, "carpentry")].last_touched = (TODAY - timedelta(days=61)).isoformat()
    context.skills._save_progress()

    snapshot = assemble_life_state(context, profile.profile_id, TODAY)
    assert snapshot.skills_declining == ["Maker"]


# ------------------------------------------------------------------
# System signals (open Insights)
# ------------------------------------------------------------------

def test_system_signals_includes_household_wide_insight(isolated_paths):
    context = _full_context(isolated_paths)
    context.insights.create_insight_if_new(
        source_type="maintenance", source_id="task1", kind="overdue",
        title="Mower overdue", message="The mower is overdue for an oil change.",
    )
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.system_signals == ["The mower is overdue for an oil change."]


def test_system_signals_includes_own_pattern_insight_excludes_other_profiles(isolated_paths):
    context = _full_context(isolated_paths)
    context.insights.create_insight_if_new(
        source_type="patterns", source_id="p1", kind="skill_momentum",
        title="p1", message="p1's own momentum signal.",
    )
    context.insights.create_insight_if_new(
        source_type="patterns", source_id="p2", kind="skill_momentum",
        title="p2", message="p2's own momentum signal — must not leak into p1's summary.",
    )
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.system_signals == ["p1's own momentum signal."]


def test_system_signals_excludes_resolved_insights(isolated_paths):
    context = _full_context(isolated_paths)
    insight = context.insights.create_insight_if_new(
        source_type="maintenance", source_id="task1", kind="overdue",
        title="Mower overdue", message="The mower is overdue.",
    )
    context.insights.resolve_insight(insight.insight_id)
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.system_signals == []


# ------------------------------------------------------------------
# Maintenance / Projects
# ------------------------------------------------------------------

def test_overdue_maintenance_count(isolated_paths):
    context = _full_context(isolated_paths)
    asset = context.maintenance.add_asset("Mower", category="Garage")
    context.maintenance.add_task(
        asset.asset_id, "Oil change", interval_days=30,
        last_completed=(TODAY - timedelta(days=45)).isoformat(), trigger_type="calendar",
    )
    context.maintenance.add_task(
        asset.asset_id, "Blade sharpening", interval_days=30,
        last_completed=TODAY.isoformat(), trigger_type="calendar",
    )
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.overdue_maintenance_count == 1


def test_active_project_count_excludes_complete(isolated_paths):
    context = _full_context(isolated_paths)
    context.projects.add_project("Greenhouse build", status="Active")
    context.projects.add_project("Old shed teardown", status="Complete")
    snapshot = assemble_life_state(context, "p1", TODAY)
    assert snapshot.active_project_count == 1


# ------------------------------------------------------------------
# format_life_state_summary
# ------------------------------------------------------------------

def test_format_life_state_summary_empty_snapshot_still_returns_real_text():
    from core.context_assembler import LifeStateSnapshot
    summary = format_life_state_summary(LifeStateSnapshot(profile_id="p1"))
    assert "Nothing notable" in summary


def test_format_life_state_summary_includes_every_populated_section():
    from core.context_assembler import LifeStateSnapshot
    snapshot = LifeStateSnapshot(
        profile_id="p1",
        active_mission_count=3,
        recurring_streaks=[("Laundry", 4)],
        skills_growing=["Cooking"],
        skills_declining=["Fitness"],
        skills_dormant=["Maker"],
        system_signals=["A real observation."],
        overdue_maintenance_count=2,
        active_project_count=1,
    )
    summary = format_life_state_summary(snapshot)
    assert "3 active mission" in summary
    assert "Laundry (4)" in summary
    assert "Cooking" in summary
    assert "Fitness" in summary
    assert "Maker" in summary
    assert "2 maintenance item" in summary
    assert "1 active project" in summary
    assert "A real observation." in summary


# ------------------------------------------------------------------
# format_life_state_glance_line
# ------------------------------------------------------------------

def test_format_life_state_glance_line_all_quiet():
    from core.context_assembler import LifeStateSnapshot
    assert format_life_state_glance_line(LifeStateSnapshot(profile_id="p1")) == "All quiet"


def test_format_life_state_glance_line_singular_mission():
    from core.context_assembler import LifeStateSnapshot
    snapshot = LifeStateSnapshot(profile_id="p1", active_mission_count=1)
    assert format_life_state_glance_line(snapshot) == "1 active mission"


def test_format_life_state_glance_line_combines_every_populated_count():
    from core.context_assembler import LifeStateSnapshot
    snapshot = LifeStateSnapshot(
        profile_id="p1",
        active_mission_count=3,
        skills_growing=["Cooking"],
        skills_declining=["Fitness", "Maker"],
        overdue_maintenance_count=1,
    )
    assert format_life_state_glance_line(snapshot) == "3 active missions · 1 growing · 2 declining · 1 overdue item"


def test_format_life_state_glance_line_ignores_dormant_and_streaks():
    """Dormant interests and streaks are real signals in the full
    summary but deliberately left out of the compact glance line —
    there's only room for the handful that matter most at a glance."""
    from core.context_assembler import LifeStateSnapshot
    snapshot = LifeStateSnapshot(profile_id="p1", skills_dormant=["Maker"], recurring_streaks=[("Laundry", 4)])
    assert format_life_state_glance_line(snapshot) == "All quiet"
