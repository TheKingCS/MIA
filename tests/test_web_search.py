"""
tests.test_web_search
=======================

Search for the web's Ctrl+K (core/web_search.py): how names are ranked, and that results come from the person's
own records with the page each opens.
"""

from types import SimpleNamespace

from core.links import KINDS
from core.web_search import PAGES, score, search, words_of


def test_every_word_must_be_in_the_name():
    assert score("Chicken Coop", ["coop"]) > 0
    assert score("Chicken Coop", ["coop", "roof"]) == 0
    assert score("Anything", []) == 0


def test_the_query_at_the_start_beats_a_word_start_beats_inside_a_word():
    words = words_of("chick")
    assert score("Chicken Coop", words) > score("Feed the chickens", words) > score("Bechick", words) > 0


def test_every_searched_kind_is_in_the_link_catalog():
    assert set(PAGES) <= set(KINDS)


class _Store:
    """A stand-in store listing records."""

    def __init__(self, **lists):
        """Keeps each list under its method name."""
        for name, records in lists.items():
            setattr(self, name, (lambda r: (lambda: r))(records))


def test_results_carry_their_kind_detail_and_page_best_first():
    truck = SimpleNamespace(asset_id="a1", name="F-150 Truck", category="Vehicle")
    trailer = SimpleNamespace(asset_id="a2", name="Utility trailer for the truck", category="")
    chili = SimpleNamespace(recipe_id="r1", name="Truck-stop chili", category="Dinner")
    context = SimpleNamespace(maintenance=_Store(all_assets=[trailer, truck], all_tasks=[]),
                              kitchen=_Store(all_recipes=[chili]))
    found = search(context, "truck")["results"]
    assert [r["title"] for r in found] == ["Truck-stop chili", "F-150 Truck", "Utility trailer for the truck"]
    assert found[0]["href"] == "recipe.html?id=r1" and found[0]["detail"] == "Recipe · Dinner"
    assert found[1]["href"] == "asset.html?id=a1"


def test_too_short_a_query_finds_nothing_and_missing_stores_are_skipped():
    assert search(SimpleNamespace(), "t")["results"] == []
    assert search(SimpleNamespace(), "truck")["results"] == []
