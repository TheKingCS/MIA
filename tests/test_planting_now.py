"""
tests.test_planting_now
=========================

What to plant now and when to plant one crop (core/planting_now.py), from his last spring frost: each crop's next
step (start indoors, transplant or sow) and its date, a step just past still fine, a window long past said so, the
coming spring used once this one is well behind (a date saved with its year too), his frost date asked for when it
isn't known, crops named by whole words ("peanuts" are never peas), a late seed start said as buy transplants, and a
crop sown again and again still sowable until its days before his first frost.
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
    """Said as next spring's, with the tomatoes' March start."""
    said = pn.say_crop(_ctx("April 20"), "when should I plant tomatoes?", date(2026, 11, 24))
    assert "Tomatoes: start indoors in" in said and "Mar 2" in said and said.startswith("This year's spring window")


def test_now_lists_whats_due_and_his_frost_is_asked_for():
    due = pn.now(date(2027, 4, 20), date(2027, 3, 1))
    assert any(x["name"] == "Tomatoes" and x["step"] == "start indoors" for x in due)
    assert "When's your last spring frost?" in pn.say_now(_ctx(), date(2027, 3, 1))


def test_crops_are_named_by_whole_words_the_longest_first():
    assert pn.crop_named("sweet potatoes").id == "sweet_potato" and pn.crop_named("green beans").id == "bean_bush"
    assert pn.crop_named("acorn squash").id == "winter_squash" and pn.crop_named("summer squash").id == "zucchini"
    for said in ("peanuts", "peppermint", "my orchard", "horseradish", "chickpeas"):
        assert pn.crop_named(said) is None, said


def test_a_frost_saved_with_its_year_moves_to_next_spring():
    said = pn.say_crop(_ctx("2026-04-20"), "when should I plant tomatoes?", date(2026, 11, 24))
    assert "This year's spring window has passed; next spring: Tomatoes: start indoors" in said


def test_a_late_seed_start_says_buy_transplants_and_a_resown_crop_still_sows():
    said = pn.say_crop(_ctx("April 20"), "tomatoes", date(2027, 3, 25))
    assert "buy transplants" in said
    both = SimpleNamespace(config=SimpleNamespace(get=lambda k, d=None: {"garden.last_frost": "April 20",
                                                                        "garden.first_frost": "October 15"}.get(k, d)))
    assert "you can still sow them" in pn.say_crop(both, "bush beans", date(2027, 7, 25))
