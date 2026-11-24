"""
tests.test_seed_life
======================

How long his seeds keep (core/seed_life.py): each kind's usual span, his dated packets of it said good, worth a
germination test or past it, a plural or another name for a crop understood ("broccoli sprouts" never Brussels
sprouts), a packet naming two crops counted for both, a "packed for" year counted from the year before, and a packet
with no year asked to give one.
"""

from datetime import date
from types import SimpleNamespace

from core import seed_life as sl

TODAY = date(2026, 11, 24)


def test_kinds_are_read_from_how_he_says_them():
    """Plurals and other names, and broccoli sprouts never Brussels sprouts."""
    assert sl.crop_of("are my tomatoes still good") == "tomato" and sl.crop_of("zucchini seeds") == "squash"
    assert sl.crop_of("onion") == "onion" and sl.crop_of("dragon fruit") == ""
    assert sl.crop_of("broccoli sprouts") == "broccoli" and sl.crop_of("brussels sprouts") == "brussels sprout"


def test_his_dated_packets_are_good_worth_a_test_or_old():
    """By age against the span; a two-crop packet counts for both, a packed-for year from the year before."""
    names = ["Tomato seeds 2024", "tomato seeds 2022", "Tomato seed 2019", "Tomato seeds", "Bean seeds 2025"]
    found = sl.packets(names, "tomato", TODAY)
    assert [(p["year"], p["state"]) for p in found] == [(2024, "good"), (2022, "test"), (2019, "old")]
    both = sl.packets(["Tomato & pepper seeds 2024", "Tomato seeds, packed for 2025"], "tomato", date(2026, 11, 24))
    assert [(p["year"], p["age"]) for p in both] == [(2024, 2), (2024, 2)]


def test_the_answer_says_the_span_and_each_packet():
    inventory = SimpleNamespace(all_items=lambda: [SimpleNamespace(name="Onion seeds 2023")])
    said = sl.say(SimpleNamespace(inventory=inventory, kitchen=None), "onion seeds", TODAY)
    assert said.startswith("Onion seed usually stays good about 1 year") and "past its usual span" in said
    assert "give a year" in sl.say(SimpleNamespace(inventory=None, kitchen=None), "beans", TODAY)
