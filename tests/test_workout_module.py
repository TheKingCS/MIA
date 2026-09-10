"""
tests.test_workout_module
============================

Unit tests for modules.workout.module's pure formatters — no Qt event
loop needed, same shape as tests/test_kitchen_module.py.
format_elapsed()'s own tests mirror tests/test_stopwatch_format.py's
exact shape (a deliberately-duplicated, independently-owned copy — see
module docstring for why).
"""

from __future__ import annotations

import pytest

from core.workout_manager import Exercise, WorkoutSession, WorkoutTemplate
from modules.workout.module import (
    format_elapsed,
    format_exercise_row,
    format_session_row,
    format_template_row,
)


def test_format_elapsed_zero():
    assert format_elapsed(0) == "00:00"


def test_format_elapsed_seconds():
    assert format_elapsed(5_000) == "00:05"


def test_format_elapsed_minutes_seconds():
    assert format_elapsed(65_000) == "01:05"


def test_format_elapsed_under_an_hour_has_no_hours_component():
    assert format_elapsed(59 * 60_000 + 59_000) == "59:59"


def test_format_elapsed_exactly_one_hour_switches_to_hh_mm_ss():
    assert format_elapsed(60 * 60_000) == "01:00:00"


def test_format_elapsed_hours_minutes_seconds():
    total_ms = (2 * 3600 + 3 * 60 + 4) * 1000
    assert format_elapsed(total_ms) == "02:03:04"


def test_format_elapsed_negative_raises():
    with pytest.raises(ValueError):
        format_elapsed(-1)


def test_format_exercise_row_includes_name_category():
    exercise = Exercise(exercise_id="e1", name="Barbell Squat", category="Legs")
    assert format_exercise_row(exercise) == "Barbell Squat   [Legs]"


def test_format_exercise_row_includes_equipment_when_set():
    exercise = Exercise(exercise_id="e1", name="Barbell Squat", category="Legs", equipment="Barbell")
    assert format_exercise_row(exercise) == "Barbell Squat   [Legs]  (Barbell)"


def test_format_template_row_singular_exercise():
    template = WorkoutTemplate(template_id="t1", name="Legs", exercises=[{"exercise_id": "e1"}])
    assert format_template_row(template) == "Legs   (1 exercise)"


def test_format_template_row_plural_exercises():
    template = WorkoutTemplate(template_id="t1", name="Legs", exercises=[{"exercise_id": "e1"}, {"exercise_id": "e2"}])
    assert format_template_row(template) == "Legs   (2 exercises)"


def test_format_template_row_zero_exercises():
    template = WorkoutTemplate(template_id="t1", name="Legs", exercises=[])
    assert format_template_row(template) == "Legs   (0 exercises)"


def test_format_session_row_includes_date_template_duration_sets():
    session = WorkoutSession(session_id="s1", date="2026-09-10", duration_minutes=45.0, sets_logged=[{}, {}])
    assert format_session_row(session, "Push Day") == "2026-09-10   Push Day   45 min   2 sets"


def test_format_session_row_singular_set():
    session = WorkoutSession(session_id="s1", date="2026-09-10", duration_minutes=10.0, sets_logged=[{}])
    assert format_session_row(session, "Freeform") == "2026-09-10   Freeform   10 min   1 set"
