"""The orchard (core/orchard.py): his fruit trees read from Maintenance by the fruit in their names, the year's work
dated from his last spring frost (stone fruit pruned near bloom, dormant oil before bud break, thinning, harvest by
each kind's days from bloom, fall cleanup), a kind alone without its pollination partner named, a missing frost date
asked for, and the questions reaching the tools."""

from datetime import date
from types import SimpleNamespace

import pytest

from core import orchard


def _with(names, last_frost="April 20", first_frost="October 15"):
    """A context whose Maintenance has these assets and whose garden has these frost dates."""
    assets = [SimpleNamespace(asset_id=f"a{i}", name=n) for i, n in enumerate(names)]
    config = SimpleNamespace(get=lambda k, d=None: {"garden.last_frost": last_frost,
                                                    "garden.first_frost": first_frost}.get(k, d))
    return SimpleNamespace(maintenance=SimpleNamespace(all_assets=lambda: assets), config=config)


@pytest.mark.parametrize("name, kind, variety, count", [
    ("Honeycrisp apple tree", "apple", "Honeycrisp", 1), ("2 Elberta peaches", "peach", "Elberta", 2),
    ("Montmorency cherry", "sour cherry", "Montmorency", 1), ("Bing cherry tree", "sweet cherry", "Bing", 1),
    ("Lawn mower", None, None, None),
])
def test_a_tree_is_read_from_how_its_asset_is_named(name, kind, variety, count):
    found = orchard.trees(_with([name]))
    if kind is None:
        assert found == []
    else:
        assert (found[0]["kind"].name, found[0]["variety"], found[0]["count"]) == (kind, variety, count)


def test_the_years_work_is_dated_from_the_frost_and_stone_fruit_is_pruned_near_bloom():
    kinds = [orchard.kind_in("apple"), orchard.kind_in("peach")]
    jobs = {job.split(",")[0].split(" (")[0]: day for day, job, _ in orchard.calendar(kinds, date(2027, 4, 20),
                                                                                    date(2027, 10, 15))}
    assert jobs["Dormant pruning"] == date(2027, 2, 9)  # ten weeks before the frost
    assert jobs["Prune stone fruit near bloom"] == date(2027, 3, 27)  # bloom two weeks before it, ten days earlier
    assert jobs["Fall cleanup: rake dropped fruit and leaves"] == date(2027, 10, 1)


def test_the_next_30_days_and_a_lone_apple_without_its_partner():
    said = orchard.say_month(_with(["Honeycrisp apple tree", "2 Elberta peaches"]), date(2027, 2, 1))
    assert "February 9: Dormant pruning" in said and "Honeycrisp apple tree" in said
    assert "Apple needs a second variety nearby" in said
    two = orchard.say_month(_with(["Honeycrisp apple tree", "Liberty apple tree"]), date(2027, 2, 1))
    assert "second variety" not in two


def test_without_trees_or_a_frost_date_it_says_what_it_needs():
    assert "No fruit trees in your records yet" in orchard.say_month(_with([]), date(2027, 2, 1))
    assert "need your last spring frost" in orchard.say_month(_with(["Honeycrisp apple tree"], last_frost=""),
                                                              date(2027, 2, 1))
    assert "need a second variety" in orchard.say_kind("pear") and "one variety alone" in orchard.say_kind("peach")


def test_orchard_questions_reach_its_tools():
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    names = lambda said: [a.name for a in registry.matching_actions(said, context)]  # noqa: E731
    assert "orchard_this_month" in names("what does the orchard need this month?")
    assert "orchard_this_month" in names("when should I prune the apple trees?")
    assert "fruit_tree_facts" in names("how many chill hours does a peach need?")
