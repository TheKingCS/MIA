"""
tests.test_missions_module
=============================

Unit tests for modules.missions.module's pure functions, same style as
tests/test_expeditions_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.mission_manager import Mission, Objective
from modules.missions.module import (
    format_checklist_label,
    format_group_progress_line,
    format_individual_contribution_line,
    format_level_footer_line,
    format_mission_row,
    format_objective_assignee_suffix,
    format_objective_row,
    format_objectives_heading,
    format_participants_line,
    format_recurring_status_line,
    format_rewards_line,
)


def test_format_mission_row_with_trip():
    mission = Mission(mission_id="m1", name="Master Angler", status="active")
    assert format_mission_row(mission, trip_name="Day 1") == "Master Angler  [Day 1]  (active)"


def test_format_mission_row_no_trip():
    mission = Mission(mission_id="m1", name="General Goal", status="completed")
    assert format_mission_row(mission) == "General Goal  (completed)"


def test_format_recurring_status_line_daily_with_streak():
    assert format_recurring_status_line("daily", 4) == "\U0001F525 4-day streak"


def test_format_recurring_status_line_daily_zero_streak():
    assert format_recurring_status_line("daily", 0) == "\U0001F525 New streak starting today"


def test_format_recurring_status_line_weekly():
    assert format_recurring_status_line("weekly", 0, weekly_progress=3) == "\U0001F3C6 3/7 days this week"


def test_format_recurring_status_line_unknown_kind():
    assert format_recurring_status_line("nonsense", 0) == ""


def test_format_objective_row_incomplete_tally():
    objective = Objective(description="Catch 3 fish", metric_type="tally", target=3.0, progress=1.0)
    assert format_objective_row(objective, progress=1.0, is_complete=False) == "[ ] Catch 3 fish: 1 of 3"


def test_format_objective_row_complete():
    objective = Objective(description="Catch 3 fish", metric_type="tally", target=3.0, progress=3.0)
    assert format_objective_row(objective, progress=3.0, is_complete=True) == "[x] Catch 3 fish: 3 of 3"


def test_format_objective_row_fractional_hours():
    objective = Objective(description="Spend 2 hours fishing", metric_type="trip_duration_hours", target=2.0)
    assert format_objective_row(objective, progress=1.5, is_complete=False) == "[ ] Spend 2 hours fishing: 1.5 of 2"


def test_format_rewards_line():
    assert format_rewards_line(25, 160) == "$25    160 XP"


def test_format_rewards_line_zero_rewards():
    assert format_rewards_line(0, 0) == "$0    0 XP"


def test_format_rewards_line_formats_large_numbers_with_commas():
    assert format_rewards_line(1500, 12000) == "$1,500    12,000 XP"


def test_format_level_footer_line():
    assert format_level_footer_line(6, 9143, 13886) == "Level 6    9,143 / 13,886"


def test_format_level_footer_line_omits_prestige_at_tier_zero():
    assert format_level_footer_line(6, 9143, 13886, 0) == "Level 6    9,143 / 13,886"


def test_format_level_footer_line_includes_prestige_once_earned():
    assert format_level_footer_line(1, 0, 100, 2) == "Level 1    0 / 100    PRESTIGE 2"


def test_format_objectives_heading_no_objectives():
    assert format_objectives_heading(0, 0) == "OBJECTIVES"


def test_format_objectives_heading_partial():
    assert format_objectives_heading(1, 2) == "OBJECTIVES — 1 of 2 complete"


def test_format_objectives_heading_all_complete():
    assert format_objectives_heading(2, 2) == "OBJECTIVES — 2 of 2 complete"


def test_format_checklist_label_single_step_target_omits_fraction():
    assert format_checklist_label("Complete the task", 0.0, 1.0, False) == "Complete the task"


def test_format_checklist_label_multi_step_incomplete_shows_fraction():
    assert format_checklist_label("Catch 3 fish", 1.0, 3.0, False) == "Catch 3 fish (1 of 3)"


def test_format_checklist_label_complete_omits_fraction_even_with_multi_step_target():
    assert format_checklist_label("Catch 3 fish", 3.0, 3.0, True) == "Catch 3 fish"


# ------------------------------------------------------------------
# Group quests (2026-09-14)
# ------------------------------------------------------------------

def test_format_objective_assignee_suffix_with_an_assignee():
    assert format_objective_assignee_suffix("Zac") == " — Zac"


def test_format_objective_assignee_suffix_shared_is_empty():
    assert format_objective_assignee_suffix(None) == ""


def test_format_participants_line():
    assert format_participants_line(["Zac", "Faith"]) == "Party: Zac, Faith"


def test_format_individual_contribution_line():
    assert format_individual_contribution_line(4, 7) == "Your Contribution: 4/7 objectives"


def test_format_group_progress_line():
    assert format_group_progress_line(5, 7) == "Household Progress: 5/7 objectives"
