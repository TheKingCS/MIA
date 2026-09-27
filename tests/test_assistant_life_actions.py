"""
tests.test_assistant_life_actions
===================================

Workout, people & pets, household routine, and Classroom Assistant tools
(core/assistant_life_actions.py) run through the real registry against
real managers on temp data, plus their pure parsers.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

import core.classroom_manager as classroom_module
import core.config_manager as config_module
import core.mission_manager as mission_module
import core.recurring_mission_manager as recurring_module
import core.relationships_manager as relationships_module
import core.skill_manager as skill_module
import core.workout_manager as workout_module
from core.app_context import AppContext
from core.assistant_life_actions import days_until, parse_birthday, parse_exercise_line, speak_birthday
from core.classroom_manager import ClassroomManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.mission_manager import MissionManager
from core.recurring_mission_manager import RecurringMissionManager
from core.relationships_manager import RelationshipsManager
from core.workout_manager import WorkoutManager
from tests.assistant_registry import build_desktop_registry

_MODULES = [classroom_module, mission_module, recurring_module, relationships_module, skill_module, workout_module]


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    for module in _MODULES:
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.missions = MissionManager(context)
    context.recurring_missions = RecurringMissionManager(context)
    context.workout = WorkoutManager(context)
    context.relationships = RelationshipsManager(context)
    context.classroom = ClassroomManager(context)
    context.assistant_actions = build_desktop_registry()
    return context


def say(ctx, action, **arguments):
    return ctx.assistant_actions.execute(ctx, action, arguments)


# ------------------------------------------------------------------ parsers


@pytest.mark.parametrize("line, expected", [
    ("3x10 squats at 185", {"name": "squats", "sets": 3, "reps": 10, "weight": 185.0}),
    ("squats 3 sets of 10 @ 185 lbs", {"name": "squats", "sets": 3, "reps": 10, "weight": 185.0}),
    ("3 sets of 8 bench press with 155 pounds", {"name": "bench press", "sets": 3, "reps": 8, "weight": 155.0}),
    ("20 push-ups", {"name": "push-ups", "sets": 1, "reps": 20, "weight": 0.0}),
    ("ran 3 miles", {"name": "ran 3 miles", "sets": 0, "reps": 0, "weight": 0.0}),
])
def test_parse_exercise_line(line, expected):
    assert parse_exercise_line(line) == expected


@pytest.mark.parametrize("text, iso", [
    ("1990-03-03", "1990-03-03"), ("March 3", "2000-03-03"), ("march 3rd 1990", "1990-03-03"),
    ("3/3", "2000-03-03"), ("3/3/90", "1990-03-03"), ("Feb 30", None), ("someday", None), ("", None),
])
def test_parse_birthday(text, iso):
    assert parse_birthday(text) == iso


def test_speak_birthday_hides_placeholder_year():
    assert speak_birthday("2000-03-03") == "March 3"
    assert speak_birthday("1990-03-03") == "March 3, 1990"


def test_days_until_birthday_wraps_and_handles_leap_day():
    today = date(2026, 9, 27)
    assert days_until("2000-09-27", today) == 0
    assert days_until("2000-09-26", today) == 364
    assert days_until("2000-02-29", date(2026, 2, 28)) == 1  # observed Mar 1 in a non-leap year


# ------------------------------------------------------------------ workout


def test_log_workout_creates_exercises_and_sets(ctx):
    reply = say(ctx, "log_workout", exercises=["3x10 squats at 185", "ran 2 miles"], duration_minutes=45)
    assert reply.startswith("Logged your workout: 3x10 Squats at 185; ran 2 miles.")
    assert "New exercise: Squats" in reply
    session = ctx.workout.all_sessions()[0]
    assert len(session.sets_logged) == 3 and session.duration_minutes == 45 and "ran 2 miles" in session.notes


def test_log_workout_reuses_existing_exercise_and_reports_pr(ctx):
    ctx.workout.add_exercise("Back Squat", category="Legs")
    say(ctx, "log_workout", exercises="3x5 squat at 225")
    assert len(ctx.workout.all_exercises()) == 1
    assert say(ctx, "get_personal_record", exercise="squat") == f"Your Back Squat record is 225 for 5 reps, on {date.today().isoformat()}."


def test_workout_summary(ctx):
    assert "No workouts logged yet" in say(ctx, "get_workout_summary")
    say(ctx, "log_workout", exercises=["20 push-ups"])
    assert say(ctx, "get_workout_summary") == "1 workout(s) this week. Your last one was today (Push-Ups)."


# ------------------------------------------------------------------ people & pets


def test_add_and_enrich_a_person(ctx):
    assert say(ctx, "add_person", name="Megan", relationship="Sister", birthday="June 12") == "Added Megan (Sister) to People, birthday June 12."
    say(ctx, "update_person", name="megan", favorite_thing="cast iron cooking", gift_idea="a Lodge skillet", note="started nursing school")
    reply = say(ctx, "get_person", name="Megan")
    assert "your sister" in reply and "June 12" in reply and "Lodge skillet" in reply and "nursing school" in reply


def test_add_person_duplicate(ctx):
    ctx.relationships.add_person("Sarah")
    assert "already in People" in say(ctx, "add_person", name="sarah")


def test_update_person_bad_birthday_is_refused(ctx):
    ctx.relationships.add_person("Sarah")
    assert "couldn't read" in say(ctx, "update_person", name="Sarah", birthday="someday")


def test_upcoming_birthdays(ctx):
    # Year 2000 (a leap year) keeps every month/day valid, including Feb 29.
    ctx.relationships.add_person("Sarah", birthday=(date.today() + timedelta(days=5)).replace(year=2000).isoformat())
    ctx.relationships.add_person("Ray", birthday=(date.today() + timedelta(days=200)).replace(year=2000).isoformat())
    reply = say(ctx, "list_upcoming_birthdays")
    assert "Sarah in 5 days" in reply and "Ray" not in reply


def test_pets_medical_history_is_dated(ctx):
    assert say(ctx, "add_pet", name="Rosie", species="Dog") == "Added Rosie the dog to Pets."
    say(ctx, "update_pet", name="rosie", medical_note="rabies vaccine")
    reply = say(ctx, "get_pet", name="Rosie")
    assert f"{date.today().isoformat()}: rabies vaccine" in reply


# ------------------------------------------------------------------ household


def test_household_routine_lifecycle(ctx):
    assert "don't have any household routines" in say(ctx, "list_household_routines")
    assert say(ctx, "add_household_routine", name="Laundry", times=2, recurrence="weekly") == "Added Laundry: 2 times a week. I'll track your streak."
    assert "already have" in say(ctx, "add_household_routine", name="laundry")
    assert say(ctx, "log_household_routine", routine="a load of laundry") == "Laundry: 1 of 2."
    assert say(ctx, "log_household_routine", routine="laundry") == "Laundry: 2 of 2. That's done for the week!"
    assert "1 of 1 routines done" in say(ctx, "list_household_routines")


def test_log_unknown_routine_lists_existing(ctx):
    say(ctx, "add_household_routine", name="Dishes", times=1)
    assert "You have: Dishes" in say(ctx, "log_household_routine", routine="mopping")


# ------------------------------------------------------------------ classroom


def test_classroom_course_lessons_notes_and_progress(ctx):
    reply = say(ctx, "add_course", subject="Electrical", course="Residential Wiring", lessons=["Circuit Breakers", "GFCI Outlets"])
    assert reply == "Added the course Residential Wiring with 2 lessons under new subject Electrical."
    assert say(ctx, "add_lesson", course="wiring", lessons=["Panel Upgrades"]) == "Added Panel Upgrades to Residential Wiring."
    assert say(ctx, "complete_lesson", lesson="circuit breakers") == "Nice, Circuit Breakers is done. Residential Wiring: 1 of 3 lessons complete."
    assert say(ctx, "add_lesson_notes", lesson="GFCI", notes="test them monthly") == "Added to your GFCI Outlets notes."
    assert say(ctx, "get_learning_progress") == "Electrical: 1 of 3 lessons, next up GFCI Outlets."


def test_complete_lesson_only_considers_unfinished(ctx):
    say(ctx, "add_course", subject="Electrical", course="Basics", lessons=["Ohm's Law"])
    say(ctx, "complete_lesson", lesson="ohm")
    assert "don't have an unfinished lesson called 'ohm'" in say(ctx, "complete_lesson", lesson="ohm")
