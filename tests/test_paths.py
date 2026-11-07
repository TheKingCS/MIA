"""
tests.test_paths
==================

MIA's learning paths (core/paths.py, DEC-0112): the same loop for any desire.
A program for an interest with none is drafted (grounded, checked in code,
kept as a draft until started); several paths run side by side, each with
its own homework mission that completes from the log; statistics; and a
draft whose shape doesn't hold is refused.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from core import paths
from core.assistant_path_actions import _action_check, _action_practice, _action_progress, _action_start

TODAY = date(2026, 11, 7)  # a Saturday

DRAFT = {"name": "Welding", "skill": "fabrication", "about": "Safe, strong welds.", "words": ["weld", "welding", "mig"],
         "stages": [
             {"name": "Safety and setup", "builds": "setting up safely",
              "lessons": [{"title": "Gear and ventilation", "steps": ["Wear an auto-darkening helmet.", "Ventilate."],
                           "why": "Burns and fumes are the real dangers.", "watch": ["Flammables nearby."]}],
              "checks": [{"what": "Set up the welder and the gear safely", "how": "said"}]},
             {"name": "Beads", "builds": "running a straight bead",
              "lessons": [{"title": "Running a bead", "steps": ["Hold the gun at 15 degrees.", "Push steadily."],
                           "why": "Every weld is beads.", "watch": []}],
              "checks": [{"what": "Straight beads in a row on scrap", "how": "counted", "passes_at": 5,
                          "unit": "beads"}]}]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The shared engine world with learning paths in the person's folder."""
    from tests.engine_world import build_world

    context = build_world(tmp_path, monkeypatch)
    context.paths = paths.PathBook(context, data_dir=tmp_path / "me")
    return context


def test_a_new_interest_is_drafted_checked_and_started_only_when_asked(world, monkeypatch):
    """No program for welding: one is drafted (the prompt carries the interest, the goal and the specialists'
    grounding), its ids made in code, kept as a draft and described; "start it" starts it; then it runs like any
    path, counted checks against their mark."""
    asked = []

    def model(prompt):
        asked.append(prompt)
        return "Here:\n" + json.dumps(DRAFT)

    monkeypatch.setattr(paths, "_ollama", model)
    said = _action_start(world, {"interest": "welding", "goal": "fix my own trailer"})
    assert said.startswith("Welding (a plan I drafted for you): stage 1, Safety and setup") and "start it" in said
    assert "welding" in asked[0] and "fix my own trailer" in asked[0] and "specialists" in asked[0]
    book = world.paths
    assert "welding" in book.drafts and book.path("welding") is None  # a draft, not started
    started = _action_start(world, {"interest": "", "minutes_a_day": 30, "days_a_week": 3})
    assert "You're set for Welding (a plan I drafted): 30 minutes a day, 3 days a week" in started
    program = paths.program_of(world, "welding")
    assert program.drafted and paths.problems(program) == [] and program.skill == "fabrication"
    assert _action_check(world, {"check": "set up the welder safely", "path": "welding"}).startswith("Passed")
    assert "not there yet" in _action_check(world, {"check": "straight beads", "value": 3, "path": "welding"})
    assert "That finishes the stage" not in _action_check(world, {"check": "beads", "value": 6, "path": "welding"})
    assert book.passed("welding", "welding_2_c1")


def test_a_draft_that_doesnt_hold_together_is_refused(world, monkeypatch):
    """A counted check without a mark, or a stage without checks, is caught in code and nothing is kept."""
    bad = json.loads(json.dumps(DRAFT))
    bad["stages"][1]["checks"][0].pop("passes_at")
    monkeypatch.setattr(paths, "_ollama", lambda prompt: json.dumps(bad))
    assert "didn't hold together" in _action_start(world, {"interest": "welding"})
    assert world.paths.drafts == {}
    monkeypatch.setattr(paths, "_ollama", lambda prompt: "no json here")
    assert "didn't come through" in _action_start(world, {"interest": "welding"})


def test_paths_run_side_by_side_each_with_its_homework(world, monkeypatch):
    """Guitar and a drafted path at once: each has its own weekly homework mission; practice on one moves only its
    own; a mission completes from the log; the progress answer covers both; which path is asked when it's unclear."""
    monkeypatch.setattr(paths, "_ollama", lambda prompt: json.dumps(DRAFT))
    from core import guitar

    book = world.paths
    book.start(guitar.PROGRAM, "songs", 10, 2, today=TODAY)
    weld = paths.draft(world, "welding")
    book.start(weld, "trailer", 20, 1, today=TODAY)
    missions = paths.ensure_homework(world, TODAY)
    assert sorted(m.occurrence_key for m in missions) == ["path:guitar:week:2026-11-02", "path:welding:week:2026-11-02"]
    assert "Which one?" in _action_practice(world, {"minutes": 20})
    monday = (TODAY - timedelta(days=TODAY.weekday())).isoformat()
    book.log_practice(weld, 20, day=monday)
    book.attempt(weld, "welding_1_c1", True)
    done = {m.occurrence_key: m.status for m in paths.ensure_homework(world, TODAY)}
    assert done["path:welding:week:2026-11-02"] == "completed" and done["path:guitar:week:2026-11-02"] == "active"
    said = _action_progress(world, {})
    assert said.startswith("Guitar: stage 1 of 5") and "Welding: stage 2 of 2" in said


def test_stats_say_how_a_path_is_going(world):
    """This week against the plan, the streak (a gap breaks it), hours, checks and bests."""
    from core import guitar

    book = world.paths
    book.start(guitar.PROGRAM, "x", 15, 5, today=TODAY)
    for back in (0, 1, 2):
        book.log_practice(guitar.PROGRAM, 30, day=(TODAY - timedelta(days=back)).isoformat())
    book.attempt(guitar.PROGRAM, "changes_em_am", False, value=14, how="counted")
    book.attempt(guitar.PROGRAM, "changes_em_am", True, value=21, how="counted")
    s = paths.stats(book, guitar.PROGRAM, TODAY)
    assert (s["week_days"], s["week_minutes"], s["streak"], s["hours"]) == (3, 90, 3, 1.5)
    assert s["bests"] == {"changes_em_am": 21} and s["checks_passed"] == 1
    assert paths.stats(book, guitar.PROGRAM, TODAY + timedelta(days=3))["streak"] == 0
    assert "Bests:" in paths.describe_stats(book, guitar.PROGRAM, TODAY)


def test_a_program_saves_and_comes_back_the_same():
    """A drafted program's saved form reads back as the same program."""
    program = paths.program_from_draft(DRAFT, "welding")
    again = paths.from_dict(paths.to_dict(program))
    assert again.stages == program.stages and again.name == program.name and again.drafted
