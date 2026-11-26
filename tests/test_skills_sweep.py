"""
tests.test_skills_sweep
=========================

The skills live sweep's fixes (brainstorm round 19, 2026-11-26): her lessons for tying down a load, the chainsaw and
storing roots; "the sheet itself shows" never said; a week-long outage asked ahead; garlic from his first fall frost.
"""

from datetime import date
from types import SimpleNamespace

from core import lesson_answer, outage_plan, planting_now
from core.response_composer import without_sheet_words


def test_the_new_lessons_are_found():
    assert lesson_answer.find("What knot should I use to tie down a load?") == ("bushcraft", "knots")
    assert lesson_answer.find("How do I sharpen my chainsaw?") == ("carpentry", "chainsaw")
    assert lesson_answer.find("What's the best way to store potatoes over winter?") == ("gardening", "dry_store")
    assert lesson_answer.find("how do I tie a fishing hook?") != ("bushcraft", "knots")


def test_sheet_words_and_the_outage():
    said = without_sheet_words("The most pressing thing the sheet itself shows is the node. Cut the sheet of plywood.")
    assert "sheet itself" not in said and "sheet of plywood" in said
    assert outage_plan._ASKED.search("What should I do if the power is out for a week?")


def test_garlic_from_his_first_frost():
    config = SimpleNamespace(get=lambda k, d=None: "October 15" if k == "garden.first_frost" else d)
    said = planting_now.say_garlic(SimpleNamespace(config=config), date(2026, 9, 20))
    assert said.startswith("Garlic goes in this fall, from about your first frost (Oct 15) to Nov 12")
    late = planting_now.say_garlic(SimpleNamespace(config=config), date(2026, 11, 26))
    assert late.startswith("Garlic's window this fall was about Oct 15 to Nov 12")
    assert "Tell me your first fall frost" in planting_now.say_garlic(SimpleNamespace(), date(2026, 9, 20))
