"""Harvests by voice (core/harvest_log.py): a harvest goes on his growing batch of that crop (plurals alike), a crop
not in the grow lab gets a batch first, two batches of it are asked about; and this year's harvest adds up by crop
and unit, valued only at a price he recorded in the same unit."""

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
                                        ("lettuce", "Lettuce", True), ("beans", "peas", False)])
def test_crop_names_are_the_same_crop_whatever_their_plural(a, b, same):
    assert hl._same_crop(a, b) is same


def test_a_harvest_goes_on_the_growing_batch_of_that_crop(garden):
    b = garden.grow_lab.add_batch("Tomato")
    said = hl.log(garden, "tomatoes", 5, "pounds")
    assert "recorded" in said.lower()
    assert garden.grow_lab.get_batch(b.batch_id).harvests[0]["amount"] == 5
    assert garden.grow_lab.get_batch(b.batch_id).harvests[0]["unit"] == "lb"


def test_a_crop_not_in_the_grow_lab_gets_a_batch_first(garden):
    said = hl.log(garden, "zucchini", 3, "each")
    assert said.startswith("No zucchini was in the grow lab, so I added a batch of it.")
    assert [b.crop for b in garden.grow_lab.batches] == ["zucchini"]


def test_two_batches_of_a_crop_are_asked_about(garden):
    garden.grow_lab.add_batch("Lettuce", system="Tank A")
    garden.grow_lab.add_batch("Lettuce", system="Bed 2")
    assert "Which one was it?" in hl.log(garden, "lettuce", 2, "heads")
    assert "recorded" in hl.log(garden, "lettuce", 2, "heads", where="tank a").lower()


def test_this_years_harvest_adds_up_and_is_valued_only_at_a_price_in_the_same_unit(garden):
    garden.grow_lab.add_batch("Tomato")
    garden.grow_lab.add_batch("Kale")
    hl.log(garden, "tomato", 4, "lb")
    hl.log(garden, "tomatoes", 2.5, "lbs")
    hl.log(garden, "kale", 3, "bunches")
    garden.prices.record("tomatoes", "the market", 3.0, 1, "lb")
    rows = {r["crop"]: r for r in hl.year(garden, TODAY)}
    assert rows["Tomato"]["amount"] == 6.5 and rows["Tomato"]["value"] == 19.5
    assert rows["Kale"]["value"] is None
    said = hl.say_year(garden, TODAY)
    assert "Tomato: 6.5 lb" in said and "$19.50" in said and "No store price recorded in the same unit for Kale" in said


def test_saying_a_harvest_reaches_the_tool(garden):
    for said, tool in (("I harvested 5 pounds of tomatoes", "log_harvest"),
                       ("what has the garden produced this year?", "harvest_this_year")):
        assert tool in [a.name for a in garden.assistant_actions.matching_actions(said, garden)], said
