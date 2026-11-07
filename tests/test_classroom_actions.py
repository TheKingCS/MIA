"""The Classroom's web screen (core/classroom_manager.screen, with the course to continue: DEC-0113) and its actions
(core/classroom_actions.py)."""

from types import SimpleNamespace

import pytest

from core import actions
from core.actions import ActionCenter, ActionError
from core.classroom_manager import ClassroomManager, screen


@pytest.fixture
def person(tmp_path, monkeypatch):
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    ctx = SimpleNamespace(config=None, undo=None, events=None, actions=ActionCenter())
    ctx.classroom = ClassroomManager(ctx, data_dir=tmp_path)
    return ctx


def act(ctx, kind, **params):
    done = ctx.actions.approve(ctx, ctx.actions.propose(ctx, kind, params, proposed_by="person").proposal_id)
    return done.result


def test_a_subject_its_course_and_lessons_ticked_off(person, monkeypatch):
    import core.classroom_manager as cm

    credited = []
    monkeypatch.setattr(cm, "grant_xp", lambda *a, **k: credited.append(a))
    assert act(person, "subject.add", name="Welding", category="Trade skills") == "Added the subject Welding."
    subject = screen(person)["subjects"][0]
    act(person, "course.add", subject_id=subject["id"], name="MIG basics")
    course = screen(person)["subjects"][0]["courses"][0]
    act(person, "lesson.add", course_id=course["id"], name="Safety")
    act(person, "lesson.add", course_id=course["id"], name="Bead on plate")
    first = screen(person)["subjects"][0]["courses"][0]["lessons"][0]
    assert act(person, "lesson.done", lesson_id=first["id"]) == "Safety: done."
    shown = screen(person)["subjects"][0]
    assert (shown["done"], shown["total"]) == (1, 2) and shown["courses"][0]["lessons"][0]["done_at"]
    assert act(person, "lesson.done", lesson_id=first["id"], done="no") == "Safety: not done yet."
    act(person, "subject.delete", subject_id=subject["id"])
    assert screen(person)["subjects"] == []  # with its courses and lessons


def test_what_it_refuses(person):
    with pytest.raises(ActionError):
        person.actions.propose(person, "subject.add", {"name": "  "}, proposed_by="person")
    with pytest.raises(ActionError):
        person.actions.propose(person, "course.add", {"subject_id": "nope", "name": "X"}, proposed_by="person")
    assert screen(SimpleNamespace(classroom=None)) == {"available": False, "subjects": [], "continue": None}


def test_continue_is_the_course_you_last_finished_a_lesson_in():
    from core.classroom_manager import continue_course

    def lesson(name, done_at=""):
        return {"id": name, "name": name, "done": bool(done_at), "done_at": done_at, "xp": 30}
    circuits = {"id": "c1", "name": "Basic circuits", "done": 2, "total": 4,
                "lessons": [lesson("Ohm's law", "2026-11-01"), lesson("Meters", "2026-11-05"), lesson("Series"), lesson("Schematics")]}
    soldering = {"id": "c2", "name": "Soldering", "done": 1, "total": 2, "lessons": [lesson("Irons", "2026-10-01"), lesson("Joints")]}
    finished = {"id": "c3", "name": "Safety", "done": 1, "total": 1, "lessons": [lesson("Gloves", "2026-11-06")]}
    subjects = [{"name": "Electronics", "courses": [soldering, circuits, finished]}]
    got = continue_course(subjects)
    assert (got["course"], got["subject"], got["done"], got["total"]) == ("Basic circuits", "Electronics", 2, 4)
    assert [l["name"] for l in got["lessons"]] == ["Meters", "Series", "Schematics"]  # the last done, then what's next
    assert continue_course([{"name": "Math", "courses": [finished]}]) is None  # nothing left
