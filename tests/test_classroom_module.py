"""
tests.test_classroom_module
===============================

Unit tests for modules.classroom.module's pure functions, same style
as tests/test_pathway_tool.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.classroom_manager import Course, Lesson, Subject
from modules.classroom.module import (
    format_completion_summary,
    format_course_row,
    format_lesson_row,
    format_subject_row,
)


def test_format_completion_summary_with_lessons():
    assert format_completion_summary(2, 5) == "2 of 5 complete"


def test_format_completion_summary_with_no_lessons():
    assert format_completion_summary(0, 0) == "No lessons yet"


def test_format_subject_row_with_category():
    subject = Subject(subject_id="s1", name="Geometry", category="Mathematics")
    assert format_subject_row(subject, 1, 2) == "Geometry [Mathematics] — 1 of 2 complete"


def test_format_subject_row_without_category():
    subject = Subject(subject_id="s1", name="Geometry")
    assert format_subject_row(subject, 0, 0) == "Geometry — No lessons yet"


def test_format_course_row():
    course = Course(course_id="c1", subject_id="s1", name="Intro")
    assert format_course_row(course, 3, 3) == "Intro — 3 of 3 complete"


def test_format_lesson_row_incomplete():
    lesson = Lesson(lesson_id="l1", course_id="c1", name="First Lesson")
    assert format_lesson_row(lesson) == "○ First Lesson"


def test_format_lesson_row_complete():
    lesson = Lesson(lesson_id="l1", course_id="c1", name="First Lesson", completed=True)
    assert format_lesson_row(lesson) == "✓ First Lesson"
