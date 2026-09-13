"""
tests.test_recurring_mission_manager
=======================================

Unit tests for core.recurring_mission_manager. Isolates
_DATA_DIR/_MISSIONS_FILE/_TEMPLATES_FILE plus core.calendar_manager's
own file constants (ensure_current_missions() creates a real
CalendarEvent) into a tmp_path scratch area, same monkeypatch pattern
as tests/test_pathway_manager.py.
"""

from __future__ import annotations

from datetime import date

import pytest

import core.calendar_manager as calendar_manager_module
import core.mission_manager as mission_manager_module
import core.recurring_mission_manager as recurring_mission_manager_module
from core.app_context import AppContext
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.gamification import SkillWeight
from core.mission_manager import MissionManager
from core.recurring_mission_manager import (
    RecurringMissionManager,
    current_streak_for,
    current_target_for,
    current_weekly_streak_for,
    week_index_for,
    week_key_for,
)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(mission_manager_module, "_MISSIONS_FILE", data_dir / "missions.json")
    monkeypatch.setattr(recurring_mission_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(recurring_mission_manager_module, "_TEMPLATES_FILE", data_dir / "recurring_mission_templates.json")
    monkeypatch.setattr(calendar_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(calendar_manager_module, "_EVENTS_FILE", data_dir / "calendar_events.json")


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.missions = MissionManager(context)
    context.calendar = CalendarManager(context)
    context.recurring_missions = RecurringMissionManager(context)
    return context


# ----------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------

def test_week_index_for_same_day_is_week_zero():
    assert week_index_for(date(2026, 9, 13), date(2026, 9, 13)) == 0


def test_week_index_for_advances_every_seven_days():
    start = date(2026, 9, 13)
    assert week_index_for(start, date(2026, 9, 19)) == 0
    assert week_index_for(start, date(2026, 9, 20)) == 1
    assert week_index_for(start, date(2026, 9, 27)) == 2


def test_week_index_for_never_negative():
    assert week_index_for(date(2026, 9, 13), date(2026, 9, 1)) == 0


def test_current_target_for_escalates_weekly():
    template = RecurringMissionManagerTestTemplate(base_target=20, target_increment_per_week=5, start_date="2026-09-13")
    assert current_target_for(template, date(2026, 9, 13)) == 20
    assert current_target_for(template, date(2026, 9, 20)) == 25
    assert current_target_for(template, date(2026, 9, 27)) == 30


def test_week_key_for_is_stable_and_distinct_per_week():
    start = date(2026, 9, 13)
    assert week_key_for(start, 0) == "2026-09-13-W0"
    assert week_key_for(start, 1) == "2026-09-13-W1"


def test_current_streak_for_counts_consecutive_days_ending_today():
    dates = ["2026-09-11", "2026-09-12", "2026-09-13"]
    assert current_streak_for(dates, date(2026, 9, 13)) == 3


def test_current_streak_for_counts_from_yesterday_if_today_not_done_yet():
    dates = ["2026-09-11", "2026-09-12"]
    assert current_streak_for(dates, date(2026, 9, 13)) == 2


def test_current_streak_for_resets_across_a_gap():
    dates = ["2026-09-01", "2026-09-11", "2026-09-12", "2026-09-13"]
    assert current_streak_for(dates, date(2026, 9, 13)) == 3


def test_current_streak_for_zero_when_nothing_recent():
    assert current_streak_for(["2026-08-01"], date(2026, 9, 13)) == 0


def test_current_streak_for_empty_list():
    assert current_streak_for([], date(2026, 9, 13)) == 0


def test_current_weekly_streak_for_counts_consecutive_weeks_ending_current():
    assert current_weekly_streak_for([0, 1, 2], 2) == 3


def test_current_weekly_streak_for_counts_from_previous_week_if_current_not_done_yet():
    assert current_weekly_streak_for([0, 1], 2) == 2


def test_current_weekly_streak_for_resets_across_a_skipped_week():
    assert current_weekly_streak_for([0, 2], 2) == 1


def test_current_weekly_streak_for_empty_list():
    assert current_weekly_streak_for([], 0) == 0


class RecurringMissionManagerTestTemplate:
    """Minimal duck-typed stand-in for RecurringMissionTemplate — only
    current_target_for()'s own three fields are needed for the pure
    helper tests above."""

    def __init__(self, base_target, target_increment_per_week, start_date):
        self.base_target = base_target
        self.target_increment_per_week = target_increment_per_week
        self.start_date = start_date


# ----------------------------------------------------------------------
# RecurringMissionManager — real behavior
# ----------------------------------------------------------------------

def test_ensure_current_missions_creates_daily_and_weekly(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Push-ups",
        objective_description_template="Do {target:g} push-ups",
        base_target=20,
        target_increment_per_week=5,
        daily_reward_xp=10,
        weekly_bonus_reward_xp=15,
        start_date="2026-09-13",
        daily_skill_rewards=[SkillWeight("calisthenics", 15)],
        weekly_bonus_skill_rewards=[SkillWeight("calisthenics", 10)],
    )

    daily, weekly = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))

    assert daily.recurring_kind == "daily"
    assert daily.occurrence_key == "2026-09-13"
    assert daily.objectives[0].target == 20
    assert daily.objectives[0].description == "Do 20 push-ups"
    assert weekly.recurring_kind == "weekly"
    assert weekly.occurrence_key == "2026-09-13-W0"
    assert weekly.objectives[0].target == 7

    assert len(context.calendar.all_events()) == 1
    assert context.calendar.all_events()[0].date == "2026-09-13"


