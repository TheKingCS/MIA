"""
tests.test_lesson_named_course
================================

A lesson asked for by its course's name (core/assistant_path_actions.py; live check, 2026-11-25): a course he hasn't
started is said as not started, never swapped for the one he has; with no course named, his one started course's
next lesson, as before.
"""

from types import SimpleNamespace

from core import assistant_path_actions as actions
from core import paths
from core.money_path import PROGRAM as MONEY


def test_a_course_he_hasnt_started_is_said_not_swapped_for_the_one_he_has(tmp_path):
    """Money basics started: "small business basics" says it isn't started and how; nothing named, or "money": Money
    basics' first lesson."""
    book = paths.PathBook(None, data_dir=tmp_path)
    book.start(MONEY, "")
    context = SimpleNamespace(paths=book)
    said = actions._action_lesson(context, {"path": "small business basics", "topic": "small business basics"})
    assert said.startswith("You haven't started Small business basics yet.")
    assert actions._action_lesson(context, {}).startswith("See where it goes.")
    assert actions._action_lesson(context, {"path": "money"}).startswith("See where it goes.")
