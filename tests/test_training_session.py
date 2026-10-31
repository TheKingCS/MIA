"""The live workout session (DEC-0055, core/training_session.py): prescribed
from the plan, performed set by set with how each count was made, rest by
itself, pauses, corrections, counting aloud kept honest, and finishing as
one ordinary workout log."""

from datetime import datetime, timedelta

import pytest

from core import training_session as ts

T0 = datetime(2026, 10, 30, 18, 0, 0)
DAY = {"name": "Push", "exercises": [{"name": "Push-ups", "sets": 2, "reps": 15},
                                     {"name": "Plank", "sets": 1, "hold_seconds": 60, "rest_seconds": 30}]}


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def test_a_session_goes_set_by_set_with_rest_by_itself():
    s = ts.start(DAY, T0)
    assert ts.view(s, T0)["now"] == {"name": "Push-ups", "set": 1, "sets": 2, "target": "15 reps", "reps": 15,
                                     "hold_seconds": None, "cadence_seconds": 2.0, "last": None}
    ts.log_set(s, at(40), reps=12, counted="cadence")  # a short set is a set
    assert s.status == ts.RESTING and ts.rest_left(s, at(50)) == 50
    assert ts.say(s, at(50)) == "Resting: 50 seconds. Then Push-ups, set 2 of 2, 15 reps."
    ts.settle(s, at(100))  # the rest ran out by itself
    assert s.status == ts.ACTIVE and s.steps[0].done[0]["rested"] == 60
    ts.log_set(s, at(140), reps=15, counted="said")
    ts.skip_rest(s, at(150))  # "skip rest": on to the plank
    assert ts.current(s).name == "Plank" and s.steps[0].done[1]["rested"] == 10
    ts.log_set(s, at(220), seconds=45, counted="told")
    assert s.status == ts.COMPLETE and ts.say(s, at(221)).startswith("That's the whole workout")
    with pytest.raises(ValueError):
        ts.log_set(s, at(230), reps=1)


def test_pause_freezes_the_clock_and_the_rest():
    s = ts.start(DAY, T0)
    ts.log_set(s, at(30), reps=15)
    ts.pause(s, at(40))  # 50 s of rest left
    ts.resume(s, at(340))  # five minutes later
    assert s.status == ts.RESTING and ts.rest_left(s, at(340)) == 50
    assert ts.elapsed(s, at(340)) == 40


def test_skip_and_correct():
    s = ts.start(DAY, T0)
    ts.log_set(s, at(30), reps=10)
    ts.correct(s, reps=11)  # "make that 11"
    assert s.steps[0].done[0]["reps"] == 11
    ts.skip_exercise(s, at(40))
    assert ts.current(s).name == "Plank" and s.steps[0].skipped and len(s.steps[0].done) == 1


def test_counting_aloud_is_kept_honest():
    assert ts.numbers_heard("one two three four") == [1, 2, 3, 4]
    assert ts.numbers_heard("twenty one, 22") == [21, 22]
    assert ts.follow_count([1, 2, 2, 3, 4]) == 4  # a repeat isn't counted twice
    assert ts.follow_count([1, 2, 6, 3]) == 3  # a misheard "six" is ignored
    assert ts.follow_count([1, 2, 4, 5]) == 5  # one word lost in the noise
    assert ts.follow_count(ts.numbers_heard("one to three for five")) == 5  # sound-alikes, in sequence
    assert ts.follow_count([1, 2, 3], start=5) == 5  # numbers from before don't move it back


def test_finishing_writes_one_workout_log(tmp_path):
    from types import SimpleNamespace

    logged = []
    exercises = []

    class Workout:
        def all_exercises(self):
            return exercises

        def add_exercise(self, name):
            e = SimpleNamespace(exercise_id=f"x{len(exercises)}", name=name)
            exercises.append(e)
            return e

        def add_session(self, **kw):
            logged.append(kw)
            return SimpleNamespace(session_id="w1")

    store = ts.TrainingStore(SimpleNamespace(workout=Workout()), data_dir=tmp_path)
    store.begin(DAY, T0)
    ts.log_set(store.session, at(30), reps=12, counted="cadence")
    store.save()
    again = ts.TrainingStore(SimpleNamespace(workout=Workout()), data_dir=tmp_path)  # a restart keeps it
    assert again.live().steps[0].done[0]["reps"] == 12
    assert store.finish(at(90)) == "w1" and store.live() is None
    (kw,) = logged
    (entry,) = kw["sets_logged"]
    assert entry["reps"] == 12 and entry["target_reps"] == 15 and entry["counted"] == "cadence"
    assert entry["exercise_id"] == "x0" and kw["duration_minutes"] == 1.5


def test_nothing_done_logs_nothing(tmp_path):
    from types import SimpleNamespace

    store = ts.TrainingStore(SimpleNamespace(workout=None), data_dir=tmp_path)
    store.begin(DAY, T0)
    assert store.finish(at(10)) is None


def test_a_day_with_no_exercises_says_so():
    with pytest.raises(ValueError):
        ts.start({"name": "Rest", "exercises": []}, T0)


