"""DEC-0037: chickens (eggs, feed, birds; cartons into goods, eggs into
the bakery), Grow Lab harvests into stock, goods added by hand, and the
starter recipes."""

from datetime import date, timedelta

import pytest

from core.flock import Entry, Flock, figures, week_series
from core.goods_starters import STARTERS
from core.craft_recipes import CraftRecipe
from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


@pytest.fixture
def farm(shop):  # noqa: F811
    from core.business_book import BusinessBook
    from core.flock import FlockBook
    from core.grow_lab import GrowLab

    w = shop
    w.business = BusinessBook(w, data_dir=w.home_dir)
    w.flock = FlockBook(w, data_dir=w.home_dir)
    w.grow_lab = GrowLab(w, data_dir=w.home_dir)
    return w


def test_flock_figures_from_the_log():
    today = date(2026, 10, 21)
    f = Flock("f", "Layers", hens=10)
    entries = [Entry(str(i), "f", "eggs", (today - timedelta(days=i)).isoformat(), count=8) for i in range(10)]
    entries += [Entry("feed", "f", "feed", today.isoformat(), pounds=50, cost=24.0),
                Entry("u1", "f", "use", today.isoformat(), count=36, use="carton"),
                Entry("u2", "f", "use", today.isoformat(), count=6, use="baking")]
    x = figures(f, entries, today)
    assert (x["today"], x["week"], x["collected"], x["loose"]) == (8, 56, 80, 38)
    assert x["lay_rate"] == 0.8  # 56 eggs from 10 hens over 7 days
    assert x["feed_per_dozen"] == round(24 / (80 / 12), 2) and x["feed_per_egg"] == round(x["feed_per_dozen"] / 12, 4)
    series = week_series("f", entries, today)
    assert len(series) == 14 and series[-1] == {"date": "2026-10-21", "eggs": 8} and series[0]["eggs"] == 0


def test_a_week_with_the_hens(farm):
    from core.goods_actions import _lots
    from core.web_flock import flock_page

    w = farm
    do(w, "craft_recipe.starter", starter_id="eggs")
    eggs_good = w.craft_recipes.all_recipes()[0]
    w.craft_recipes.update_recipe(eggs_good.recipe_id, price=5, shelf_days=21)
    do(w, "flock.add", name="Layers", hens=12, breed="Buff Orpington", egg_recipe_id=eggs_good.recipe_id)
    flock = w.flock.flocks[0]
    for n in (9, 10, 11):
        do(w, "flock.eggs", flock_id=flock.flock_id, count=n)
    p = do(w, "flock.feed", flock_id=flock.flock_id, pounds=50, cost=20)
    assert p.summary == "Bought 50 lb of feed for $20.00 for Layers; a cost in the business's books"
    assert w.ledger.total_expenses() == 20

    p = do(w, "flock.use", flock_id=flock.flock_id, use="carton", eggs=24)
    assert p.summary.startswith("24 eggs from Layers into cartons: 2 dozen of Eggs into stock at $")
    lots = _lots(w, eggs_good.recipe_id)
    assert [lot.produced for lot in lots] == [2] and lots[0].unit_cost == round(20 / (30 / 12), 2)
    p = do(w, "flock.use", flock_id=flock.flock_id, use="baking", eggs=4)
    eggs = next(m for m in w.materials.all_materials() if m.name == "Eggs")
    assert eggs.quantity_on_hand == 4 and eggs.unit_cost == pytest.approx(20 / 30, abs=0.01)
    with pytest.raises(Exception, match="Only 2 loose eggs"):
        w.actions.propose(w, "flock.use", {"flock_id": flock.flock_id, "use": "home", "eggs": 3})
    p = do(w, "flock.birds", flock_id=flock.flock_id, change=-1, why="a hawk")
    assert p.summary == "Lost 1 hen (Layers: 12 → 11): a hawk"
    assert w.flock.flocks[0].hens == 11

    page = flock_page(w)
    card = page["flocks"][0]
    assert (card["figures"]["today"], card["figures"]["loose"], card["good"]["on_hand_text"]) == (30, 2, "2 dozen")
    assert page["total"]["hens"] == 11 and card["log"][0]["text"] == "1 hen lost"

    # The cartons sell at the market like anything else; taking back a log line works.
    do(w, "goods.sell", recipe_id=eggs_good.recipe_id, quantity=1)
    assert w.ledger.total_revenue() == 5
    do(w, "flock.entry_delete", entry_id=w.flock.entries[-1].entry_id)
    assert w.flock.flocks[0].hens == 12