def test_ensure_current_missions_is_idempotent(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Push-ups", objective_description_template="Do {target:g} push-ups",
        base_target=20, target_increment_per_week=5, daily_reward_xp=10, weekly_bonus_reward_xp=15,
        start_date="2026-09-13",
    )

    daily1, weekly1 = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))
    daily2, weekly2 = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))

    assert daily1.mission_id == daily2.mission_id
    assert weekly1.mission_id == weekly2.mission_id
    assert len(context.missions.all_missions()) == 2  # not 4
    assert len(context.calendar.all_events()) == 1  # not 2


def test_completing_daily_mission_increments_weekly_tally(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Push-ups", objective_description_template="Do {target:g} push-ups",
        base_target=20, target_increment_per_week=5, daily_reward_xp=10, weekly_bonus_reward_xp=15,
        start_date="2026-09-13",
    )
    daily, weekly = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))

    context.missions.update_mission(daily.mission_id, status="completed")

    weekly = context.missions.get_mission(weekly.mission_id)
    assert weekly.objectives[0].progress == 1
    assert weekly.status == "active"  # not yet 7


def test_completing_all_seven_days_completes_the_weekly_bonus(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Push-ups", objective_description_template="Do {target:g} push-ups",
        base_target=20, target_increment_per_week=5, daily_reward_xp=10, weekly_bonus_reward_xp=15,
        weekly_bonus_skill_rewards=[SkillWeight("calisthenics", 10)],
        start_date="2026-09-13",
    )
    weekly_mission_id = None
    for day in range(13, 20):  # 2026-09-13 .. 2026-09-19, one real week
        today = date(2026, 9, day)
        daily, weekly = context.recurring_missions.ensure_current_missions(template, today)
        weekly_mission_id = weekly.mission_id
        context.missions.update_mission(daily.mission_id, status="completed")

    weekly = context.missions.get_mission(weekly_mission_id)
    assert weekly.objectives[0].progress == 7
    assert weekly.status == "completed"
    assert weekly.rewards_credited is True


def test_current_streak_for_template_reflects_real_completions(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Push-ups", objective_description_template="Do {target:g} push-ups",
        base_target=20, target_increment_per_week=5, daily_reward_xp=10, weekly_bonus_reward_xp=15,
        start_date="2026-09-13",
    )
    daily, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))
    context.missions.update_mission(daily.mission_id, status="completed")

    assert context.recurring_missions.current_streak_for_template(template.template_id, date(2026, 9, 13)) == 1


