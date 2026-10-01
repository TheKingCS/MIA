"""
Starter sets (core/starter_templates.py), 2026-10-01: the usual chores,
routines, upkeep schedules and a workout for a kind of life, added in one
undoable step, never twice.
"""

from datetime import date
from types import SimpleNamespace

import pytest

import core.calendar_manager as calendar_module
import core.config_manager as config_module
import core.mission_manager as mission_module
import core.profile_manager as profile_module
import core.recurring_mission_manager as recurring_module
from core import starter_templates
from core.app_context import AppContext
from core.assistant_starter_actions import _action_add_starter_set, _action_list_starter_sets
from core.calendar_manager import CalendarManager
from core.child_accounts import make_child
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceManager, days_until_due
from core.mission_manager import MissionManager
from core.profile_manager import ProfileManager
from core.recurring_mission_manager import RecurringMissionManager
from core.starter_templates import STARTERS, Routine, Upkeep, Workout, for_goals
from core.undo_log import UndoLog, undo_last
from core.workout_manager import WorkoutManager

TODAY = date(2026, 10, 1)


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setattr(mission_module, "_DATA_DIR", data)
    monkeypatch.setattr(mission_module, "_MISSIONS_FILE", data / "missions.json")
    monkeypatch.setattr(recurring_module, "_DATA_DIR", data)
    monkeypatch.setattr(recurring_module, "_TEMPLATES_FILE", data / "recurring_mission_templates.json")
    monkeypatch.setattr(calendar_module, "_DATA_DIR", data)
    monkeypatch.setattr(calendar_module, "_EVENTS_FILE", data / "calendar_events.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.me = context.profiles.create_profile("Robin")
    context.undo = UndoLog()
    context.missions = MissionManager(context)
    context.calendar = CalendarManager(context)
    context.recurring_missions = RecurringMissionManager(context)
    context.maintenance = MaintenanceManager(context, data_dir=data)
    context.workout = WorkoutManager(context, data_dir=data)
    return context


def test_every_set_is_well_formed():
    for starter in STARTERS.values():
        assert starter.parts and len({p.part_id for p in starter.parts}) == len(starter.parts)
        for part in starter.parts:
            for item in part.items:
                if isinstance(item, Routine):
                    assert item.recurrence in ("daily", "weekly") and "{target:g}" in item.objective
                    item.objective.format(target=item.target)
                elif isinstance(item, Upkeep):
                    assert all(days > 0 for _title, days in item.tasks)
                else:
                    assert isinstance(item, Workout) and item.exercises


def test_goals_suggest_sets_and_names_find_them():
    assert for_goals(["school", "health", "money", "school"]) == ["student", "fitness"]
    assert starter_templates.find("Home & Family").starter_id == "home_family"
    assert starter_templates.find("homestead").starter_id == "homestead"
    assert starter_templates.find("fit").starter_id == "fitness"
    assert starter_templates.find("spaceship") is None and starter_templates.find("") is None
    assert "Test the well water".lower() in starter_templates.describe(STARTERS["homestead"])


def test_homestead_adds_routines_and_upkeep_counted_from_today(ctx):
    result = starter_templates.apply(ctx, "homestead", ["chores", "water"], TODAY)
    assert "Animal chores" in result.added and "Test the well water" in result.added
    assert {t.name for t in ctx.recurring_missions.all_templates()} == {"Animal chores", "Garden check",
                                                                         "Walk the property"}
    well = next(a for a in ctx.maintenance.all_assets() if a.name == "Well and water")
    tasks = [t for t in ctx.maintenance.all_tasks() if t.asset_id == well.asset_id]
    assert {t.title for t in tasks} == {"Test the well water", "Check the pressure tank"}
    assert all(days_until_due(t, TODAY) > 0 for t in tasks)  # nothing starts out overdue
    assert not any(a.name == "Generator" for a in ctx.maintenance.all_assets())  # left out


def test_adding_again_adds_nothing_twice(ctx):
    starter_templates.apply(ctx, "home_family", today=TODAY)
    before = (len(ctx.recurring_missions.all_templates()), len(ctx.maintenance.all_tasks()))
    again = starter_templates.apply(ctx, "home_family", today=TODAY)
    assert again.added == [] and again.describe() == "Everything in that set is already here."
    # Homestead shares the house upkeep: only its own new things are added.
    homestead = starter_templates.apply(ctx, "homestead", ["house", "fences"], TODAY)
    assert homestead.added == ["Walk and fix the fences"] and "Clean the dryer vent" in homestead.already
    assert (len(ctx.recurring_missions.all_templates()), len(ctx.maintenance.all_tasks())) == (before[0], before[1] + 1)


def test_fitness_builds_a_workout_reusing_exercises(ctx):
    ctx.workout.add_exercise("Push-ups", "Chest")
    starter_templates.apply(ctx, "fitness", today=TODAY)
    template = next(t for t in ctx.workout.all_templates() if t.name == "Beginner full body")
    assert len(template.exercises) == 5
    assert sum(1 for e in ctx.workout.all_exercises() if e.name == "Push-ups") == 1
    move = next(t for t in ctx.recurring_missions.all_templates() if t.name == "Move")
    assert move.category == "Fitness"  # shows in the Workouts app


def test_one_undo_takes_the_whole_set_back(ctx):
    starter_templates.apply(ctx, "home_family", today=TODAY)
    assert ctx.recurring_missions.all_templates() and ctx.maintenance.all_assets()
    change = undo_last(ctx, ctx.me.profile_id)
    assert change.label == "starter_home_family"
    assert ctx.recurring_missions.all_templates() == [] and ctx.maintenance.all_assets() == []


def test_a_child_gets_routines_but_not_house_upkeep(ctx):
    kid = ctx.profiles.create_profile("Ari")
    make_child(ctx, kid.profile_id, [ctx.me.profile_id])
    ctx.profiles.set_active_profile(kid.profile_id)
    result = starter_templates.apply(ctx, "home_family", today=TODAY)
    assert "Dishes" in result.added and ctx.maintenance.all_assets() == []
    assert result.unavailable == ["House upkeep (alarms, filters, dryer vent...)"]


def test_missing_stores_are_left_out_not_crashed():
    bare = SimpleNamespace(config=None, recurring_missions=None, maintenance=None, workout=None)
    result = starter_templates.apply(bare, "fitness", today=TODAY)
    assert result.added == [] and len(result.unavailable) == 2
    with pytest.raises(ValueError):
        starter_templates.apply(bare, "nope")


def test_the_assistant_lists_and_adds_with_parts_left_out(ctx):
    assert "Homestead" in _action_list_starter_sets(ctx, {})
    assert "Beginner full body" in _action_list_starter_sets(ctx, {"name": "fitness"})
    reply = _action_add_starter_set(ctx, {"name": "homestead", "leave_out": "well and generator"})
    assert reply.startswith("Homestead starter set: Added") and "undo that" in reply
    names = {a.name for a in ctx.maintenance.all_assets()}
    assert "Fences" in names and "Well and water" not in names and "Generator" not in names
    assert _action_add_starter_set(ctx, {"name": "spaceship"}).startswith("Which starter set?")


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_the_dialog_adds_only_ticked_parts(ctx, qapp):
    from gui.starter_dialog import StarterDialog

    dialog = StarterDialog(ctx, starter_id="homestead")
    assert set(dialog.part_checks) == {"chores", "house", "water", "power", "fences"}
    for part_id in ("chores", "house", "water", "fences"):
        dialog.part_checks[part_id].setChecked(False)
    dialog.add_button.click()
    assert [a.name for a in ctx.maintenance.all_assets()] == ["Generator"]
    assert "Added 2" in dialog.message_label.text()
    dialog.part_checks["power"].setChecked(False)
    dialog.add_button.click()
    assert dialog.message_label.text() == "Tick at least one part."


def test_setup_questions_offer_the_matching_sets(ctx, qapp):
    from gui.onboarding_dialog import OnboardingDialog

    dialog = OnboardingDialog(ctx, ctx.me, {})
    dialog._goal_buttons["home"].setChecked(True)
    dialog._goal_buttons["health"].setChecked(True)
    dialog.next_button.click()
    dialog.next_button.click()
    dialog.next_button.click()
    assert set(dialog.starter_checks) == {"home_family", "fitness"}
    dialog.starter_checks["fitness"].setChecked(False)
    dialog.next_button.click()  # "Sounds good"
    assert any(t.name == "Dishes" for t in ctx.recurring_missions.all_templates())
    assert ctx.workout.all_templates() == []