def test_resting_after_an_exercise_shows_the_next_one():
    s = ts.start(DAY, T0)
    ts.log_set(s, at(30), reps=15)
    ts.skip_rest(s, at(40))
    ts.log_set(s, at(80), reps=15)  # Push-ups' last set: the rest leads to the plank
    v = ts.view(s, at(90))
    assert s.status == ts.RESTING and v["now"]["name"] == "Plank" and v["next"] is None
    assert ts.say(s, at(90)) == "Resting: 50 seconds. Then Plank, set 1 of 1, 60 seconds."


@pytest.mark.parametrize("said, status, expected", [
    ("MIA, start my workout routine.", None, ("training.start", {})),
    ("let's do my workout", None, ("training.start", {})),
    ("twelve", None, None),  # no workout going: not a set
    ("twelve", ts.ACTIVE, ("training.set", {"reps": 12, "counted": "told"})),
    ("I got 15 reps", ts.ACTIVE, ("training.set", {"reps": 15, "counted": "told"})),
    ("45 seconds", ts.ACTIVE, ("training.set", {"seconds": 45, "counted": "told"})),
    ("next set", ts.RESTING, ("training.skip_rest", {})),
    ("next set", ts.ACTIVE, ("training.set", {"counted": "tapped"})),  # done, but no count: recorded as uncounted
    ("done", ts.ACTIVE, ("ask", {})),
    ("make that 10", ts.RESTING, ("training.correct", {"reps": 10})),
    ("pause", ts.ACTIVE, ("training.pause", {})),
    ("I'm back", ts.PAUSED, ("training.resume", {})),
    ("skip this exercise", ts.ACTIVE, ("training.skip", {})),
    ("how am I doing?", ts.RESTING, ("say", {})),
    ("I'm done", ts.ACTIVE, ("training.finish", {})),
    ("add milk to the grocery list", ts.ACTIVE, None),  # not about the workout
    ("I did 12 and then I went to the store", ts.ACTIVE, None),
])
def test_what_is_said_during_a_workout(said, status, expected):
    assert ts.parse_training(said, status) == expected


def test_a_set_said_during_rest_ends_the_rest_and_a_hold_is_seconds():
    s = ts.start(DAY, T0)
    ts.log_set(s, at(30), reps=15)
    ts.log_set(s, at(50), reps=14)  # did the second set early: the rest ended there
    assert [d["reps"] for d in s.steps[0].done] == [15, 14] and s.steps[0].done[0]["rested"] == 20
    ts.skip_rest(s, at(60))
    ts.log_set(s, at(120), reps=45)  # "45" on the plank
    assert s.steps[1].done[0]["seconds"] == 45.0 and s.steps[1].done[0]["reps"] is None


def test_a_whole_workout_by_voice(tmp_path, monkeypatch):
    """Start, count, rest, correct and finish by voice; the result is one
    ordinary workout log, so the existing paths (XP, records, missions) follow."""
    from tests.test_crafting import build_world
    from core.actions import ActionCenter
    from core.quick_commands import handle

    w = build_world(tmp_path, monkeypatch)
    w.actions = ActionCenter()
    w.training = ts.TrainingStore(w, data_dir=w.my_dir)
    every_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    w.fitness.update_plan({"training": {"days": every_day, "rotation": [
        {"name": "Push", "exercises": [{"name": "Push-ups", "sets": 2, "reps": 15}]}]}})
    assert handle(w, "MIA, start my workout routine").startswith("Push: 1 exercise. First up, Push-ups, 2 sets of 15 reps")
    assert handle(w, "twelve").startswith("Resting: 60 seconds. Then Push-ups, set 2 of 2")
    assert handle(w, "make that 13") == "Changed to 13 reps."
    assert handle(w, "next set").startswith("Push-ups, set 2 of 2")
    assert handle(w, "I got 15").startswith("That's the whole workout")
    assert handle(w, "I'm done") == "Workout done: 2 sets in the books. Nice work."
    (session,) = w.workout.all_sessions()
    assert [(e["reps"], e["target_reps"], e["counted"]) for e in session.sets_logged] == [(13, 15, "told"), (15, 15, "told")]
    assert handle(w, "twelve") is None  # no workout going: not a command any more
    assert w.fitness.steps_done() == [0]  # the day's Push-ups are done: the training mission follows (DEC-0052)


def test_the_glasses_follow_the_workout(tmp_path, monkeypatch):
    from datetime import date

    from core.actions import ActionCenter
    from core.glasses import _workout_live
    from core.quick_commands import handle
    from tests.test_crafting import build_world

    w = build_world(tmp_path, monkeypatch)
    w.actions = ActionCenter()
    w.training = ts.TrainingStore(w, data_dir=w.my_dir)
    w.fitness.update_plan({"training": {"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "rotation": [
        {"name": "Push", "exercises": [{"name": "Push-ups", "sets": 2, "reps": 15}]}]}})
    panel = _workout_live(w, date.today())
    assert panel["lines"][0]["action"]["kind"] == "training.start"
    handle(w, "start my workout")
    handle(w, "ten")
    lines = _workout_live(w, date.today())["lines"]
    assert lines[0]["text"] == "Push-ups" and lines[0]["detail"] == "Set 2/2 · 15 reps · last 10"
    assert lines[1]["action"]["kind"] == "training.skip_rest"  # resting: skip it from the glasses
