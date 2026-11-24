"""Courses from her offline library (core/library_course.py): "I want to learn about beekeeping" builds a Classroom
course, one lesson a stage the library covers, each from one article never used twice and only one that fits the
subject; too little in the library is said, never padded; no library is said with a learning path offered; and the
next lesson is read from its own article to teach, nothing added."""

from types import SimpleNamespace

import pytest

from core import library_course as lc
from core import offline_library
from core.classroom_manager import ClassroomManager

ARTICLES = {
    "beekeeping": [("Beekeeping", "Beekeeping is the keeping of honey bee colonies in hives.")],
    "beekeeping basics introduction": [("Beekeeping", "dup"), ("Western honey bee", "Beekeeping keeps the western "
                                                                                     "honey bee in hives.")],
    "beekeeping tools equipment materials": [("Smoker (beekeeping)", "A beekeeping smoker calms the bees.")],
    "beekeeping safety hazards precautions": [("Bee sting", "A bee sting injects venom; beekeeping suits protect.")],
    "beekeeping history": [("Bread", "Bread is baked from dough.")],  # doesn't fit: left out
}


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A Classroom and a library whose search answers from ARTICLES."""
    from tests.engine_world import build_world

    w = build_world(tmp_path, monkeypatch)
    w.classroom = ClassroomManager(w, data_dir=w.home_dir)
    w.reference_library = SimpleNamespace(list_packs=lambda: ["wikipedia"])
    monkeypatch.setattr(offline_library, "passages", lambda lib, q, keep=4: [
        {"pack": "wikipedia", "article": a, "text": t, "ref": f"wikipedia/{a}"} for a, t in ARTICLES.get(q, [])])
    monkeypatch.setattr(offline_library, "read_further",
                        lambda lib, ref, focus="": f"[From her offline library] the text of {ref}")
    return w


def test_a_course_is_built_a_lesson_a_stage_from_fitting_articles_never_twice(world):
    lessons = lc.outline(world.reference_library, "beekeeping")
    assert [(x["stage"], x["article"]) for x in lessons] == [
        ("What it is", "Beekeeping"), ("The basics", "Western honey bee"),
        ("Tools and materials", "Smoker (beekeeping)"), ("Safety", "Bee sting")]
    said = lc.make(world, "I want to learn about beekeeping")
    assert "4 lessons" in said and "teach me the next lesson on beekeeping" in said
    [course] = lc._courses(world.classroom)
    assert course.name == "Beekeeping" and "ref: wikipedia/Beekeeping" in world.classroom.lessons_for_course(
        course.course_id)[0].notes


def test_the_next_lesson_is_read_from_its_own_article_to_teach(world):
    lc.make(world, "I want to learn about beekeeping")
    said = lc.teach(world, "teach me the next lesson on beekeeping")
    assert "lesson 1 of 4: 1. What it is: Beekeeping" in said and "the text of wikipedia/Beekeeping" in said
    assert "Never add facts the text doesn't have" in said


def test_too_little_in_the_library_or_no_library_is_said_never_padded(world, monkeypatch):
    assert "doesn't cover quantum chromodynamics well enough" in lc.make(world, "learn about quantum chromodynamics")
    world.reference_library = None
    said = lc.make(world, "I want to learn about beekeeping")
    assert "can't build a course on beekeeping here" in said and "start learning beekeeping" in said
    assert lc._courses(world.classroom) == []


def test_learning_about_something_reaches_the_course_and_learning_to_play_reaches_a_path():
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    names = lambda said: [a.name for a in registry.matching_actions(said, context)]  # noqa: E731
    assert "learn_about" in names("I want to learn about beekeeping")
    assert "start_learning" in names("I want to learn to play guitar")
