"""
tests.test_curriculum
=======================

MIA's curriculum (core/curriculum.py, DEC-0107): the tracks are whole and
point at real files, mastery is counted from the nights' lessons, the next
objective takes the tracks in turn, security lessons carry their rules, and
a night of school sets one lesson for it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from core import curriculum as cur
from core import night_school as ns
from tests.test_night_school import FakeLab, exercise, school  # noqa: F401 (school is a fixture)

ROOT = Path(__file__).resolve().parent.parent


def test_every_track_is_whole_and_points_at_real_places():
    """Each track named in the request is there, every objective has a level, a practice and unique id, and every
    file or folder it starts from exists."""
    ids = {t.id for t in cur.TRACKS}
    assert {"engineering", "testing", "documentation", "design", "web", "apps", "deploying", "security", "pentest",
            "monitoring"} <= ids
    every = [o for t in cur.TRACKS for o in t.objectives]
    assert len(every) == len(cur.BY_ID) and all(o.track in ids and o.level in cur.LEVELS for o in every)
    assert all(t.objectives[0].level == "foundation" for t in cur.TRACKS)
    missing = [(o.id, f) for o in every for f in o.files if not (ROOT / f.rstrip("/")).exists()]
    assert not missing, missing


def test_mastery_is_counted_from_lessons_passed():
    """Two passed lessons for an objective master it; fails count as tried; invalid lessons and ones without an
    objective don't count."""
    rows = cur.progress([{"objective": "engineering.1", "outcome": "pass"},
                         {"objective": "engineering.1", "outcome": "fail"},
                         {"objective": "engineering.1", "outcome": "pass"},
                         {"objective": "testing.1", "outcome": "invalid"},
                         {"outcome": "pass"}, {"objective": "nope.9", "outcome": "pass"}])
    assert rows["engineering.1"] == {"tried": 3, "passed": 2, "mastered": True}
    assert rows["testing.1"] == {"tried": 0, "passed": 0, "mastered": False}
    standing = {s["track"]: s for s in cur.standing(rows)}
    assert standing["engineering"]["mastered"] == 1 and standing["engineering"]["level"] == "none"
    done = cur.progress({"objective": o.id, "outcome": "pass"} for o in cur.TRACKS[1].objectives
                        if o.level == "foundation" for _ in range(2))
    assert {s["track"]: s for s in cur.standing(done)}["testing"]["level"] == "foundation"


def test_the_tracks_take_turns_even_while_she_struggles():
    """Behind everywhere, the first track; a track she's tried and failed yields to one untried; a mastered
    objective moves her on; with everything mastered there's nothing next."""
    empty = cur.progress([])
    assert cur.next_objective(empty).id == "engineering.1"
    failing = cur.progress([{"objective": "engineering.1", "outcome": "fail"}] * 3)
    assert cur.next_objective(failing).id == "testing.1"  # no share mastered anywhere, engineering tried most
    one = cur.progress([{"objective": "engineering.1", "outcome": "pass"}] * 2)
    assert cur.next_objective(one).track != "engineering"
    everything = cur.progress({"objective": o, "outcome": "pass"} for o in cur.BY_ID for _ in range(2))
    assert cur.next_objective(everything) is None


def test_security_lessons_carry_the_rules():
    """A security or pen-testing brief says she attacks only herself, in-process; others don't need the rules."""
    pentest = cur.lesson_brief(cur.BY_ID["pentest.2"])
    assert "on MIA herself only" in pentest and "TestClient" in pentest and "never a network address" in pentest
    assert cur.SECURITY_RULES in cur.lesson_brief(cur.BY_ID["security.1"])
    assert cur.SECURITY_RULES not in cur.lesson_brief(cur.BY_ID["design.1"])


def test_a_night_sets_one_lesson_for_her_curriculum(school):
    """The syllabus asks for the curriculum exercise by its objective, and the lesson she passes for it is counted
    toward that objective."""
    asked = []

    def ask(provider, prompt):
        asked.append(prompt)
        if "set her exercises" in prompt:
            return json.dumps({"pick_agrees": True, "why": "fine", "exercises": [
                exercise(objective="engineering.1", test_name="tests/test_night_pin_down.py")]})
        return json.dumps({"note": "Good."})

    clock = iter([datetime(2026, 11, 7, 1, 30) + timedelta(minutes=10 * i) for i in range(40)])
    night = ns.night(datetime(2026, 11, 7, 1, 30), ask=ask, lab=FakeLab(school.tmp), one_test=lambda w, n: False,
                     shadow=lambda tid: {"outcome": "pass", "summary": "ok"}, clock=lambda: next(clock),
                     config=dict(ns.DEFAULTS), store=school.store, tasks_dir=school.tasks, log=school.log)
    assert night["objective"] == "engineering.1" and '"objective": "engineering.1"' in asked[0]
    assert night["lessons"][0]["objective"] == "engineering.1" and night["lessons"][0]["outcome"] == "pass"
    assert "Curriculum: engineering.1" in ns.describe(night)
    rows = cur.progress(l for n in ns.nights(store=school.store) for l in n.get("lessons", []))
    assert rows["engineering.1"]["passed"] == 1
    off = ns.night(datetime(2026, 11, 8, 1, 30), ask=ask, lab=FakeLab(school.tmp), one_test=lambda w, n: False,
                   shadow=lambda tid: {"outcome": "pass"}, clock=lambda: datetime(2026, 11, 8, 1, 30),
                   config=dict(ns.DEFAULTS, curriculum=False), store=school.store, tasks_dir=school.tasks,
                   log=school.log)
    assert "objective" not in off


def test_her_self_assessment_names_a_model_that_could_help():
    """A slipping loop one of her playbook's models serves says so in her reason (DEC-0106); one no model serves
    doesn't."""
    areas = ns.self_assessment([{"id": "answers.no_tool", "what": "no tool", "state": "below", "why": "3 this week"},
                                {"id": "pc.disk", "what": "free space", "state": "slid", "why": "less"}], {}, {})
    why = {a["area"]: a["why"] for a in areas}
    assert why["loop answers.no_tool"].endswith("(a model of her own could help: a router that picks which of her "
                                                "tools fit what was said)")
    assert "model" not in why["loop pc.disk"]
