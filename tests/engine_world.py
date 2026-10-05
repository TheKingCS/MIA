"""
tests.engine_world
====================

A small, real MIA world for the Engine Phase 1 tests (life events,
relationships, Life State v2, the state export): real stores in a temp
folder, a household folder and each person's own, placeholder names
only. `build_world(tmp_path, monkeypatch)` returns the context.
"""

from __future__ import annotations

import time

import core.calendar_manager as calendar_module
import core.config_manager as config_module
import core.mission_manager as mission_module
import core.profile_manager as profile_module
import core.recurring_mission_manager as recurring_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.intent_manager import IntentManager
from core.kitchen_manager import KitchenManager
from core.life_events import LifeEventLog, PersonalLifeEventLog
from core.maintenance_manager import MaintenanceManager
from core.mission_manager import MissionManager
from core.profile_manager import ProfileManager
from core.project_manager import ProjectManager
from core.real_estate_manager import RealEstateManager
from core.recurring_mission_manager import RecurringMissionManager
from core.skill_manager import SkillManager
from core.task_manager import TaskManager
from core.undo_log import UndoLog
from core.workout_manager import WorkoutManager


def build_world(tmp_path, monkeypatch) -> AppContext:
    home = tmp_path / "household"
    device = tmp_path / "device"
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    for module, files in ((mission_module, ("_MISSIONS_FILE",)), (recurring_module, ("_TEMPLATES_FILE",)),
                          (calendar_module, ("_EVENTS_FILE",))):
        monkeypatch.setattr(module, "_DATA_DIR", device)
        for name in files:
            monkeypatch.setattr(module, name, device / getattr(module, name).name)
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.me = context.profiles.create_profile("Robin", make_active=True)
    time.sleep(0.01)
    context.other = context.profiles.create_profile("Sam", make_active=False)
    mine = tmp_path / "profiles" / context.me.profile_id
    context.undo = UndoLog()
    context.missions = MissionManager(context)
    context.recurring_missions = RecurringMissionManager(context)
    context.calendar = CalendarManager(context)
    context.skills = SkillManager(context)
    context.budget = BudgetManager(context, data_dir=home)
    context.maintenance = MaintenanceManager(context, data_dir=home)
    context.tasks = TaskManager(context, data_dir=home)
    context.projects = ProjectManager(context, data_dir=home)
    context.real_estate = RealEstateManager(context, data_dir=home)
    context.kitchen = KitchenManager(context, data_dir=home)
    context.workout = WorkoutManager(context, data_dir=mine)
    context.intents = IntentManager(context, data_dir=mine)
    context.life_events = LifeEventLog(context, data_dir=home)
    context.personal_life_events = PersonalLifeEventLog(context, data_dir=mine)
    context.home_dir, context.my_dir, context.device_dir = home, mine, device
    return context
