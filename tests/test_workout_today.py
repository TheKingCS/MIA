"""
tests.test_workout_today
==========================

"What's a good workout for today?" (core/workout_today.py, the live sweep 2026-11-26): the group he's rested
longest, his own exercises for it with last time and a small step up, his saved workout for it; a starter with no
history; "what should I train today?" reaches it in code.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, workout_today

TODAY = date(2026, 11, 26)


def _store(sessions):
    exercises = [SimpleNamespace(exercise_id="sq", name="Back Squat", category="Legs"),
                 SimpleNamespace(exercise_id="bp", name="Bench Press", category="Chest"),
                 SimpleNamespace(exercise_id="row", name="Barbell Row", category="Back"),
                 SimpleNamespace(exercise_id="pl", name="Plank", category="Core")]
    templates = [SimpleNamespace(name="Pull day", exercises=[{"exercise_id": "row"}])]
    return SimpleNamespace(all_exercises=lambda: exercises, all_templates=lambda: templates,
                           all_sessions=lambda start_date=None: [s for s in sessions if s.date >= (start_date or "")])


def _session(day, *sets):
    return SimpleNamespace(date=day, profile_id=None,
                           sets_logged=[{"exercise_id": e, "reps": r, "weight": w} for e, r, w in sets])


def test_the_group_rested_longest_with_his_own_lifts(monkeypatch):
    from core import person_settings

    monkeypatch.setattr(person_settings, "person_id", lambda c: None)
    store = _store([_session("2026-11-25", ("sq", 10, 185), ("sq", 8, 185)), _session("2026-11-24", ("bp", 12, 135)),
                    _session("2026-11-20", ("pl", 1, 0)), _session("2026-11-15", ("row", 10, 115))])
    said = workout_today.say(SimpleNamespace(workout=store), TODAY)
    assert said.startswith("Pull is the one rested longest (last trained 11 days ago).")
    assert "Barbell Row (last time 10 reps at 115 lb; try 11 reps at 115 lb)" in said
    assert 'Your saved workout "Pull day" covers it.' in said


def test_with_no_history_a_starter(monkeypatch):
    from core import person_settings

    monkeypatch.setattr(person_settings, "person_id", lambda c: None)
    said = workout_today.say(SimpleNamespace(workout=_store([])), TODAY)
    assert said.startswith("With nothing logged in the last two weeks, a full-body starter")


def test_twelve_reps_steps_up_the_weight():
    assert workout_today._step_up(12, 135) == "try 140 lb for 8"
    assert workout_today._step_up(8, 0) == "try 9 reps"


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(workout_today, "say", lambda c, t=None: "the workout")
    for words in ("What's a good workout for today?", "what should I train today", "what workout should I do",
                  "what should I work out tonight?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the workout", words


def test_the_next_woodworking_piece_from_the_course(monkeypatch):
    from core import woodworking

    off = woodworking.next_project(SimpleNamespace())
    assert off.startswith("Something small with real joints, finished start to end: a cutting board")
    assert 'say "materials for a 6 foot workbench"' in off
    monkeypatch.setattr(woodworking, "next_project", lambda c: "the piece")
    for words in ("What woodworking project should I do next?", "what's a good first woodworking project",
                  "what should I build in my shop"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the piece", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what project should I do next") != "the piece"
