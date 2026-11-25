"""
tests.test_next_lesson_reply
==============================

"What's my next guitar lesson?" answered in code, read only (core/assistant_path_actions.next_lesson_reply; live
sweep, 2026-11-25): a course named and started gets its next step from his own path, one not started says so and
how to start it, a course named by its id as a word counts ("my next money lesson"), and with no course named it
isn't this route's.
"""

from types import SimpleNamespace

from core import paths
from core.assistant_path_actions import next_lesson_reply
from core.money_path import PROGRAM as MONEY


def test_a_course_named_gets_its_next_step_or_how_to_start_it(tmp_path):
    book = paths.PathBook(None, data_dir=tmp_path)
    context = SimpleNamespace(paths=book)
    assert next_lesson_reply(context, "What's my next guitar lesson?") == \
        "You haven't started Guitar yet. Say \"I want to learn guitar\" and I'll set it up with you."
    assert "learn carpentry\"" in next_lesson_reply(context, "what's the next lesson in carpentry?")
    book.start(MONEY, "")
    assert next_lesson_reply(context, "What's my next money lesson?").startswith("Money basics, stage 1")


def test_no_course_named_or_a_board_course_isnt_this_routes(tmp_path):
    context = SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path))
    for words in ("What's my next step?", "what's next?", "What's my next Arduino lesson?", "next week's lesson plan"):
        assert next_lesson_reply(context, words) is None, words
