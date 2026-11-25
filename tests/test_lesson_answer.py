"""
tests.test_lesson_answer
==========================

A how-to answered from one of MIA's own courses (core/lesson_answer.py; live sweep, 2026-11-25): a fire in the rain,
water from a creek, a chisel, seeds indoors, a tape measure, a first woodworking piece, each its lesson's steps, why
and what to watch for, with a drill to practise it and how to start a course he hasn't; never a when, a watering
question or a project for his business. Also the sweep's plan fixes: a beginner project, a survival how-to and his
net worth are never his projects', the project picture's or the products', and "The Dungeon." is taken off an answer.
And the business's how-tos (markup, writing a quote) are its course's, his own product's price and margin the plans';
the flock's questions (mites, feed, predators) its lesson's, the step asked about first.
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


def test_the_business_how_tos_find_its_lessons_and_leave_his_own_numbers_to_the_plans(tmp_path):
    """Markup and writing a quote are the business course's lessons, with how to do it with MIA; what he should
    charge for a product of his, or his own margin, stays the product plans' (worked from his records)."""
    assert la.find("What's the markup I should use for my woodworking?") == ("business", "biz_price")
    assert la.find("How do I write a quote for a deck job?") == ("business", "biz_terms")
    for words in ("What should I charge for a cutting board?", "what's my profit margin on cutting boards?",
                  "make a quote for the deck job for Sarah"):
        assert la.find(words) is None, words
    said = la.reply(SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path)), "How do I write a quote for a deck job?")
    assert "say \"make a quote for\"" in said


def test_the_flocks_questions_find_its_lesson_and_lead_with_the_step_asked_about():
    """Mites, feeding hens and predators are the flock lesson's (its mites step new, from the extension guides), the
    step asked about said first; an egg count stays the flock's own record."""
    for words in ("How do I know if my chickens have mites?", "What should I feed laying hens in winter?",
                  "how do I protect my chickens from raccoons?"):
        assert la.find(words) == ("gardening", "flock_care"), words
    assert la.find("How many eggs did my hens lay this week?") is None
    from types import SimpleNamespace as N

    said = la.reply(N(paths=None), "How do I know if my chickens have mites?")
    assert said.startswith('From the Gardening and homesteading course, "Keeping a small flock": Once a month, check each '
                           'bird for mites and lice')
    steps = ("Close the coop.", "Check for mites under the wings.")
    assert la.steps_for(steps, "any mites?") == ["Check for mites under the wings.", "Close the coop."]
    assert la.steps_for(steps, "how do I start?") == list(steps)
