"""
tests.test_hobby_progress
===========================

His hobbies' progress (core/hobby_progress.py, 2026-11-25): this month's practice on each course, the fish caught and
the best, the workouts and the project hours, in one answer; "how are my hobbies going?" reaches it.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, hobby_progress


def test_the_month_is_said_across_his_hobbies(monkeypatch):
    monkeypatch.setattr(hobby_progress, "month", lambda c, t=None: {
        "paths": [{"name": "Guitar", "minutes": 200, "days": 9, "stage": 2, "stages": 5},
                  {"name": "Fishing basics", "minutes": 30, "days": 1, "stage": 4, "stages": 4, "finished": True}],
        "catches": 4, "best": {"species": "Eel", "length": 19, "weight": None},
        "workouts": 11, "projects": [("the shed", 6.0)]})
    said = hobby_progress.say(None)
    assert said == ("This month so far: Guitar: 3 hours 20 minutes over 9 days, stage 2 of 5; Fishing basics: 30 "
                    "minutes over 1 day, finished; 4 fish caught, the best an eel (19 in); 11 workouts. On your "
                    "projects: 6 hours on the shed.")


def test_a_month_with_nothing_logged_says_how_to_start(monkeypatch):
    monkeypatch.setattr(hobby_progress, "month", lambda c, t=None: {"paths": [], "catches": 0, "best": None,
                                                                    "workouts": None, "projects": []})
    assert hobby_progress.say(None).startswith("Nothing logged for your hobbies")


def test_an_empty_context_reads_without_failing():
    """No stores at all is nothing counted, never an error."""
    found = hobby_progress.month(SimpleNamespace(), date(2026, 11, 25))
    assert found["paths"] == [] and found["projects"] == []


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(hobby_progress, "say", lambda c, t=None: "the month")
    for words in ("How are my hobbies going?", "my hobbies this month", "hobby progress",
                  "what have I done for fun this month?", "how are my hobbies going lately?",
                  "how are my hobbies going, MIA?", "hows my hobbies", "how are my hobbies and projects going"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the month", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what are good hobbies for winter") != "the month"
