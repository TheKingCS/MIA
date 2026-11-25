"""Harvests by voice (core/harvest_log.py): a harvest goes on his growing batch of that crop (plurals alike), a crop
not in the grow lab gets a batch dated by him first, two batches of it are asked about, a place none is in is a new
one, eggs and honey aren't crops; this year's harvest adds up by crop and unit, valued only at a price he recorded in
the same unit, beside what its plantings cost, with the greenhouse node's produce in it and its fish said apart; and
sentences that aren't a harvest don't bring its tools."""

from datetime import date

import pytest

from core import harvest_log as hl
from core.price_book import PriceBook
from tests.test_grow_lab import lab  # noqa: F401  (the fixture)

TODAY = date.today()


@pytest.fixture
def garden(lab):  # noqa: F811
    """The grow lab world with a price book and the desktop's tools."""
    from tests.assistant_registry import build_desktop_registry

    lab.prices = PriceBook(lab, data_dir=lab.home_dir)
    lab.assistant_actions = build_desktop_registry()
    return lab


@pytest.mark.parametrize("a, b, same", [("tomatoes", "Tomato", True), ("peas", "Pea", True),
                                        ("radishes", "radish", True), ("green beans", "Green bean", True),
                                        ("lettuce", "Lettuce", True), ("beans", "peas", False),
                                        ("strawberries", "Strawberry", True), ("leaves", "leaf", True)])
def test_crop_names_are_the_same_crop_whatever_their_plural(a, b, same):
    assert hl._same_crop(a, b) is same


def test_a_harvest_goes_on_the_growing_batch_of_that_crop(garden):
    b = garden.grow_lab.add_batch("Tomato")
    said = hl.log(garden, "tomatoes", 5, "pounds")
    assert "recorded" in said.lower()
    assert garden.grow_lab.get_batch(b.batch_id).harvests[0]["amount"] == 5
    assert garden.grow_lab.get_batch(b.batch_id).harvests[0]["unit"] == "lb"


def test_a_crop_not_in_the_grow_lab_gets_a_batch_dated_by_him_never_by_a_guess(garden):
    assert "When did you plant it" in hl.log(garden, "zucchini", 3, "each")
    assert garden.grow_lab.batches == []
    said = hl.log(garden, "zucchini", 3, "each", where="Bed 3", planted="2026-05-10")
    assert said.startswith("No zucchini was in the grow lab, so I added a batch of it.")
    b = garden.grow_lab.batches[0]
    assert (b.crop, b.planted) == ("zucchini", "2026-05-10") and "bed 3" in garden.grow_lab.place_name(b.asset_id or b.system).lower()


def test_eggs_and_honey_are_not_crops(garden):
    assert hl.log(garden, "eggs", 12).startswith("Eggs go to the Chickens")
    assert "pantry" in hl.log(garden, "honey", 3, "quarts")
    assert garden.grow_lab.batches == []


def test_a_place_none_of_its_batches_is_in_is_a_new_batch_there(garden):
    garden.grow_lab.add_batch("Kale", system="Tank A")
    assert "When did you plant it" in hl.log(garden, "kale", 2, "bunches", where="Bed 9")
    assert garden.grow_lab.batches[0].harvests == []


def test_two_batches_of_a_crop_are_asked_about(garden):
    garden.grow_lab.add_batch("Lettuce", system="Tank A")
    garden.grow_lab.add_batch("Lettuce", system="Bed 2")
    assert "Which one was it?" in hl.log(garden, "lettuce", 2, "heads")
    assert "recorded" in hl.log(garden, "lettuce", 2, "heads", where="tank a").lower()


def test_this_years_harvest_adds_up_by_crop_and_is_valued_only_at_a_price_in_the_same_unit_beside_its_cost(garden):
    garden.grow_lab.add_batch("Tomato", cost=6)
    garden.grow_lab.add_batch("Kale")
    hl.log(garden, "tomato", 4, "lb", last=True)  # the batch is done...
    garden.grow_lab.add_batch("tomatoes")  # ...and a second planting, spelled otherwise, is one crop with it
    hl.log(garden, "tomatoes", 2.5, "lbs")
    hl.log(garden, "kale", 3, "bunches")
    garden.prices.record("tomatoes", "the market", 3.0, 1, "lb")
    rows = {r["crop"]: r for r in hl.year(garden, TODAY)}
    assert rows["Tomato"]["amount"] == 6.5 and rows["Tomato"]["value"] == 19.5
    assert rows["Kale"]["value"] is None
    said = hl.say_year(garden, TODAY)
    assert "Tomato: 6.5 lb" in said and "$19.50" in said and "No store price recorded in the same unit for Kale" in said
    assert "before the $6.00 its plantings cost" in said
    assert hl._amount({"unit": "cups", "amount": 2}) == "2 cups" and hl._amount({"unit": "dozen", "amount": 3}) == "3 dozen"


@pytest.mark.parametrize("said", ["dug up the old fence post", "how much did I grow my savings",
                                  "when should I harvest the garlic", "what should I plant"])
def test_sentences_that_arent_a_harvest_dont_bring_its_tools(garden, said):
    names = [a.name for a in garden.assistant_actions.matching_actions(said, garden)]
    assert "log_harvest" not in names and "harvest_this_year" not in names, said


def test_saying_a_harvest_reaches_the_tool(garden):
    for said, tool in (("I harvested 5 pounds of tomatoes", "log_harvest"),
                       ("what has the garden produced this year?", "harvest_this_year")):
        assert tool in [a.name for a in garden.assistant_actions.matching_actions(said, garden)], said



def test_the_greenhouse_nodes_harvests_are_in_this_years_total(tmp_path, monkeypatch):
    """Lettuce the node harvested joins the year's produce; its tilapia is said on its own, never priced."""
    from core import greenhouse_link as gl
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    link = gl.GreenhouseLink(world, data_dir=tmp_path / "gh")
    link.state = {"cells": [], "yield": {"events": [
        {"id": 1, "item": "lettuce", "quantity": 3, "unit": "lb", "yield_type": "harvest_produce",
         "timestamp": "2026-11-20 10:00:00"},
        {"id": 2, "item": "tilapia", "quantity": 4, "unit": "lb", "yield_type": "harvest_fish",
         "timestamp": "2026-11-21 10:00:00"}]}}
    gl.keep_harvests(world, link)
    rows = hl.year(world, date(2026, 11, 24))
    assert any(r["crop"] == "Lettuce" and r["amount"] == 3 and not r["fish"] for r in rows)
    said = hl.say_year(world, date(2026, 11, 24))
    assert "Lettuce: 3 lb" in said and "The greenhouse's fish: Tilapia: 4 lb." in said
