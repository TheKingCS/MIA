"""A scanned receipt fills in a recipe's Bought It: store-receipt names
matched to recipe materials, each line used once, nothing guessed, and the
money never counted twice (it's already in the Budget)."""

from core.craft_recipes import CraftRecipe
from core.receipt_match import match, prefill, receipts, similarity
from tests.test_crafting import do, shop  # noqa: F401  (the workshop fixture)

LOWES = [
    {"description": "2X4X8 PREMIUM STUD", "amount": 23.88, "quantity": 6, "unit_price": 3.98},
    {"description": "3/4 PLYWD SANDE 4X8", "amount": 54.98, "quantity": None, "unit_price": None},
    {"description": "KREG POCKET SCRW 1-1/4", "amount": 7.98, "quantity": 1, "unit_price": 7.98},
    {"description": "SHOP TOWELS", "amount": 4.48},
]


def test_store_names_match_recipe_materials():
    assert similarity("Plywood 3/4", "3/4 PLYWD SANDE 4X8") == 1.0
    assert similarity("2x4 8ft", "4X8 PLYWOOD") == 0.0  # sharing numbers isn't a match
    found = match(["2x4 8ft", "Plywood 3/4", "Pocket screws", "Wood glue"], LOWES)
    assert found == {"pairs": {0: 0, 1: 1, 2: 2}, "unused": [3]}


def test_prefill():
    recipe = CraftRecipe(recipe_id="r", name="Bench", materials="6 board 2x4 8ft\n1 sheet Plywood 3/4\n24 pcs Pocket screws\nWood glue")
    p = prefill(recipe, LOWES)
    assert p["values"] == {"q_0": 6, "c_0": 23.88, "q_1": 1.0, "c_1": 54.98, "q_2": 1, "c_2": 7.98}
    assert p["unmatched"] == ["SHOP TOWELS"] and len(p["matched"]) == 3


def test_from_a_filed_receipt_without_double_counting(shop):  # noqa: F811
    w = shop
    expense = w.budget.add_expense(91.32, "Supplies", "Lowe's", payee="Lowe's", items=LOWES)
    [r] = receipts(w)
    assert r["id"] == f"expense:{expense.entry_id}" and r["name"].startswith("Lowe's · ")
    do(w, "craft_recipe.add", name="Bench", materials="6 board 2x4 8ft\n1 sheet Plywood 3/4")
    recipe = w.craft_recipes.all_recipes()[0]
    values = prefill(recipe, r["items"])["values"]
    p = do(w, "craft.receive", recipe_id=recipe.recipe_id, receipt=r["id"], **values)
    assert p.summary.endswith("(already in your Budget from the receipt)")
    assert w.ledger.total_expenses() == 0  # recorded once, in the Budget
    assert {m.name: m.quantity_on_hand for m in w.materials.all_materials()} == {"2x4 8ft": 6, "Plywood 3/4": 1}
    assert next(m for m in w.materials.all_materials() if m.name == "2x4 8ft").unit_cost == 3.98
