"""
tests.test_hobby_programs
===========================

His hobbies' learning programs (DEC-0289): woodworking, gardening and homesteading, fitness, survival and bushcraft,
on core/paths.py's method like guitar and carpentry; a recorded check counts from the day its stage opened. Each one's skill is a real skill, every recorded check reads a
record MIA keeps, every id is unique, every lesson has steps, a why and things to watch for, and the words that start
one don't start another.
"""

import json
from pathlib import Path

import pytest

from core import paths

ROOT = Path(__file__).resolve().parent.parent
HOBBIES = ("woodworking", "gardening", "fitness", "bushcraft")


def _skills() -> set:
    raw = json.loads((ROOT / "data" / "skill_definitions.json").read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("skills", list(raw.values()))
    return {r.get("id") or r.get("skill_id") for r in rows}


@pytest.mark.parametrize("pid", HOBBIES)
def test_each_hobby_program_is_registered_and_complete(pid):
    paths._builtins()
    program = paths.PROGRAMS[pid]
    assert program.skill in _skills()
    assert program.stages and [s.number for s in program.stages] == list(range(1, len(program.stages) + 1))
    for stage in program.stages:
        assert stage.lessons and stage.checks
        for lesson in stage.lessons:
            assert lesson.steps and lesson.why and lesson.watch, lesson.id
        for check in stage.checks:
            assert check.how in ("said", "counted", "recorded"), check.id
            if check.how == "recorded":
                assert check.source in paths.SOURCES and check.passes_at > 0, check.id
            if check.how == "counted":
                assert check.passes_at > 0 and check.unit, check.id


def test_ids_are_unique_and_no_words_start_two_programs():
    paths._builtins()
    ids = [c.id for p in paths.PROGRAMS.values() for s in p.stages for c in s.checks]
    lessons = [l.id for p in paths.PROGRAMS.values() for s in p.stages for l in s.lessons]
    for pid in HOBBIES:
        program = paths.PROGRAMS[pid]
        own = [c.id for s in program.stages for c in s.checks] + [l.id for s in program.stages for l in s.lessons]
        assert len(own) == len(set(own)), pid
    words = [w for p in paths.PROGRAMS.values() for w in p.words]
    assert len(words) == len(set(words))
    assert ids and lessons


def test_the_safety_lines_are_there():
    paths._builtins()
    text = lambda pid: " ".join(" ".join(l.steps) for s in paths.PROGRAMS[pid].stages for l in s.lessons)  # noqa: E731
    assert "riving knife" in text("woodworking") and "oil" in text("woodworking")
    assert "pressure canner" in text("gardening") and "tested recipes" in text("gardening")
    assert "check with a doctor" in text("fitness")
    assert "1 minute" in text("bushcraft") and "burn bans" in text("bushcraft")


def test_a_recorded_check_counts_from_the_day_its_stage_opened(tmp_path, monkeypatch):
    """Stage 2's workouts never pass stage 3's minutes: each stage reads its records from the day it opened."""
    from types import SimpleNamespace

    paths._builtins()
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(paths.PROGRAMS["fitness"])
    record = book.path("fitness")
    record["stage"], record["stage_since"] = 3, {"3": "2026-11-20"}
    asked = []
    monkeypatch.setitem(paths.SOURCES, "workout_minutes",
                        paths.Source("minutes", "minutes", lambda c, since: asked.append(since) or 0.0))
    check = paths.PROGRAMS["fitness"].check("minutes_600")[1]
    paths.measure(SimpleNamespace(paths=book), "fitness", check)
    assert asked == ["2026-11-20"]