def test_a_microgreens_harvest_goes_into_stock_with_the_batchs_cost(farm):
    from core.goods_actions import _lots

    w = farm
    do(w, "craft_recipe.starter", starter_id="microgreens")
    greens = w.craft_recipes.all_recipes()[0]
    do(w, "batch.add", crop="Radish microgreens", count=1, cost=6)
    batch = w.grow_lab.batches[0]
    p = do(w, "batch.harvest", batch_id=batch.batch_id, amount=1, unit="lb", into="goods", recipe_id=greens.recipe_id,
           stock_qty=8)
    assert p.summary == "Harvest 1 lb of Radish microgreens; 8 clamshells of Microgreens into stock at $0.75 each (the batch's cost)"
    assert [(lot.produced, lot.unit_cost) for lot in _lots(w, greens.recipe_id)] == [(8, 0.75)]
    # A second cut from the same tray isn't charged the seed again.
    p = do(w, "batch.harvest", batch_id=batch.batch_id, amount=0.5, unit="lb", into="goods", recipe_id=greens.recipe_id,
           stock_qty=4)
    assert "at $" not in p.summary
    # Herbs into Materials, for a blend.
    do(w, "batch.add", crop="Basil", count=6, cost=3)
    basil = w.grow_lab.batches[1]
    do(w, "batch.harvest", batch_id=basil.batch_id, amount=60, unit="g", into="materials", material="Dried basil")
    m = next(m for m in w.materials.all_materials() if m.name == "Dried basil")
    assert (m.quantity_on_hand, m.unit, m.unit_cost) == (60, "g", 0.05)


def test_goods_added_by_hand_and_every_starter_reads(farm):
    from core.goods_actions import _lots

    w = farm
    do(w, "craft_recipe.starter", starter_id="tomato_starts")
    starts = w.craft_recipes.all_recipes()[0]
    assert (starts.makes, starts.makes_unit) == (36, "pots")
    p = do(w, "goods.add", recipe_id=starts.recipe_id, quantity=30, cost_each=0.4, source="potted up")
    assert p.summary == "30 pots of Tomato starts into stock (potted up), at $0.40 each"
    assert _lots(w, starts.recipe_id)[0].unit_cost == 0.4
    for s in STARTERS:
        recipe = CraftRecipe(recipe_id="x", name=s["name"], materials=s.get("materials", ""))
        assert all(line.name and line.quantity > 0 for line in recipe.lines), s["id"]
        assert not any(line.name.split()[0].lower() in ("tray", "packet", "bag", "sheet", "board") for line in recipe.lines)
    p = w.actions.propose(w, "craft_recipe.starter", {"starter_id": "tomato_starts"})
    assert "a second" in p.summary


def test_a_child_helps_harvest_but_doesnt_stock_it(farm, monkeypatch):
    import core.child_accounts as child_accounts

    w = farm
    do(w, "craft_recipe.starter", starter_id="microgreens")
    do(w, "batch.add", crop="Peas", count=1)
    monkeypatch.setattr(child_accounts, "is_child", lambda context, profile_id=None: True)
    with pytest.raises(Exception, match="Ask a grown-up"):
        w.actions.propose(w, "batch.harvest", {"batch_id": w.grow_lab.batches[0].batch_id, "amount": 1, "into": "goods",
                                               "recipe_id": w.craft_recipes.all_recipes()[0].recipe_id})
