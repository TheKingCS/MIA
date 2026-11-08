"""The Classroom's web screen (core/classroom_manager.screen, with the course to continue: DEC-0113) and its actions
(core/classroom_actions.py), and a lesson's notes both ways: lesson.notes on the screen, add_lesson_notes and
get_lesson_notes by voice; the skill a lesson trains (lesson.skill, set_lesson_skill)."""

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
    assert screen(SimpleNamespace(classroom=None)) == {"available": False, "subjects": [], "continue": None,
                                                       "skills": []}


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


def test_a_lessons_notes_are_shown_saved_from_the_screen_and_read_back_by_voice(person):
    from core.assistant_life_actions import _action_add_lesson_notes, _action_get_lesson_notes

    act(person, "subject.add", name="Welding")
    act(person, "course.add", subject_id=screen(person)["subjects"][0]["id"], name="MIG basics")
    act(person, "lesson.add", course_id=screen(person)["subjects"][0]["courses"][0]["id"], name="Bead on plate")
    lesson = screen(person)["subjects"][0]["courses"][0]["lessons"][0]
    assert lesson["notes"] == ""
    assert act(person, "lesson.notes", lesson_id=lesson["id"], notes="Push angle 10 degrees") == \
        "Saved your notes for Bead on plate."
    assert _action_add_lesson_notes(person, {"lesson": "bead on plate", "notes": "Listen for the sizzle"}) == \
        "Added to your Bead on plate notes."
    shown = screen(person)["subjects"][0]["courses"][0]["lessons"][0]["notes"]
    assert shown.splitlines() == ["Push angle 10 degrees", "Listen for the sizzle"]
    assert _action_get_lesson_notes(person, {"lesson": "bead"}) == \
        "Your notes for Bead on plate: Push angle 10 degrees / Listen for the sizzle"
    assert act(person, "lesson.notes", lesson_id=lesson["id"], notes="  ") == "Cleared your notes for Bead on plate."
    assert _action_get_lesson_notes(person, {"lesson": "bead"}) == "There are no notes on Bead on plate yet."


def test_the_skill_a_lesson_trains_is_set_on_the_screen_and_by_voice(person):
    from types import SimpleNamespace

    from core.assistant_life_actions import _action_set_lesson_skill

    welding = SimpleNamespace(skill_id="welding", name="Welding")
    person.skills = SimpleNamespace(all_skills=lambda: [welding],
                                    get_skill=lambda i: welding if i == "welding" else None)
    act(person, "subject.add", name="Trade skills")
    act(person, "course.add", subject_id=screen(person)["subjects"][0]["id"], name="MIG basics")
    act(person, "lesson.add", course_id=screen(person)["subjects"][0]["courses"][0]["id"], name="Bead on plate")
    page = screen(person)
    lesson = page["subjects"][0]["courses"][0]["lessons"][0]
    assert page["skills"] == [{"id": "welding", "name": "Welding"}] and lesson["skill"] is None
    assert act(person, "lesson.skill", lesson_id=lesson["id"], skill_id="welding", xp="20") == \
        "Bead on plate trains Welding now."
    shown = screen(person)["subjects"][0]["courses"][0]["lessons"][0]
    assert shown["skill"] == {"id": "welding", "name": "Welding", "xp": 20} and shown["xp"] == 20
    with pytest.raises(ActionError, match="1 to 100"):
        person.actions.propose(person, "lesson.skill", {"lesson_id": lesson["id"], "skill_id": "welding", "xp": "500"},
                               proposed_by="person")
    assert _action_set_lesson_skill(person, {"lesson": "bead", "skill": "none"}) == "Bead on plate trains no skill now."
    assert _action_set_lesson_skill(person, {"lesson": "bead", "skill": "welding", "xp": 15}) == \
        "Bead on plate trains Welding now."
    assert screen(person)["subjects"][0]["courses"][0]["lessons"][0]["skill"]["xp"] == 15
