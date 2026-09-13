"""
tests.test_household_module
==============================

Unit tests for modules.household.module's pure functions, same style
as tests/test_greenhouse_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.mission_manager import Mission, Objective
from core.recurring_mission_manager import RecurringMissionTemplate
from modules.household.module import format_checklist_line, household_progress, is_household_template


def _template(recurrence="daily", category="Household"):
    return RecurringMissionTemplate(
        template_id="t1",
        name="Laundry",
        objective_description_template="Do {target:g} loads of laundry",
        base_target=3,
        target_increment_per_week=0,
        daily_reward_xp=10,
        weekly_bonus_reward_xp=0,
        start_date="2026-09-13",
        recurrence=recurrence,
        category=category,
    )


def _mission(status="active", progress=1.0, target=3.0):
    mission = Mission(mission_id="m1", name="Laundry — Week 1", icon="\U0001F9FA", summary="", status=status)
    mission.objectives.append(Objective(description="Do 3 loads of laundry", metric_type="tally", target=target, progress=progress))
    return mission


# ----------------------------------------------------------------------
# is_household_template
# ----------------------------------------------------------------------

def test_is_household_template_true_for_household_category():
    assert is_household_template(_template(category="Household")) is True


def test_is_household_template_false_for_other_categories():
    assert is_household_template(_template(category="Fitness")) is False


# ----------------------------------------------------------------------
# format_checklist_line
# ----------------------------------------------------------------------

def test_format_checklist_line_shows_progress_and_streak():
    line = format_checklist_line(_template(recurrence="weekly"), _mission(progress=2.0), streak=3)
    assert line == "• Laundry — 2/3 — 3-week streak"


def test_format_checklist_line_marks_completed():
    line = format_checklist_line(_template(recurrence="weekly"), _mission(status="completed", progress=3.0), streak=1)
    assert line == "✓ Laundry — 3/3 — 1-week streak"


def test_format_checklist_line_daily_uses_day_unit():
    line = format_checklist_line(_template(recurrence="daily"), _mission(progress=1.0, target=1.0), streak=0)
    assert line == "• Laundry — 1/1 — new streak starting"


def test_format_checklist_line_no_mission_falls_back_to_name_and_streak():
    line = format_checklist_line(_template(recurrence="weekly"), None, streak=2)
    assert line == "Laundry — 2-week streak"


# ----------------------------------------------------------------------
# household_progress
# ----------------------------------------------------------------------

def test_household_progress_counts_completed_missions():
    missions = [_mission(status="completed"), _mission(status="active"), _mission(status="completed")]
    assert household_progress(missions) == (2, 3)


def test_household_progress_empty_list():
    assert household_progress([]) == (0, 0)


def test_household_progress_treats_none_as_not_completed():
    assert household_progress([None, _mission(status="completed")]) == (1, 2)
