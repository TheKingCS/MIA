"""Crafting recipes (DEC-0030 phase B): the smallest real end-to-end
workflow. A recipe → what's short → a shopping list → receive what you
bought → build it → photos → sell it → the build's real profit. Inventory
has to add up, nothing doubles on retry, and every step can be undone."""

import pytest

from core.actions import ActionCenter
from core.craft_recipes import CraftRecipe, average_cost, check, key, parse_lines
from core.job_manager import JobManager
from core.ledger_manager import LedgerManager
from core.material_manager import MaterialManager
from core.product_manager import ProductManager
from tests.engine_world import build_world


def test_parsing_and_checking():
    lines = parse_lines("4 board 2x4 8ft @ 3.98\n- 1/2 gal stain\nWood glue\n\n# note\n1 sheet Plywood 3/4 @54.98\n2x4 scrap")
    assert [(l.quantity, l.unit, l.name, l.unit_cost) for l in lines] == [
        (4, "board", "2x4 8ft", 3.98), (0.5, "gal", "stain", None), (1, "", "Wood glue", None),
        (1, "sheet", "Plywood 3/4", 54.98), (1, "", "2x4 scrap", None)]
    assert key("  Plywood   3/4 ") == "plywood 3/4"
    assert average_cost(0, 0, 4, 3.5) == 3.5 and average_cost(2, 4.0, 2, 5.0) == 4.5

    class M:  # a material on hand
        def __init__(self, name, q, cost):
            self.material_id, self.name, self.quantity_on_hand, self.unit_cost, self.unit = name, name, q, cost, ""
    recipe = CraftRecipe(recipe_id="r", name="Bench", materials="4 board 2x4 8ft @ 3.98\n1 Wood glue")
    state = check(recipe, [M("2x4 8ft", 1, 4.25)], times=2)
    assert [(r["need"], r["have"], r["short"], r["status"]) for r in state["rows"]] == [(8, 1, 7, "short"), (2, 0, 2, "missing")]
    assert state["shopping_cost"] == 29.75 and state["unpriced"] == 1 and not state["ready"]


@pytest.fixture
def shop(tmp_path, monkeypatch):
    from core.craft_recipes import CraftRecipeBook

    world = build_world(tmp_path, monkeypatch)
    here = world.home_dir  # the household's folder, where its history is too
    world.materials = MaterialManager(world, data_dir=here)
    world.products = ProductManager(world, data_dir=here)
    world.jobs = JobManager(world, data_dir=here)
    world.ledger = LedgerManager(world, data_dir=here)
    world.craft_recipes = CraftRecipeBook(world, data_dir=here)
    world.actions = ActionCenter()
    return world


def do(world, kind, **params):
    p = world.actions.propose(world, kind, params)
    world.actions.approve(world, p.proposal_id)
    return p


