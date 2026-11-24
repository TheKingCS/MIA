"""
tests.test_planting_now
=========================

What to plant now and when to plant one crop (core/planting_now.py), from his last spring frost: each crop's next
step (start indoors, transplant or sow) and its date, a step just past still fine, a window long past said so, the
coming spring used once this one is well behind, and his frost date asked for when it isn't known.
"""

from datetime import date
from types import SimpleNamespace

from core import planting_now as pn
from core.garden_plans import CROPS


def _ctx(frost=""):
    """A context whose settings hold his last frost, if any."""
    return SimpleNamespace(config=SimpleNamespace(get=lambda k, d=None: frost if k == "garden.last_frost" else d))


def test_a_crop_says_its_next_step_and_date():
    frost = date(2027, 4, 20)
    tomato = pn.window(CROPS["tomato"], frost, date(2027, 2, 25))
    assert tomato["step"] == "start indoors" and tomato["on"] == date(2027, 3, 2)
    assert pn.window(CROPS["tomato"], frost, date(2027, 7, 1))["step"] == "past"


def test_in_november_the_coming_spring_counts():
    said = pn.say_crop(_ctx("April 20"), "when should I plant tomatoes?", date(2026, 11, 24))
    assert said.startswith("Tomatoes: start indoors in") and "Mar 2" in said


def test_now_lists_whats_due_and_his_frost_is_asked_for():
    due = pn.now(date(2027, 4, 20), date(2027, 3, 1))
    assert any(x["name"] == "Tomatoes" and x["step"] == "start indoors" for x in due)
    assert "When's your last spring frost?" in pn.say_now(_ctx(), date(2027, 3, 1))
