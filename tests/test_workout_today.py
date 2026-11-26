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
    assert said.startswith("You trained the last two days: a light day or a walk is a fine choice too. Pull is the "
                           "one rested longest (last trained 11 days ago).")
    assert "Barbell Row (last time 10 reps at 115 lb; try 11 reps at 115 lb)" in said
    assert 'Your saved workout "Pull day" covers it.' in said


def test_with_no_history_a_starter(monkeypatch):
    from core import person_settings

    monkeypatch.setattr(person_settings, "person_id", lambda c: None)
    said = workout_today.say(SimpleNamespace(workout=_store([])), TODAY)
    assert said.startswith("With nothing logged yet, a full-body starter")


def test_twelve_reps_steps_up_the_weight_and_a_hold_its_seconds():
    assert workout_today._step_up(12, 135, 0, "lb") == "try 140 lb for 8"
    assert workout_today._step_up(12, 15, 0, "lb") == "try 17.5 lb for 8"
    assert workout_today._step_up(8, 0, 0, "kg") == "try 9 reps"
    assert workout_today._step_up(0, 0, 30, "lb") == "try 35 seconds"
    assert workout_today._last(1, 0, 0, "lb") == "last time 1 rep"


def test_a_spoken_log_counts_by_the_exercises_name(monkeypatch):
    from core import person_settings

    monkeypatch.setattr(person_settings, "person_id", lambda c: None)
    exercises = [SimpleNamespace(exercise_id="sq", name="Back Squat", category="Full Body"),
                 SimpleNamespace(exercise_id="pu", name="Push-up", category="Full Body")]
    sessions = [_session("2026-11-25", ("sq", 10, 185)), _session("2026-11-01", ("pu", 15, 0))]
    store = SimpleNamespace(all_exercises=lambda: exercises, all_templates=lambda: [],
                            all_sessions=lambda start_date=None: [s for s in sessions if s.date >= (start_date or "")])
    said = workout_today.say(SimpleNamespace(workout=store), TODAY)
    assert said.startswith("Push is the one rested longest (last trained not in the last two weeks).")
    assert "Push-up (last time 15 reps; try 16 reps)" in said, "his last set from all his history"
    assert "Core" not in said, "a group he has no exercises for is never chosen"


def test_his_plan_comes_first(monkeypatch):
    from core import person_settings

    monkeypatch.setattr(person_settings, "person_id", lambda c: None)
    store = _store([_session("2026-11-15", ("row", 10, 115))])
    store.get_template = lambda tid: SimpleNamespace(exercises=[{"exercise_id": "row"}])
    fitness = SimpleNamespace(plan={"training": {"rotation": [{"name": "Pull day", "template_id": "t1"}]}},
                              today_training=lambda t=None: {"name": "Pull day", "template_id": "t1", "done": False},
                              default_units=lambda: "kg")
    said = workout_today.say(SimpleNamespace(workout=store, fitness=fitness), TODAY)
    assert said == "Today in your plan: Pull day. Barbell Row (last time 10 reps at 115 kg; try 11 reps at 115 kg)."
    fitness.today_training = lambda t=None: None
    assert workout_today.say(SimpleNamespace(workout=store, fitness=fitness), TODAY).startswith("Today's a rest day")


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
    for words in ("what project should I do next", "what project should I build next in the shop"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) != "the piece", words
