"""
tests.test_classroom_manager
================================

Unit tests for core.classroom_manager. Isolates _DATA_DIR/the three
per-level file constants into a tmp_path scratch area, same pattern as
tests/test_workout_manager.py.
"""

from __future__ import annotations

import json

import pytest

import core.classroom_manager as classroom_manager_module
import core.config_manager as config_manager_module
import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.classroom_manager import ClassroomManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.gamification import SkillWeight
from core.profile_manager import ProfileManager
from core.skill_manager import SkillManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(classroom_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(classroom_manager_module, "_SUBJECTS_FILE", data_dir / "classroom_subjects.json")
    monkeypatch.setattr(classroom_manager_module, "_COURSES_FILE", data_dir / "classroom_courses.json")
    monkeypatch.setattr(classroom_manager_module, "_LESSONS_FILE", data_dir / "classroom_lessons.json")
    # Needed once a test constructs a real ProfileManager/SkillManager
    # too (skill-crediting tests below) — without these, that would
    # write to the actual config/config.json and data/skill_*.json.
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    return data_dir


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


# ------------------------------------------------------------------
# Subjects
# ------------------------------------------------------------------

def test_all_subjects_empty_when_no_file_exists(isolated_paths):
    manager = ClassroomManager(_make_context())
    assert manager.all_subjects() == []


def test_add_subject_persists_and_sorts_by_name(isolated_paths):
    manager = ClassroomManager(_make_context())
    manager.add_subject(name="Geometry", category="Mathematics")
    manager.add_subject(name="Electrical", category="Trade Skills")

    names = [s.name for s in manager.all_subjects()]
    assert names == ["Electrical", "Geometry"]


def test_update_subject_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")

    updated = manager.update_subject(subject.subject_id, name="Applied Geometry", description="Real-world math")

    assert updated.name == "Applied Geometry"
    assert updated.description == "Real-world math"
    assert updated.updated_at != ""


def test_update_subject_rejects_created_at(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    with pytest.raises(ValueError):
        manager.update_subject(subject.subject_id, created_at="2020-01-01T00:00:00")


def test_update_subject_unknown_id_raises(isolated_paths):
    manager = ClassroomManager(_make_context())
    with pytest.raises(ValueError):
        manager.update_subject("does-not-exist", name="X")


def test_subjects_persist_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = ClassroomManager(context)
    manager.add_subject(name="Geometry")

    reloaded = ClassroomManager(context)

    assert len(reloaded.all_subjects()) == 1


# ------------------------------------------------------------------
# Courses
# ------------------------------------------------------------------

def test_courses_for_subject_filters_and_sorts(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    other_subject = manager.add_subject(name="Electrical")
    manager.add_course(subject_id=subject.subject_id, name="Z Course")
    manager.add_course(subject_id=subject.subject_id, name="A Course")
    manager.add_course(subject_id=other_subject.subject_id, name="Unrelated")

    names = [c.name for c in manager.courses_for_subject(subject.subject_id)]
    assert names == ["A Course", "Z Course"]


def test_update_course_rejects_subject_id_change(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    with pytest.raises(ValueError):
        manager.update_course(course.course_id, subject_id="different")


# ------------------------------------------------------------------
# Lessons
# ------------------------------------------------------------------

def test_lessons_for_course_sorted_by_creation_order(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    manager.add_lesson(course_id=course.course_id, name="First")
    manager.add_lesson(course_id=course.course_id, name="Second")

    names = [l.name for l in manager.lessons_for_course(course.course_id)]
    assert names == ["First", "Second"]


def test_marking_a_lesson_complete_sets_completed_at_once(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    lesson = manager.add_lesson(course_id=course.course_id, name="First")
    assert lesson.completed_at == ""

    updated = manager.update_lesson(lesson.lesson_id, completed=True)
    first_completed_at = updated.completed_at
    assert first_completed_at != ""

    # Saving again while still completed must not change completed_at.
    updated_again = manager.update_lesson(lesson.lesson_id, notes="edited")
    assert updated_again.completed_at == first_completed_at


def test_marking_a_lesson_incomplete_then_complete_again_resets_completed_at(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    lesson = manager.add_lesson(course_id=course.course_id, name="First")

    manager.update_lesson(lesson.lesson_id, completed=True)
    manager.update_lesson(lesson.lesson_id, completed=False)
    updated = manager.update_lesson(lesson.lesson_id, completed=True)

    assert updated.completed_at != ""


def test_update_lesson_rejects_direct_completed_at_set(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    lesson = manager.add_lesson(course_id=course.course_id, name="First")
    with pytest.raises(ValueError):
        manager.update_lesson(lesson.lesson_id, completed_at="2020-01-01T00:00:00")


# ------------------------------------------------------------------
# Cascading delete
# ------------------------------------------------------------------

def test_deleting_a_course_deletes_its_lessons(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    lesson = manager.add_lesson(course_id=course.course_id, name="First")

    manager.delete_course(course.course_id)

    assert manager.get_course(course.course_id) is None
    assert manager.get_lesson(lesson.lesson_id) is None


def test_deleting_a_subject_deletes_its_courses_and_lessons(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    other_subject = manager.add_subject(name="Electrical")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    lesson = manager.add_lesson(course_id=course.course_id, name="First")
    unrelated_course = manager.add_course(subject_id=other_subject.subject_id, name="Unrelated")

    manager.delete_subject(subject.subject_id)

    assert manager.get_subject(subject.subject_id) is None
    assert manager.get_course(course.course_id) is None
    assert manager.get_lesson(lesson.lesson_id) is None
    # Unrelated subject's own course must survive untouched.
    assert manager.get_course(unrelated_course.course_id) is not None


# ------------------------------------------------------------------
# Derived completion
# ------------------------------------------------------------------

def test_course_completion_with_no_lessons_is_zero_of_zero(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")

    assert manager.course_completion(course.course_id) == (0, 0)


def test_course_completion_counts_completed_lessons(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course = manager.add_course(subject_id=subject.subject_id, name="Intro")
    lesson_1 = manager.add_lesson(course_id=course.course_id, name="First")
    manager.add_lesson(course_id=course.course_id, name="Second")
    manager.update_lesson(lesson_1.lesson_id, completed=True)

    assert manager.course_completion(course.course_id) == (1, 2)


def test_subject_completion_aggregates_across_courses(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")
    course_1 = manager.add_course(subject_id=subject.subject_id, name="Course 1")
    course_2 = manager.add_course(subject_id=subject.subject_id, name="Course 2")
    lesson_1 = manager.add_lesson(course_id=course_1.course_id, name="A")
    manager.add_lesson(course_id=course_1.course_id, name="B")
    lesson_3 = manager.add_lesson(course_id=course_2.course_id, name="C")
    manager.update_lesson(lesson_1.lesson_id, completed=True)
    manager.update_lesson(lesson_3.lesson_id, completed=True)

    assert manager.subject_completion(subject.subject_id) == (2, 3)


def test_subject_completion_with_no_courses_is_zero_of_zero(isolated_paths):
    manager = ClassroomManager(_make_context())
    subject = manager.add_subject(name="Geometry")

    assert manager.subject_completion(subject.subject_id) == (0, 0)


# ------------------------------------------------------------------
# skill_rewards crediting — "Wire Classroom into Hero's Path" (2026-09-12)
# ------------------------------------------------------------------

def _write_skill_definitions(data_dir) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "skill_definitions.json").write_text(
        json.dumps({"skills": [{"skill_id": "electrical", "name": "Electrical", "category": "Trade Skills"}]})
    )


def test_completing_a_lesson_with_skill_rewards_grants_skill_xp(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    context.profiles = ProfileManager(context)
    context.skills = SkillManager(context)
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    manager = ClassroomManager(context)
    subject = manager.add_subject(name="Electrical")
    course = manager.add_course(subject_id=subject.subject_id, name="DC Circuits")
    lesson = manager.add_lesson(
        course_id=course.course_id, name="Ohm's Law", skill_rewards=[SkillWeight(skill_id="electrical", xp=10)],
    )

    manager.update_lesson(lesson.lesson_id, completed=True)

    assert context.skills.get_progress(profile.profile_id, "electrical").total_xp == 10


def test_completing_a_lesson_with_skill_rewards_grants_zero_flat_profile_xp(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    context.profiles = ProfileManager(context)
    context.skills = SkillManager(context)
    context.profiles.create_profile(name="Alex", make_active=True)
    manager = ClassroomManager(context)
    subject = manager.add_subject(name="Electrical")
    course = manager.add_course(subject_id=subject.subject_id, name="DC Circuits")
    lesson = manager.add_lesson(
        course_id=course.course_id, name="Ohm's Law", skill_rewards=[SkillWeight(skill_id="electrical", xp=10)],
    )

    manager.update_lesson(lesson.lesson_id, completed=True)

    assert context.profiles.get_active_profile().total_xp == 0


def test_toggling_a_lesson_complete_incomplete_complete_does_not_recredit(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    context.profiles = ProfileManager(context)
    context.skills = SkillManager(context)
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    manager = ClassroomManager(context)
    subject = manager.add_subject(name="Electrical")
    course = manager.add_course(subject_id=subject.subject_id, name="DC Circuits")
    lesson = manager.add_lesson(
        course_id=course.course_id, name="Ohm's Law", skill_rewards=[SkillWeight(skill_id="electrical", xp=10)],
    )

    manager.update_lesson(lesson.lesson_id, completed=True)
    manager.update_lesson(lesson.lesson_id, completed=False)
    manager.update_lesson(lesson.lesson_id, completed=True)

    assert context.skills.get_progress(profile.profile_id, "electrical").total_xp == 10


def test_completing_a_lesson_with_no_skill_rewards_grants_nothing(isolated_paths):
    _write_skill_definitions(isolated_paths)
    context = _make_context()
    context.profiles = ProfileManager(context)
    context.skills = SkillManager(context)
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    manager = ClassroomManager(context)
    subject = manager.add_subject(name="Electrical")
    course = manager.add_course(subject_id=subject.subject_id, name="DC Circuits")
    lesson = manager.add_lesson(course_id=course.course_id, name="Ohm's Law")

    manager.update_lesson(lesson.lesson_id, completed=True)

    assert context.skills.get_progress(profile.profile_id, "electrical").total_xp == 0


def test_completing_a_lesson_with_no_skills_service_does_not_raise(isolated_paths):
    context = _make_context()
    manager = ClassroomManager(context)
    subject = manager.add_subject(name="Electrical")
    course = manager.add_course(subject_id=subject.subject_id, name="DC Circuits")
    lesson = manager.add_lesson(
        course_id=course.course_id, name="Ohm's Law", skill_rewards=[SkillWeight(skill_id="electrical", xp=10)],
    )

    manager.update_lesson(lesson.lesson_id, completed=True)  # must not raise
