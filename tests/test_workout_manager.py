"""
tests.test_workout_manager
=============================

Unit tests for core.workout_manager. Isolates _DATA_DIR/the three
per-record-type file constants into a tmp_path scratch area, same
monkeypatch pattern as test_kitchen_manager.py's isolated_paths.
"""

from __future__ import annotations

import pytest

import core.config_manager as config_manager_module
import core.workout_manager as workout_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager
from core.workout_manager import (
    WorkoutManager,
    WorkoutSession,
    personal_record,
    weight_progression,
)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(workout_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(workout_manager_module, "_EXERCISES_FILE", data_dir / "workout_exercises.json")
    monkeypatch.setattr(workout_manager_module, "_TEMPLATES_FILE", data_dir / "workout_templates.json")
    monkeypatch.setattr(workout_manager_module, "_SESSIONS_FILE", data_dir / "workout_sessions.json")
    # Not needed by any pre-existing test here (WorkoutManager never
    # touches context.config), but real once a test constructs a real
    # ProfileManager too (2026-09-11 gamification hook tests below) —
    # without this, that would write to the actual config/config.json.
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    return data_dir


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


def _make_manager(context: AppContext) -> WorkoutManager:
    manager = WorkoutManager(context)
    context.workout = manager
    return manager


def _session(session_id="s1", date="2026-09-10", sets_logged=None) -> WorkoutSession:
    return WorkoutSession(session_id=session_id, date=date, sets_logged=sets_logged or [])


# ------------------------------------------------------------------
# Exercise CRUD
# ------------------------------------------------------------------

def test_add_exercise_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_exercise(name="Barbell Squat", category="Legs", equipment="Barbell")

    reloaded = WorkoutManager(context)
    exercises = reloaded.all_exercises()
    assert len(exercises) == 1
    assert exercises[0].name == "Barbell Squat"
    assert exercises[0].equipment == "Barbell"


def test_add_exercise_rejects_unknown_category(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    exercise = manager.add_exercise(name="X", category="Nonsense")
    assert exercise.category == "Other"


def test_update_exercise_changes_fields(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    exercise = manager.add_exercise(name="X")
    manager.update_exercise(exercise.exercise_id, name="Y", category="Back")
    updated = manager.get_exercise(exercise.exercise_id)
    assert updated.name == "Y"
    assert updated.category == "Back"


def test_delete_exercise_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    exercise = manager.add_exercise(name="X")
    manager.delete_exercise(exercise.exercise_id)
    assert manager.get_exercise(exercise.exercise_id) is None


# ------------------------------------------------------------------
# Template CRUD + template exercises
# ------------------------------------------------------------------

def test_add_template_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_template(name="Push Day")

    reloaded = WorkoutManager(context)
    templates = reloaded.all_templates()
    assert len(templates) == 1
    assert templates[0].name == "Push Day"


def test_update_template_changes_fields(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    template = manager.add_template(name="X")
    manager.update_template(template.template_id, name="Y")
    assert manager.get_template(template.template_id).name == "Y"


def test_delete_template_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    template = manager.add_template(name="X")
    manager.delete_template(template.template_id)
    assert manager.get_template(template.template_id) is None


def test_add_exercise_to_template_appends(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    exercise = manager.add_exercise(name="Squat")
    template = manager.add_template(name="Legs")
    manager.add_exercise_to_template(template.template_id, exercise.exercise_id, target_sets=3, target_reps=5, target_weight=225.0)
    updated = manager.get_template(template.template_id)
    assert updated.exercises == [{"exercise_id": exercise.exercise_id, "target_sets": 3, "target_reps": 5, "target_weight": 225.0}]


def test_remove_exercise_from_template_by_index(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    squat = manager.add_exercise(name="Squat")
    bench = manager.add_exercise(name="Bench")
    template = manager.add_template(name="X")
    manager.add_exercise_to_template(template.template_id, squat.exercise_id)
    manager.add_exercise_to_template(template.template_id, bench.exercise_id)
    manager.remove_exercise_from_template(template.template_id, 0)
    updated = manager.get_template(template.template_id)
    assert len(updated.exercises) == 1
    assert updated.exercises[0]["exercise_id"] == bench.exercise_id


def test_remove_exercise_from_template_out_of_range_is_a_no_op(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    exercise = manager.add_exercise(name="Squat")
    template = manager.add_template(name="X")
    manager.add_exercise_to_template(template.template_id, exercise.exercise_id)
    manager.remove_exercise_from_template(template.template_id, 5)
    assert len(manager.get_template(template.template_id).exercises) == 1


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

def test_add_session_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_session(date_str="2026-09-10", duration_minutes=45.0, sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 225.0}])

    reloaded = WorkoutManager(context)
    sessions = reloaded.all_sessions()
    assert len(sessions) == 1
    assert sessions[0].duration_minutes == 45.0
    assert sessions[0].sets_logged == [{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 225.0}]


def test_add_session_defaults_to_today(isolated_paths):
    from datetime import date
    context = _make_context()
    manager = _make_manager(context)
    session = manager.add_session()
    assert session.date == date.today().isoformat()


def test_add_session_clamps_negative_duration(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    session = manager.add_session(duration_minutes=-5.0)
    assert session.duration_minutes == 0.0


def test_add_session_grants_xp_to_the_active_profile(isolated_paths):
    """2026-09-11 gamification pass — finishing a session is a real,
    one-time completion moment (see core.workout_manager's own
    docstring on the live in-memory state machine)."""
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)
    profile = context.profiles.create_profile(name="Alex", make_active=True)

    manager.add_session()

    assert context.profiles.get_active_profile().total_xp == 10
    assert profile.profile_id == context.profiles.get_active_profile().profile_id


def test_add_session_grants_xp_with_no_active_profile_does_not_raise(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)  # constructed, but no profile created/active
    manager.add_session()  # must not raise


def test_all_sessions_sorted_newest_first(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_session(date_str="2026-01-01")
    manager.add_session(date_str="2026-09-01")
    dates = [s.date for s in manager.all_sessions()]
    assert dates == ["2026-09-01", "2026-01-01"]


def test_all_sessions_filters_by_date_range(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_session(date_str="2026-01-01")
    manager.add_session(date_str="2026-09-01")
    filtered = manager.all_sessions(start_date="2026-06-01")
    assert len(filtered) == 1
    assert filtered[0].date == "2026-09-01"


def test_delete_session_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    session = manager.add_session()
    manager.delete_session(session.session_id)
    assert manager.get_session(session.session_id) is None


def test_last_session_date_returns_most_recent(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_session(date_str="2026-01-01")
    manager.add_session(date_str="2026-09-01")
    assert manager.last_session_date() == "2026-09-01"


def test_last_session_date_none_when_no_sessions(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.last_session_date() is None


# ------------------------------------------------------------------
# personal_record / weight_progression — pure logic
# ------------------------------------------------------------------

def test_personal_record_none_when_never_logged():
    assert personal_record("e1", []) is None


def test_personal_record_picks_heaviest_weight():
    sessions = [
        _session(sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 185.0}]),
        _session(sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 225.0}]),
        _session(sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 205.0}]),
    ]
    pr = personal_record("e1", sessions)
    assert pr == {"weight": 225.0, "reps": 5, "date": "2026-09-10"}


def test_personal_record_ties_broken_by_higher_reps():
    sessions = [
        _session(sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 225.0}]),
        _session(sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 8, "weight": 225.0}]),
    ]
    pr = personal_record("e1", sessions)
    assert pr["reps"] == 8


