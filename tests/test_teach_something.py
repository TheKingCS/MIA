"""
tests.test_teach_something
============================

"Teach me something" (core/teach_something.py, brainstorm round 18): a lesson from her own courses, his own stage when
he's on one, a first lesson with how to start one when he isn't; never a model's trivia.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, teach_something


def test_with_no_course_started_a_first_lesson_and_how_to_start():
    said = teach_something.say(SimpleNamespace(), date(2026, 11, 26))
    assert said.startswith("From ") and "Say \"start " in said and "Why:" in said


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(teach_something, "say", lambda c, t=None: "a lesson")
    for words in ("Teach me something", "teach me something new", "what can I learn today?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "a lesson", words