def test_a_furniture_build_end_to_end(shop):
    from core.build_media import media, save
    from core.web_more import workshop_page

    w = shop
    w.materials.add_material("2x4 8ft", unit="board", unit_cost=4.0, quantity_on_hand=2)
    do(w, "craft_recipe.add", name="Farmhouse bench", category="bench", price=180,
       materials="6 board 2x4 8ft @ 3.98\n1 sheet Plywood 3/4 @ 54.98\n24 pcs Pocket screws", steps="Cut\nAssemble\nStain")
    recipe = w.craft_recipes.all_recipes()[0]
    page = workshop_page(w)
    card = page["recipes"][0]
    assert (card["short"], card["ready"]) == (3, False)
    assert card["shopping_list"].splitlines()[0].startswith("4 board 2x4 8ft")
    assert card["receive_fields"][0]["default"] == 4

    # Bought it: 4 boards for $17, the plywood for $52, screws for $8.
    p = do(w, "craft.receive", recipe_id=recipe.recipe_id, q_0=4, c_0=17, q_1=1, c_1=52, q_2=24, c_2=8)
    assert p.summary.startswith("Receive for Farmhouse bench: 4 board 2x4 8ft ($17.00)")
    boards = next(m for m in w.materials.all_materials() if m.name == "2x4 8ft")
    assert boards.quantity_on_hand == 6 and boards.unit_cost == round((2 * 4.0 + 17) / 6, 4)
    assert {m.name for m in w.materials.all_materials()} == {"2x4 8ft", "Plywood 3/4", "Pocket screws"}
    assert w.ledger.total_expenses() == 77  # the purchase, once
    assert workshop_page(w)["recipes"][0]["ready"]

    do(w, "craft.start", recipe_id=recipe.recipe_id)
    build = workshop_page(w)["builds"][0]
    do(w, "craft.step", job_id=build["id"], index=0)
    assert workshop_page(w)["builds"][0]["steps_done"] == 1
    save(w, build["id"], "bench.jpg", b"\xff\xd8 before", tag="before")
    save(w, build["id"], "bench.jpg", b"\xff\xd8 after", tag="after")
    assert [m["tag"] for m in media(w, build["id"])] == ["before", "after"]

    p = do(w, "craft.finish", job_id=build["id"], hours=6)
    assert "use 6 board 2x4 8ft, 1 sheet Plywood 3/4, 24 pcs Pocket screws" in p.summary
    assert all(m.quantity_on_hand == 0 for m in w.materials.all_materials())  # used exactly what it needed
    product = w.products.get_product(w.craft_recipes.get_recipe(recipe.recipe_id).product_id)
    assert (product.name, product.quantity_in_stock, product.base_price) == ("Farmhouse bench", 1, 180)
    with pytest.raises(Exception):
        do(w, "craft.finish", job_id=build["id"], hours=6)  # can't finish twice

    do(w, "craft.cost", job_id=build["id"], amount=12, what="Stain", category="Materials")
    do(w, "craft.sell", job_id=build["id"], amount=175)
    result = workshop_page(w)["builds"][0]["result"]
    assert result["materials"] == 85  # what it used at its cost then: 6 boards (2 old, 4 new) $25, plywood $52, screws $8
    assert (result["sold"], result["other"], result["profit"], result["per_hour"]) == (175, 12, 78, 13)
    assert product.quantity_in_stock == 0
    again = workshop_page(w)["recipes"][0]
    assert (again["built"], again["sold"], again["actual"]["profit"]) == (1, 1, "$78.00")
    from core.chronicle import chronicle_page

    assert "You finished 1 build in the workshop." in chronicle_page(w)["this_week"]["story"]


def test_undo_puts_inventory_back(shop):
    w = shop
    do(w, "craft_recipe.add", name="Planter", materials="2 board Cedar 1x6")
    recipe = w.craft_recipes.all_recipes()[0]
    p = do(w, "craft.receive", recipe_id=recipe.recipe_id, q_0=2, c_0=20)
    assert w.materials.all_materials()[0].quantity_on_hand == 2
    w.actions.undo(w, p.proposal_id)
    assert w.materials.all_materials() == [] and w.ledger.total_expenses() == 0
    do(w, "craft.receive", recipe_id=recipe.recipe_id, q_0=2, c_0=20)
    do(w, "craft.start", recipe_id=recipe.recipe_id)
    job = w.jobs.all_jobs()[0]
    fin = do(w, "craft.finish", job_id=job.job_id, hours=1)
    assert w.materials.all_materials()[0].quantity_on_hand == 0
    w.actions.undo(w, fin.proposal_id)
    assert w.materials.all_materials()[0].quantity_on_hand == 2 and w.jobs.get_job(job.job_id).status == "In Progress"
    assert w.products.all_products() == []


def test_receiving_needs_something_and_photos_stay_in_their_folder(shop):
    from core.actions import ActionError
    from core.build_media import path_of

    w = shop
    do(w, "craft_recipe.add", name="Shelf", materials="1 board Pine 1x8")
    recipe = w.craft_recipes.all_recipes()[0]
    with pytest.raises(ActionError):
        w.actions.propose(w, "craft.receive", {"recipe_id": recipe.recipe_id, "q_0": 0})
    do(w, "craft.start", recipe_id=recipe.recipe_id)
    job = w.jobs.all_jobs()[0]
    with pytest.raises(ValueError):
        path_of(w, job.job_id, "../../jobs.json")
