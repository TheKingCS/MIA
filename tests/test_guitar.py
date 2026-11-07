"""
tests.test_guitar
===================

MIA teaches guitar (core/guitar.py, core/guitar_ear.py, DEC-0111): her ear
hears notes and chords right (and wrong ones as wrong), the program is sound
(every shape makes its chord's notes), and the coaching runs end to end:
start, practise, checks counted, said and heard, stages that open when their
checks pass, and weekly homework that completes itself from the log, with XP
in the Music skill.
"""

from __future__ import annotations

import io
import wave
from datetime import date, timedelta

import pytest

from core import guitar as g
from core import guitar_ear as ear

RATE = 22050
TODAY = date(2026, 11, 7)  # a Saturday


def _wav(samples, rate: int = RATE) -> bytes:
    """Samples as 16-bit mono WAV bytes, as the phone sends them."""
    import numpy as np

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(np.asarray(samples), -1, 1) * 32767).astype("<i2").tobytes())
    return out.getvalue()


def _strum(chord: g.Chord, frets: str = "") -> list[float]:
    """What a chord's shape sounds like (or the frets given instead, for a string fretted wrong): each played
    string's note."""
    open_strings = [ear.freq_of(n, o) for n, o in ear.STANDARD_TUNING]
    return ear.synth([f * 2 ** (int(fret) / 12) for f, fret in zip(open_strings, frets or chord.frets) if fret != "x"],
                     RATE)


def test_her_ear_hears_notes_and_the_tuner_says_which_way():
    """Each open string is heard as its note; a flat one says flat and how far; a WAV round-trips; silence and a
    format she doesn't read are refused."""
    for string, (note, octave) in zip(range(6, 0, -1), ear.STANDARD_TUNING):
        heard = ear.tuning(ear.pitch(ear.synth([ear.freq_of(note, octave)]), RATE), string)
        assert heard["in_tune"] and heard["heard"] == f"{note}{octave}", heard
    flat = ear.tuning(ear.pitch(ear.synth([ear.freq_of("A", 2) * 2 ** (-30 / 1200)]), RATE), 5)
    assert not flat["in_tune"] and -32 < flat["cents"] < -28
    assert ear.note_of(110.0) == ("A", 2, 0.0)
    samples, rate = ear.read_wav(io.BytesIO(_wav(ear.synth([196.0]))))
    assert rate == RATE and ear.note_of(ear.pitch(samples, rate))[:2] == ("G", 3)
    with pytest.raises(ear.EarError):
        ear.pitch([0.0] * RATE, RATE)
    with pytest.raises(ear.EarError):
        ear.read_wav(io.BytesIO(b"not a wav"))


def test_every_shape_makes_its_chord_and_she_hears_each_one():
    """The frets of every shape give exactly its chord's notes; each clean chord is heard as passing; the wrong
    chord, or a string fretted wrong, isn't; an extra string that's a chord tone (Am with the low E) is fine."""
    open_strings = [n for n, _o in ear.STANDARD_TUNING]
    for chord in g.CHORDS.values():
        notes = {ear.NOTES[(ear.NOTES.index(n) + int(f)) % 12] for n, f in zip(open_strings, chord.frets) if f != "x"}
        assert notes == set(chord.notes), chord.name
        assert ear.hear_chord(ear.chroma(_strum(chord), RATE), chord.notes)["passed"], chord.name
    em = ear.chroma(_strum(g.CHORDS["Em"]), RATE)
    assert not ear.hear_chord(em, g.CHORDS["Am"].notes)["passed"]
    wrong_fret = ear.hear_chord(ear.chroma(_strum(g.CHORDS["G"], "320303"), RATE), g.CHORDS["G"].notes)
    assert not wrong_fret["passed"] and wrong_fret["stray"] == ["A#"]  # the G string at the 3rd fret
    assert "isn't in G" in ear.describe_chord("G", wrong_fret)
    assert ear.hear_chord(ear.chroma(_strum(g.CHORDS["Am"], "002210"), RATE), g.CHORDS["Am"].notes)["passed"]


def test_the_program_is_whole():
    """Five stages, numbered in order; every lesson has steps and a why; every chord a lesson teaches or a check
    hears is a known shape; every counted check has a mark and a unit; check and lesson ids are unique."""
    assert [s.number for s in g.STAGES] == [1, 2, 3, 4, 5]
    every_check = [c for s in g.STAGES for c in s.checks]
    assert len(every_check) == len(g.CHECKS) and len({l.id for s in g.STAGES for l in s.lessons}) == len(g.LESSONS)
    for s in g.STAGES:
        assert s.lessons and s.checks
        for lesson in s.lessons:
            assert lesson.steps and lesson.why and set(lesson.chords) <= set(g.CHORDS)
    for c in every_check:
        assert c.how in ("heard_chord", "heard_tuning", "counted", "said")
        assert (c.chord in g.CHORDS) == (c.how == "heard_chord")
        assert bool(c.passes_at > 0 and c.unit) == (c.how == "counted")
    assert "low E fret 3 (finger 2)" in g.shape_text(g.CHORDS["G"])
    assert g.teach(g.LESSONS["em_am"][1]).startswith("Your first chords") and "Watch for:" in g.teach(
        g.LESSONS["em_am"][1])


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The shared engine world (profiles, missions, skills) with a guitar coach in the person's folder."""
    from tests.engine_world import build_world

    context = build_world(tmp_path, monkeypatch)
    context.guitar = g.GuitarCoach(context, data_dir=tmp_path / "me")
    return context