# ----------------------------------------------------------------------
# "weekly" recurrence (laundry's own shape — one Mission per week, no
# daily sub-occurrence)
# ----------------------------------------------------------------------

def test_ensure_current_missions_weekly_creates_one_mission_no_daily_bonus(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Laundry", objective_description_template="Do {target:g} loads of laundry",
        base_target=3, target_increment_per_week=0, daily_reward_xp=10, weekly_bonus_reward_xp=0,
        start_date="2026-09-13", recurrence="weekly", category="Household",
    )

    mission, weekly = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))

    assert weekly is None
    assert mission.recurring_kind == "weekly_standalone"
    assert mission.occurrence_key == "2026-09-13-W0"
    assert mission.objectives[0].target == 3
    assert mission.objectives[0].description == "Do 3 loads of laundry"
    assert len(context.missions.all_missions()) == 1  # not 2 — no daily bonus Mission
    assert len(context.calendar.all_events()) == 1


def test_ensure_current_missions_weekly_is_idempotent_within_the_week(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Laundry", objective_description_template="Do {target:g} loads of laundry",
        base_target=3, target_increment_per_week=0, daily_reward_xp=10, weekly_bonus_reward_xp=0,
        start_date="2026-09-13", recurrence="weekly", category="Household",
    )

    mission1, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))
    mission2, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 16))

    assert mission1.mission_id == mission2.mission_id
    assert len(context.missions.all_missions()) == 1
    assert len(context.calendar.all_events()) == 1


def test_ensure_current_missions_weekly_creates_a_new_mission_next_week(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Laundry", objective_description_template="Do {target:g} loads of laundry",
        base_target=3, target_increment_per_week=0, daily_reward_xp=10, weekly_bonus_reward_xp=0,
        start_date="2026-09-13", recurrence="weekly", category="Household",
    )

    week0, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))
    week1, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 20))

    assert week0.mission_id != week1.mission_id
    assert week1.occurrence_key == "2026-09-13-W1"
    assert len(context.missions.all_missions()) == 2


def test_current_streak_for_template_weekly_counts_consecutive_completed_weeks(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Laundry", objective_description_template="Do {target:g} loads of laundry",
        base_target=3, target_increment_per_week=0, daily_reward_xp=10, weekly_bonus_reward_xp=0,
        start_date="2026-09-13", recurrence="weekly", category="Household",
    )

    week0, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))
    context.missions.update_mission(week0.mission_id, status="completed")
    week1, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 20))
    context.missions.update_mission(week1.mission_id, status="completed")

    assert context.recurring_missions.current_streak_for_template(template.template_id, date(2026, 9, 20)) == 2


def test_current_streak_for_template_weekly_resets_across_a_skipped_week(isolated_paths):
    context = _make_context()
    template = context.recurring_missions.add_template(
        name="Laundry", objective_description_template="Do {target:g} loads of laundry",
        base_target=3, target_increment_per_week=0, daily_reward_xp=10, weekly_bonus_reward_xp=0,
        start_date="2026-09-13", recurrence="weekly", category="Household",
    )

    week0, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))
    context.missions.update_mission(week0.mission_id, status="completed")
    # Week 1 (2026-09-20) skipped entirely — jump straight to week 2.
    week2, _ = context.recurring_missions.ensure_current_missions(template, date(2026, 9, 27))
    context.missions.update_mission(week2.mission_id, status="completed")

    assert context.recurring_missions.current_streak_for_template(template.template_id, date(2026, 9, 27)) == 1


def test_ensure_current_missions_without_calendar_does_not_crash(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.missions = MissionManager(context)
    context.recurring_missions = RecurringMissionManager(context)  # context.calendar left None
    template = context.recurring_missions.add_template(
        name="Push-ups", objective_description_template="Do {target:g} push-ups",
        base_target=20, target_increment_per_week=5, daily_reward_xp=10, weekly_bonus_reward_xp=15,
        start_date="2026-09-13",
    )
    context.recurring_missions.ensure_current_missions(template, date(2026, 9, 13))  # should not raise
