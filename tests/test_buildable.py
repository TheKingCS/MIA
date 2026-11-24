"""What he could build with what he has (core/buildable.py): the Library's builds laid against the workshop's stock,
the most covered first, each with what's left to buy and its cost (a floor while anything has no price), and plans
with nothing on hand left out. Read-only."""

import pytest

from core import buildable
from tests.test_crafting import shop  # noqa: F401  (the fixture)


@pytest.fixture
def stocked(shop, tmp_path):  # noqa: F811
    """The shop with the Library and lumber for a raised bed in stock (the 4x4 short, the soil unpriced)."""
    from core.plan_library import PlanLibrary

    shop.plans = PlanLibrary(shop, data_dir=tmp_path / "plans", files_dir=tmp_path / "plan_files")
    shop.materials.add_material("2x6 x 8 ft", unit="board", unit_cost=9.5, quantity_on_hand=6)
    shop.materials.add_material("3 in exterior screws", unit="screw", unit_cost=0.1, quantity_on_hand=40)
    shop.materials.add_material("4x4 x 8 ft", unit="post", unit_cost=14, quantity_on_hand=0)
    return shop


def test_the_raised_bed_comes_first_with_only_its_post_and_soil_left_to_buy(stocked):
    best = buildable.ranked(stocked)
    assert best[0]["title"] == "Raised garden bed"
    assert best[0]["covered"] == 2 and set(best[0]["to_buy"]) == {"4x4 x 8 ft", "soil and compost mix"}
    said = buildable.say(stocked)
    assert said.startswith("Closest to buildable") and "Raised garden bed: 2 of its 4 materials on hand" in said
    assert "at least $14.00" in said  # the soil has no price: a floor


def test_a_plan_with_nothing_on_hand_is_left_out(stocked):
    assert all(p["covered"] or p["partly"] for p in buildable.ranked(stocked))
    assert "Concrete slab" not in [p["title"] for p in buildable.ranked(stocked)]


def test_with_no_stock_or_no_library_it_says_so(shop, tmp_path):  # noqa: F811
    assert "isn't on this MIA" in buildable.say(shop) or "aren't on this MIA" in buildable.say(shop)
    from core.plan_library import PlanLibrary

    shop.plans = PlanLibrary(shop, data_dir=tmp_path / "p", files_dir=tmp_path / "f")
    assert "no materials logged yet" in buildable.say(shop)


def test_asking_what_can_i_build_reaches_it(stocked):
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    for said in ("what can I build with what I have?", "what could I build with the lumber in the shop"):
        assert "what_can_i_build" in [a.name for a in registry.matching_actions(said, stocked)], said
