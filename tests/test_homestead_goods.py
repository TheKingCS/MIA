"""Homestead goods (DEC-0036): batches in kitchen units, stock with a
made date and a sell-by, sold oldest first, leftovers tossed as a loss,
and a market day's tally read from the books."""

from datetime import date, timedelta

import pytest

from core import units
from core.craft_recipes import CraftRecipe, check, makes_text, parse_lines, uses
from core.goods import Lot, demand, fifo, freshness, split_amount
from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


def test_units_convert_within_a_kind_and_never_across():
    assert units.convert(1, "cup", "tbsp") == pytest.approx(16)
    assert units.convert(2, "lbs", "g") == pytest.approx(907.18474)
    assert units.convert(500, "grams", "lb") == pytest.approx(1.1023, abs=1e-4)
    assert units.convert(3, "tsp", "Tablespoons") == pytest.approx(1)
    assert units.convert(2, "dozen", "") == 24 and units.convert(24, "", "dozen") == 2
    assert units.convert(3, "cloves", "clove") == 3 and units.convert(2, "jars", "") == 2
    assert units.convert(1, "cup", "lb") is None  # no density guessing
    assert units.convert(1, "jar", "lid") is None
    assert units.canonical("Loaves") == "loaf" and units.canonical("fl. oz") == "fl oz"
    assert units.amount_text(2, "cup") == "2 cups" and units.amount_text(1, "jar") == "1 jar"
    assert units.amount_text(12, "jar") == "12 jars" and units.amount_text(3, "") == "3"
    assert units.amount_text(6, "loaf") == "6 loaves"


def test_kitchen_lines_parse_and_check_in_the_stocks_own_unit():
    lines = parse_lines("1 cup Raw honey\n3 Chili peppers\n2 cloves Garlic\n500 g Flour\n2 fl oz Lemon juice")
    assert [(l.quantity, l.unit, l.name) for l in lines] == [
        (1, "cup", "Raw honey"), (3, "", "Chili peppers"), (2, "cloves", "Garlic"), (500, "g", "Flour"),
        (2, "fl oz", "Lemon juice")]

    class M:
        def __init__(self, name, q, unit, cost):
            self.material_id = name
            self.name, self.quantity_on_hand, self.unit, self.unit_cost = name, q, unit, cost

    recipe = CraftRecipe(recipe_id="r", name="Hot honey", makes=12, makes_unit="jars",
                         materials="1 cup Raw honey\n3 Chili peppers\n2 cloves Garlic\n1 cup Flour")
    stock = [M("Raw honey", 8.2, "cups", 4.0), M("Chili peppers", 12, "", 0.25), M("Garlic", 6, "cloves", 0.1),
             M("Flour", 5, "lb", 0.6)]
    state = check(recipe, stock, times=2)
    honey, chili, garlic, flour = state["rows"]
    assert (honey["need"], honey["have"], honey["after"], honey["status"]) == (2, 8.2, 6.2, "ok")
    assert (chili["need"], chili["after"]) == (6, 6) and garlic["recipe_text"] == "4 cloves"
    assert flour["mismatch"] and flour["status"] == "check" and not state["ready"]  # cups vs pounds: said, not guessed
    assert state["makes"] == 24 and state["est_material_cost"] == round(2 * 4.0 + 6 * 0.25 + 4 * 0.1, 2)
    assert state["per_piece"] == round(state["est_material_cost"] / 24, 2)
    taken = uses(recipe, stock, 1)
    assert [(m.name, q) for m, q in taken["used"]] == [("Raw honey", 1), ("Chili peppers", 3), ("Garlic", 2)]
    assert taken["mismatched"] == ["Flour (cup vs lb)"]
    assert makes_text(recipe, 2) == "24 jars" and makes_text(CraftRecipe(recipe_id="b", name="Bench"), 2) == "2 × Bench"


def test_freshness_fifo_and_splitting_money():
    today = date(2026, 10, 21)
    lot = lambda made, sell_by, left=5: Lot("j" + made, "r", "Sourdough", made, sell_by, left, 0, 0, 1.0)  # noqa: E731
    assert freshness(lot("2026-10-20", "2026-10-24"), today) == {"state": "fresh", "days_left": 3}
    assert freshness(lot("2026-10-18", "2026-10-22"), today)["state"] == "sell first"
    assert freshness(lot("2026-10-15", "2026-10-20"), today)["state"] == "past"
    assert freshness(lot("2026-10-15", ""), today) == {"state": "keeps", "days_left": None}
    old, new = lot("2026-10-18", "", 2), lot("2026-10-20", "", 5)
    assert [(x.made, q) for x, q in fifo([new, old], 4)] == [("2026-10-18", 2), ("2026-10-20", 2)]
    assert split_amount(10, [1, 2]) == [3.33, 6.67] and sum(split_amount(97, [6, 4, 5])) == 97


