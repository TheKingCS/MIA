"""
tests.test_specialist_roster
==============================

The "counts as added" bar in code (the Specialist Forge's F1, core/specialist_roster.py; DEC-0199): a specialist
missing its charter, limits, words, starter questions, role or caveat is in progress with each gap named; one whose
answers rest on figures needs calculators and enough bench tasks for every discipline, one of them leaving an input
out; with all that but no passing model it's built, not passing; every real specialist meets the bar's first part;
the planned list never names one that exists; and voice says the same as the page.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from core import specialist_roster as roster
from core.eng_bench import TASKS
from core.eng_calcs import CALCULATORS
from core.specialist_work import DISCIPLINES
from core.specialists import BY_ID, ROLES, SPECIALISTS

PASSED = SimpleNamespace(model="m", passed=True, why="")
FAILED = SimpleNamespace(model="m", passed=False, why="it guessed")


def test_each_missing_part_of_a_specialist_is_named():
    spec = BY_ID["electrical"]
    assert roster.check(spec, ROLES["electrical"], DISCIPLINES["electrical"], CALCULATORS, TASKS) == []
    bare = replace(spec, charter="", limits=" ", words=(), starts_from=("one?",), caveat="")
    said = roster.check(bare, None)
    assert said == ["a charter", "its limits", "the words that route questions to it", "at least 2 starter questions",
                    "an agent role (department, task types, tools)"]
    no_caveat = replace(spec, caveat="")
    assert "the caveat its kind of work needs" in roster.check(no_caveat, ROLES["electrical"])


def test_figures_need_calculators_and_enough_bench_tasks_with_one_that_leaves_an_input_out():
    spec = BY_ID["electrical"]
    assert roster.check(spec, ROLES["electrical"], ("telepathy",), CALCULATORS, TASKS) == ["calculators for telepathy"]
    ids = {c.id for c in CALCULATORS if c.discipline == "electrical"}
    two = [t for t in TASKS if t.calculator in ids][:2]
    assert roster.check(spec, ROLES["electrical"], ("electrical",), CALCULATORS, two) == [
        "at least 3 bench tasks for electrical (has 2)"]
    answered = [replace(t, missing="") for t in TASKS if t.calculator in ids]
    assert roster.check(spec, ROLES["electrical"], ("electrical",), CALCULATORS, answered) == [
        "a bench task for electrical that leaves an input out"]


def test_its_standing_needs_a_passing_model_only_when_its_answers_rest_on_figures():
    assert roster.standing([], ("electrical",), PASSED) == roster.ADDED
    assert roster.standing([], ("electrical",), FAILED) == roster.NOT_PASSING
    assert roster.standing([], ("electrical",), None) == roster.NOT_PASSING
    assert roster.standing([], (), None) == roster.ADDED  # works from its notes
    assert roster.standing(["a charter"], (), None) == roster.IN_PROGRESS


def test_every_real_specialist_meets_the_bar_apart_from_its_bench_and_the_planned_list_names_none_of_them():
    for spec in SPECIALISTS:
        gaps = roster.check(spec, ROLES.get(spec.id), DISCIPLINES.get(spec.id, ()), CALCULATORS, TASKS)
        assert gaps == [], (spec.id, gaps)
    have = {s.id for s in SPECIALISTS}
    assert not have & {p[0] for p in roster.PLANNED} and len({p[0] for p in roster.PLANNED}) == len(roster.PLANNED)


def test_the_roster_reads_the_bench_results_and_voice_says_what_the_page_shows():
    from core.specialist_models import MODE

    cell = {"tasks": 5, "right": 5, "asked": 0, "wrong": 0, "guessed": 0, "unreadable": 0, "seconds": 3.0}
    results = {"good": {MODE: {d: dict(cell) for ds in DISCIPLINES.values() for d in ds}}}  # load()'s shape
    page = roster.roster(results)
    by_id = {r["id"]: r for r in page["specialists"]}
    assert by_id["electrical"]["status"] == roster.ADDED and by_id["electrical"]["model"] == "good"
    assert by_id["strategy"]["status"] == roster.ADDED and by_id["strategy"]["model"] == ""
    assert page["counts"][roster.ADDED] == len(SPECIALISTS) and page["counts"][roster.PLANNED_STATUS] == len(page["planned"])
    empty = roster.roster({})
    figures = [r for r in empty["specialists"] if r["disciplines"]]
    assert figures and all(r["status"] == roster.NOT_PASSING for r in figures)
    said = roster.said({})
    assert said.startswith(f"{empty['counts'][roster.ADDED]} specialists are added") and "Next planned: IoT and sensors" in said
