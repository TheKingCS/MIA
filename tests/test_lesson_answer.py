"""
tests.test_lesson_answer
==========================

A how-to answered from one of MIA's own courses (core/lesson_answer.py; live sweep, 2026-11-25): a fire in the rain,
water from a creek, a chisel, seeds indoors, a tape measure, a first woodworking piece, each its lesson's steps, why
and what to watch for, with a drill to practise it and how to start a course he hasn't; never a when, a watering
question or a project for his business. Also the sweep's plan fixes: a beginner project, a survival how-to and his
net worth are never his projects', the project picture's or the products', and "The Dungeon." is taken off an answer.
"""

from types import SimpleNamespace

from core import lesson_answer as la
from core import paths
from core import question_plans as plans
from core.bushcraft import PROGRAM as BUSHCRAFT


def test_each_how_to_finds_its_lesson_and_nothing_else_does():
    for words, key in (("What's the best way to start a fire in the rain?", ("bushcraft", "fire")),
                       ("How do I purify water from a creek?", ("bushcraft", "water")),
                       ("How do I sharpen a chisel?", ("woodworking", "sharpening")),
                       ("How do I start pepper seeds indoors?", ("gardening", "seed_starting")),
                       ("how do I read a tape measure", ("carpentry", "tape")),
                       ("how do I check if a wall is plumb", ("carpentry", "square_level")),
                       ("What's a good beginner woodworking project?", ("woodworking", "first_piece"))):
        assert la.find(words) == key, words
    for words in ("how do I water the tomatoes?", "When should I start tomato seeds?", "I want to build a fire pit",
                  "What's a good first project for my business?", "start a fire drill"):
        assert la.find(words) is None, words


def test_the_answer_is_the_lessons_own_with_its_drill_and_how_to_start(tmp_path):
    book = paths.PathBook(None, data_dir=tmp_path)
    context = SimpleNamespace(paths=book)
    said = la.reply(context, "How do I purify water from a creek?")
    assert said.startswith('From the Survival and bushcraft course, "Making water safe": Bring it to a rolling boil')
    assert "Watch for:" in said and 'say "give me a water drill"' in said
    assert 'say "I want to learn survival and bushcraft" to start it' in said
    book.start(BUSHCRAFT, "")
    assert "to start it" not in la.reply(context, "How do I purify water from a creek?")
    assert la.reply(context, "how are you today?") is None


def test_the_sweeps_plan_fixes_hold():
    assert plans.NOT_FOR["projects"].search("What's a good beginner woodworking project?")
    assert not plans.NOT_FOR["projects"].search("Which of my projects needs the most attention?")
    assert plans.NOT_FOR["products"].search("What's my net worth?")
    assert plans.NOT_FOR["project picture"].search("What's the best way to start a fire in the rain?")
    sheet = SimpleNamespace(facts=[SimpleNamespace(source="the Dungeon (their job)")])
    assert plans.without_source_label("The Dungeon. A good first project is a box.", sheet) == "A good first project is a box."
    assert plans.without_source_label("The Dungeon was cleared this week.", sheet) == "The Dungeon was cleared this week."