def test_demand_suggests_how_many_to_bring():
    class Day:
        def __init__(self, mid):
            self.market_id, self.status = mid, "closed"

    summaries = {"a": {"rows": [{"recipe_id": "r", "brought": 12, "sold": 12, "left": 0}]},
                 "b": {"rows": [{"recipe_id": "r", "brought": 12, "sold": 8, "left": 4}]}}
    assert demand([Day("a"), Day("b")], summaries)["r"] == {"markets": 2, "avg_sold": 10.0, "sold_out": 1, "bring": 13}


def test_hot_honey_from_receiving_to_market_day(shop):
    from core.web_more import workshop_page

    w = shop
    w.business = __import__("core.business_book", fromlist=["BusinessBook"]).BusinessBook(w, data_dir=w.home_dir)
    w.materials.add_material("Raw honey", unit="cups", unit_cost=4.0, quantity_on_hand=8.2)
    w.materials.add_material("Glass jar 8oz", unit="", unit_cost=1.0, quantity_on_hand=10)
    do(w, "craft_recipe.add", name="Hot honey", price=8, makes=6, makes_unit="jars", shelf_days=0,
       materials="1 cup Raw honey\n6 Glass jar 8oz\n3 Chili peppers @ 0.25", allergens="", net_amount="8 oz")
    recipe = w.craft_recipes.all_recipes()[0]
    p = do(w, "craft.start", recipe_id=recipe.recipe_id, times=2)
    assert p.summary.startswith("Begin crafting 2 batches of Hot honey: 12 jars")
    build = workshop_page(w)["builds"][0]
    p = do(w, "craft.finish", job_id=build["id"], hours=1)
    assert "Raw honey: 8.2 → 6.2 cups" in p.summary and "Glass jar 8oz: 10 → 0 (2 short)" in p.summary
    assert "Chili peppers not counted" in p.summary and "make 12 jars" in p.summary
    job = w.jobs.get_job(build["id"])
    assert job.finished_at[:10] == date.today().isoformat()
    assert w.products.get_product(w.craft_recipes.get_recipe(recipe.recipe_id).product_id).quantity_in_stock == 12

    # A market day: take 10, sell 6 (one tap at the recipe's price, one at a deal), toss 1 that cracked.
    p = do(w, "market.start", place="The stand", **{f"b_{recipe.recipe_id}": 10})
    assert p.summary == "Open a market day at The stand, taking 10 jars of Hot honey"
    p = do(w, "goods.sell", recipe_id=recipe.recipe_id, quantity=4)
    assert p.summary == "Sold 4 jars of Hot honey at The stand for $32.00"
    do(w, "goods.sell", recipe_id=recipe.recipe_id, quantity=2, amount=14)
    with pytest.raises(Exception, match="only 6 jars left"):
        w.actions.propose(w, "goods.sell", {"recipe_id": recipe.recipe_id, "quantity": 7})
    p = do(w, "market.close", **{f"t_{recipe.recipe_id}": 1})
    assert p.summary.startswith("Close the market day: 6 Hot honey, $46.00")
    assert p.summary.endswith("toss 1 Hot honey")
    market = w.business.markets[0]
    assert market.status == "closed"
    assert w.jobs.get_job(build["id"]).tossed == 1
    assert w.ledger.total_revenue() == 46

    # Selling past what's left is refused; undo puts the last sale back.
    p = do(w, "goods.sell", recipe_id=recipe.recipe_id, quantity=5, amount=40)
    assert w.ledger.total_revenue() == 86
    w.actions.undo(w, p.proposal_id)
    assert w.ledger.total_revenue() == 46


def test_a_finished_batch_from_yesterday_is_sold_before_todays(shop):
    from core.goods_actions import _lots

    w = shop
    do(w, "craft_recipe.add", name="Sourdough", price=5, makes=3, makes_unit="loaves", shelf_days=3)
    recipe = w.craft_recipes.all_recipes()[0]
    for _ in range(2):
        do(w, "craft.start", recipe_id=recipe.recipe_id)
        job = next(j for j in w.jobs.all_jobs() if j.status != "Complete")
        do(w, "craft.finish", job_id=job.job_id)
    first, second = sorted(w.jobs.all_jobs(), key=lambda j: j.created_at)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    w.jobs.update_job(first.job_id, finished_at=yesterday + "T08:00:00")
    lots = _lots(w, recipe.recipe_id)
    assert [lot.made for lot in lots] == [yesterday, date.today().isoformat()]
    assert lots[0].sell_by == (date.today() + timedelta(days=2)).isoformat()
    do(w, "goods.sell", recipe_id=recipe.recipe_id, quantity=4)
    left = {lot.job_id: lot.left for lot in _lots(w, recipe.recipe_id)}
    assert left == {second.job_id: 2}
    p = do(w, "goods.toss", job_id=second.job_id)
    assert p.summary.startswith("Toss 2 of Sourdough")
    assert _lots(w, recipe.recipe_id) == []