def test_personal_record_ignores_other_exercises():
    sessions = [_session(sets_logged=[{"exercise_id": "e2", "set_number": 1, "reps": 5, "weight": 500.0}])]
    assert personal_record("e1", sessions) is None


def test_weight_progression_one_point_per_day_using_max():
    sessions = [
        _session(session_id="s1", date="2026-09-01", sets_logged=[
            {"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 185.0},
            {"exercise_id": "e1", "set_number": 2, "reps": 5, "weight": 205.0},
        ]),
        _session(session_id="s2", date="2026-09-05", sets_logged=[
            {"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 225.0},
        ]),
    ]
    assert weight_progression("e1", sessions) == [("2026-09-01", 205.0), ("2026-09-05", 225.0)]


def test_weight_progression_empty_when_never_logged():
    assert weight_progression("e1", []) == []


# ------------------------------------------------------------------
# personal_record_for / weight_progression_for — manager wrappers
# ------------------------------------------------------------------

def test_personal_record_for_uses_current_sessions(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_session(date_str="2026-09-10", sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 225.0}])
    pr = manager.personal_record_for("e1")
    assert pr == {"weight": 225.0, "reps": 5, "date": "2026-09-10"}


def test_weight_progression_for_uses_current_sessions(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_session(date_str="2026-09-10", sets_logged=[{"exercise_id": "e1", "set_number": 1, "reps": 5, "weight": 225.0}])
    assert manager.weight_progression_for("e1") == [("2026-09-10", 225.0)]
