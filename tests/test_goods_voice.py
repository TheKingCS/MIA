"""Saying it to MIA (core/assistant_goods_actions.py): eggs, goods on hand,
a sale, deadlines and freedom, through the same code as their screens."""

from datetime import date, timedelta

from core.assistant_goods_actions import _get_deadlines, _get_eggs, _get_freedom, _get_goods, _log_eggs, _sell_goods
from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


def test_the_homestead_by_voice(shop):  # noqa: F811
    from core.business_book import BusinessBook
    from core.flock import FlockBook
    from core.obligations import ObligationBook

    w = shop
    w.business, w.flock = BusinessBook(w, data_dir=w.home_dir), FlockBook(w, data_dir=w.home_dir)
    w.obligations = ObligationBook(w, data_dir=w.home_dir)
    assert _get_eggs(w, {}).startswith("No flock in MIA yet")
    do(w, "flock.add", name="Layers", hens=10)
    assert _log_eggs(w, {"count": 9}) == "9 eggs logged. 9 loose on hand."
    assert _get_eggs(w, {}).startswith("Layers: 9 eggs today, 9 this week")

    do(w, "craft_recipe.add", name="Banana bread", price=9, makes=2, makes_unit="loaves", shelf_days=4)
    recipe = w.craft_recipes.all_recipes()[0]
    do(w, "goods.add", recipe_id=recipe.recipe_id, quantity=4)
    assert _get_goods(w, {}) == "On hand: 4 loaves of Banana bread."
    assert _sell_goods(w, {"item": "banana bread", "quantity": 3}) == "Sold 3 loaves of Banana bread: $27.00."
    assert _sell_goods(w, {"item": "banana bread", "quantity": 5}).startswith("Banana bread: only 1 loaf left")
    assert _sell_goods(w, {"item": "kombucha"}).startswith("Which of your goods?")

    assert _get_deadlines(w, {}).startswith("Nothing on your Compliance list yet")
    due = (date.today() + timedelta(days=20)).isoformat()
    w.obligations.add("Estimated tax", kind="tax payment", due_date=due, status="applies", verified_on="2026-10-01")
    assert _get_deadlines(w, {}).startswith("Estimated tax in ")
    assert _get_freedom(w, {}).startswith("Set what a month of living takes")
    assert "$0.00 of $0.00" not in _get_freedom(w, {})
