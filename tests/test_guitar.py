"""
tests.test_guitar
===================

Guitar, the first program on MIA's learning paths (core/guitar.py,
core/guitar_ear.py, DEC-0111): her ear hears notes and chords right (and
wrong ones as wrong), the program is sound (every shape makes its chord's
notes), and the path runs end to end by voice: start, practise, checks
counted, said and heard, the next stage opening, XP in Music.
"""

from __future__ import annotations

import io
import wave

import pytest

from core import guitar as g
from core import guitar_ear as ear
from core import paths
from core.assistant_path_actions import _action_check, _action_lesson, _action_practice, _action_progress, _action_start

RATE = 22050


def _wav(samples, rate: int = RATE) -> bytes:
    """Samples as 16-bit mono WAV bytes, as the page sends them."""
    import numpy as np

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(np.asarray(samples), -1, 1) * 32767).astype("<i2").tobytes())
    return out.getvalue()


def _strum(chord: g.Chord, frets: str = "") -> list[float]:
    """What a chord's shape sounds like (or the frets given instead, for a string fretted wrong)."""
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


def test_the_guitar_program_is_whole():
    """Registered, five stages in order, a sound shape (core/paths.problems finds nothing), every chord a lesson or
    a heard check names is a known shape, and a chord lesson is taught with its shapes."""
    assert paths.PROGRAMS["guitar"] is g.PROGRAM and g.PROGRAM.skill == "music"
    assert [s.number for s in g.STAGES] == [1, 2, 3, 4, 5] and paths.problems(g.PROGRAM) == []
    for s in g.STAGES:
        for lesson in s.lessons:
            assert set(lesson.about) <= set(g.CHORDS)
        for c in s.checks:
            assert (c.about in g.CHORDS) == (c.how == "heard_chord")
    assert "low E fret 3 (finger 2)" in g.shape_text(g.CHORDS["G"])
    taught = paths.teach(g.PROGRAM, g.LESSONS["em_am"][1])
    assert taught.startswith("Your first chords") and "Shapes: Em (E, G, B)" in taught and "Watch for:" in taught


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The shared engine world (profiles, missions, skills) with learning paths in the person's folder."""
    from tests.engine_world import build_world

    context = build_world(tmp_path, monkeypatch)
    context.paths = paths.PathBook(context, data_dir=tmp_path / "me")
    return context


def test_learning_guitar_runs_from_start_to_the_next_stage(world):
    """Start by voice with a goal and a plan; practise; a counted check under the mark fails and over it passes; a
    said one passes; heard ones pass from recordings (a wrong chord doesn't); when the stage's checks all pass,
    stage 2 opens, with XP in Music."""
    said = _action_start(world, {"interest": "guitar", "goal": "songs around the fire", "minutes_a_day": 20,
                                 "days_a_week": 4})
    assert "You're set for Guitar: 20 minutes a day, 4 days a week" in said
    book, program = world.paths, g.PROGRAM
    assert book.path("guitar")["goal"] == "songs around the fire"
    assert _action_practice(world, {"minutes": 0}) == "How long did you practise?"
    assert _action_practice(world, {"minutes": 25, "worked_on": "Em and Am"}).startswith("Logged. Guitar this week: 1")
    assert _action_lesson(world, {}).startswith("Holding it and tuning it.")  # tuning is the first open check
    assert _action_lesson(world, {"topic": "the G chord"}).startswith("G (G, B, D): low E fret 3")
    low = _action_check(world, {"check": "E minor to A minor changes", "value": 12})
    assert "not there yet" in low and "passes at 20" in low
    assert _action_check(world, {"check": "Em to Am changes", "value": 22}).startswith("Passed")
    assert _action_check(world, {"check": "strum down 60 bpm"}).startswith("Passed")
    assert "I check myself" in _action_check(world, {"check": "play e minor so every note rings"})
    for check in ("em_clean", "am_clean"):
        heard = paths.verify(world, program, check, {"wav": _wav(_strum(g.CHORDS[program.check(check)[1].about]))})
        assert heard["passed"] and "clean" in heard["said"]
    assert not paths.verify(world, program, "em_clean", {"wav": _wav(_strum(g.CHORDS["Am"]))})["passed"]
    for string, (note, octave) in zip(range(6, 0, -1), ear.STANDARD_TUNING):
        result = paths.verify(world, program, "tuned", {"wav": _wav(ear.synth([ear.freq_of(note, octave)])),
                                                        "string": string})
    assert result["passed"] and result["stage_done"] and book.path("guitar")["stage"] == 2
    assert world.skills.get_progress(world.me.profile_id, "music").total_xp > 0
    with pytest.raises(ValueError):
        paths.verify(world, program, "tuned", {"wav": _wav(ear.synth([110.0]))})  # which string?
    with pytest.raises(ValueError):
        paths.verify(world, program, "strum_60", {"wav": b""})  # said, not heard
    assert "Guitar: stage 2 of 5" in _action_progress(world, {})
