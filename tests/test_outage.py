"""
tests.test_outage
===================

The power outage clock (core/outage.py): when he said it went out read in code, the fridge's 4 hours and the
freezer's 24 or 48 said as time left or past, the fish, hens and well only when they apply, and the end said with
what to throw out; by voice and from the Power page.
And a day without safe water (core/water_day.py): what he has and how to make it safe.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from core import outage
from core.actions import ACTION_TYPES
from tests.engine_world import build_world

NOW = datetime(2026, 11, 24, 12, 0)


def test_when_he_says_it_went_out_is_read_and_a_later_hour_is_yesterday():
    """"at 6 am", "at 6:30 pm" (later than now: yesterday), "2 hours ago"; nothing said is None."""
    assert outage.when_said("it went out at 6 am", NOW) == NOW.replace(hour=6)
    assert outage.when_said("at 6:30 pm", NOW) == NOW.replace(hour=18, minute=30) - timedelta(days=1)
    assert outage.when_said("about 2 hours ago", NOW) == NOW - timedelta(hours=2)
    assert outage.when_said("the power went out", NOW) is None


def test_the_fridge_and_freezer_are_said_as_time_left_then_past():
    """1 h in: 3 h left in the fridge; 6 h: the fridge is past; 30 h: a half-full freezer is past, a full one isn't."""
    assert "about 3 h more" in outage.food_lines(1.0)[0]
    assert "past its 4 safe hours" in outage.food_lines(6.0)[0]
    lines = outage.food_lines(30.0)
    assert "half-full freezer is past" in lines[1] and "about 18 h more" in lines[1]


def test_the_clock_starts_and_ends_and_says_only_what_applies(tmp_path, monkeypatch):
    """Started at 9 am: the status counts 3 hours, the generator line is there, and no fish, hens or well (none here);
    ending says the length and what to throw out, and the status then says the power's on."""
    world = build_world(tmp_path, monkeypatch)
    said = outage.start(world, "it went out at 9 am", now=NOW)
    assert said.startswith("The power's been out 3 h (since 09:00)") and "fish" not in said and "well pump" not in said
    world.greenhouse_link = SimpleNamespace(taken_over=True)
    assert "air pump first" in outage.status(world, NOW)
    ended = outage.end(world, now=NOW + timedelta(hours=2))
    assert ended.startswith("The power was out 5 h.") and "went past its 4 safe hours" in ended and "40 F" in ended
    assert outage.since(world) is None and "the power's on" in outage.status(world, NOW)


def test_the_power_page_starts_and_ends_it(tmp_path, monkeypatch):
    """outage.start with a time, then the page shows it out with its status; outage.end clears it."""
    from core.web_power import power_page

    world = build_world(tmp_path, monkeypatch)
    ACTION_TYPES["outage.start"].execute(world, {"when": "8 am"})
    page = power_page(world)
    assert page["outage"]["out"] and "The power's been out" in page["outage"]["status"]
    ACTION_TYPES["outage.end"].execute(world, {})
    assert not power_page(world)["outage"]["out"]


def test_a_day_without_safe_water_says_what_he_has_and_how_to_make_it_safe(tmp_path, monkeypatch):
    """His drinking water in days (or none), never his tanks as drinkable, the CDC's boil and bleach; a boil-water
    notice adds no ice or toothbrushing from the tap."""
    from core import water_day

    world = build_world(tmp_path, monkeypatch)
    said = water_day.say(world)
    assert "I don't see drinking water in the pantry" in said and "rolling boil for 1 minute" in said
    assert "8 drops a gallon" in said and "boil-water notice" not in said
    world.kitchen.add_pantry_item("Drinking water", quantity=7, unit="gallons")
    boil = water_day.say(world, boil=True)
    assert boil.startswith("Under a boil-water notice") and "about 7 days of drinking water" in boil