def test_learning_runs_from_start_to_the_next_stage(world):
    """Start with a goal and a plan; practise; a counted check under the mark fails and over it passes; a said one
    passes; heard ones pass from recordings; when the stage's checks are all passed, stage 2 opens, with XP in
    Music."""
    coach = world.guitar
    assert "learn guitar" in g.next_step(coach)
    said = g._action_start(world, {"goal": "play songs around the fire", "minutes_a_day": 20, "days_a_week": 4})
    assert "20 minutes a day, 4 days a week" in said and coach.goal == "play songs around the fire"
    assert g._action_practice(world, {"minutes": 0}) == "How long did you practise?"
    assert g._action_practice(world, {"minutes": 25, "worked_on": "Em and Am"}).startswith("Logged. This week: 1 of 4")
    low = g._action_check(world, {"check": "E minor to A minor changes", "value": 12})
    assert "not there yet" in low and "passes at 20" in low
    assert g._action_check(world, {"check": "Em to Am changes", "value": 22}).startswith("Passed")
    assert g._action_check(world, {"check": "strum_60"}).startswith("Passed")
    assert "I listen to" in g._action_check(world, {"check": "em_clean"})
    for chord in ("em_clean", "am_clean"):
        heard = g.listen(world, chord, _wav(_strum(g.CHORDS[g.CHECKS[chord][1].chord])))
        assert heard["passed"] and "clean" in heard["said"]
    bad = g.listen(world, "em_clean", _wav(_strum(g.CHORDS["Am"])))
    assert not bad["passed"]
    for string, (note, octave) in zip(range(6, 0, -1), ear.STANDARD_TUNING):
        result = g.listen(world, "tuned", _wav(ear.synth([ear.freq_of(note, octave)])), string)
    assert result["passed"] and result["stage_done"] and coach.stage == 2
    assert world.skills.get_progress(world.me.profile_id, g.SKILL).total_xp > 0
    with pytest.raises(ValueError):
        g.listen(world, "tuned", _wav(ear.synth([110.0])))  # which string?
    with pytest.raises(ValueError):
        g.listen(world, "strum_60", _wav(ear.synth([110.0])))  # said, not heard
    assert "Stage 2 of 5" in g._action_progress(world, {})


def test_homework_is_a_weekly_mission_that_completes_from_the_log(world):
    """The week's homework has practice days, minutes and the open checks; practice moves it; it completes itself
    when everything's done; next week brings a new one."""
    coach = world.guitar
    coach.start("songs", minutes_a_day=10, days_a_week=2, today=TODAY)
    mission = g.ensure_homework(world, TODAY)
    texts = [o.description for o in mission.objectives]
    assert texts[:2] == ["Practise on 2 days", "Practise 20 minutes in all"] and len(texts) == 5
    assert mission.assigned_by == "mia" and mission.occurrence_key == "guitar:week:2026-11-02"
    monday = TODAY - timedelta(days=TODAY.weekday())
    coach.log_practice(10, day=monday.isoformat())
    coach.log_practice(12, day=TODAY.isoformat())
    for check in ("tuned", "em_clean", "am_clean"):
        coach.attempt(check, True, how="heard")
    done = g.ensure_homework(world, TODAY)
    assert done.status == "completed"
    nxt = g.ensure_homework(world, TODAY + timedelta(days=7))
    assert nxt.mission_id != done.mission_id and nxt.status == "active"


def test_stats_say_how_its_going(world):
    """This week against the plan, the streak (today or yesterday keeps it), hours, and the bests."""
    coach = world.guitar
    coach.start("x", minutes_a_day=15, days_a_week=5, today=TODAY)
    for back in (0, 1, 2):
        coach.log_practice(30, day=(TODAY - timedelta(days=back)).isoformat())
    coach.attempt("changes_em_am", False, value=14, how="counted")
    coach.attempt("changes_em_am", True, value=21, how="counted")
    s = g.stats(coach, TODAY)
    assert s["week_days"] == 3 and s["week_minutes"] == 90 and s["streak"] == 3 and s["hours"] == 1.5
    assert s["bests"] == {"changes_em_am": 21} and s["checks_passed"] == 1
    assert g.stats(coach, TODAY + timedelta(days=3))["streak"] == 0  # a gap breaks it
    assert "Bests:" in g.describe_stats(coach, TODAY)
