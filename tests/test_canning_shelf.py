"""
tests.test_canning_shelf
==========================

The canning shelf (core/canning_shelf.py): "I put up 7 quarts of tomatoes" adds a dated batch to the pantry, best by
a year on, a second batch the same month joins it, and the shelf is read back oldest first with the ones past or
nearing a year said first and the never-taste-a-bad-jar line always; bought cans are never on it; realistic
phrasing ("7 quart jars of tomatoes", "a dozen pints", "pinto beans") finds the right food, size and count.
And a batch put up by voice grows the Preserving (Canning) skill.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from core import canning_shelf as cs
from core.kitchen_manager import KitchenManager

DAY = date(2026, 11, 23)


@pytest.fixture
def kitchen(tmp_path):
    """A kitchen store of its own, in a temporary folder."""
    return KitchenManager(SimpleNamespace(config=None), data_dir=tmp_path)


def test_a_batch_is_dated_and_best_by_a_year_on(kitchen):
    item = cs.put_up(kitchen, "tomatoes", 7, "quart jars", DAY)
    assert item.name == "Tomatoes, quarts, Nov 2026" and item.quantity == 7
    assert item.expiration_date == "2027-11-23" and "put up 2026-11-23" in item.notes
    again = cs.put_up(kitchen, "Tomatoes", 4, "quarts", DAY)
    assert again.item_id == item.item_id and again.quantity == 11  # the same batch, never a twin


def test_the_size_is_read_from_the_food_when_not_given_and_half_pints_arent_pints():
    assert cs.size_of("half-pint jars") == "half-pints" and cs.size_of("pints") == "pints"
    assert cs.size_of("dilly beans") == ""


def test_nothing_put_up_and_nothing_asked_for_changes_nothing(kitchen):
    with pytest.raises(ValueError):
        cs.put_up(kitchen, "", 3, "pints", DAY)
    with pytest.raises(ValueError):
        cs.put_up(kitchen, "peaches", 0, "pints", DAY)
    assert kitchen.all_pantry_items() == []


def test_the_shelf_says_the_oldest_first_and_never_counts_bought_cans(kitchen):
    cs.put_up(kitchen, "green beans", 9, "pints", date(2025, 10, 1))  # past a year
    cs.put_up(kitchen, "salsa", 6, "pints", date(2025, 12, 20))  # nearing it
    cs.put_up(kitchen, "peaches", 5, "quarts", DAY)
    kitchen.add_pantry_item("Canned corn", quantity=4, unit="cans", expiration_date="2027-01-01")
    batches = cs.shelf(kitchen.all_pantry_items(), DAY)
    assert [b["state"] for b in batches] == ["past", "soon", "fine"]
    said = cs.say(SimpleNamespace(kitchen=kitchen), DAY)
    assert said.startswith("20 jars on the canning shelf, in 3 batches.")
    assert "Green beans, pints, Oct 2025" in said and "Nearing a year: Salsa" in said
    assert "Canned corn" not in said and cs.SAFETY in said


def test_an_empty_shelf_says_how_to_start():
    assert "Nothing home-canned" in cs.say(SimpleNamespace(kitchen=None), DAY)


def test_realistic_phrasing_finds_the_food_size_and_count():
    assert cs.size_of("pinto beans") == "" and cs.size_of("quartered peaches") == ""
    assert cs.size_of("qt") == "quarts" and cs.size_of("gallon of pickles") == "gallons"
    assert cs.food_of("7 quart jars of tomatoes") == "tomatoes"
    assert cs.food_of("a dozen pints of dilly beans") == "dilly beans"
    assert cs.food_of("cream of mushroom soup") == "cream of mushroom soup"
    assert cs.count_of("a dozen") == 12 and cs.count_of("seven") == 7 and cs.count_of(5) == 5


def test_the_same_food_said_two_ways_is_one_batch(kitchen):
    first = cs.put_up(kitchen, "7 quart jars of tomatoes", 7, "", DAY)
    again = cs.put_up(kitchen, "tomatoes", 2, "quarts", DAY)
    assert first.name == "Tomatoes, quarts, Nov 2026" and again.item_id == first.item_id


def test_a_batch_put_up_by_voice_grows_the_preserving_skill(tmp_path, monkeypatch):
    """Canning is a skill (brainstorm round 9): put_up_jars grants XP toward Preserving (Canning), as eggs grow Animal
    Care; the skill is in the tree under Food Production."""
    from core.assistant_domain_actions import _action_put_up_jars
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    skill = world.skills.get_skill("preserving")
    assert skill is not None and skill.prerequisite_skill_ids == ["food_production"]
    before = world.skills.get_progress(world.me.profile_id, "preserving").total_xp
    _action_put_up_jars(world, {"food": "tomatoes", "jars": 7, "size": "quarts"})
    assert world.skills.get_progress(world.me.profile_id, "preserving").total_xp > before
