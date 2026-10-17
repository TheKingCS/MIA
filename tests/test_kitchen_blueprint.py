"""
Kitchen recipes as blueprints (DEC-0028 #9): the pantry is the
materials; "I Made This" takes what the batches used out of it, and what
runs out goes on the grocery list.
"""

import pytest

from core.actions import ActionCenter
from core.kitchen_blueprint import check, plan
from core.web_screens import recipe_page
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal, done


def _chili(world):
    k = world.kitchen
    recipe = k.add_recipe("Chili")
    k.update_recipe(recipe.recipe_id, ingredients=[
        {"name": "ground beef", "quantity": 1, "unit": "lb"}, {"name": "Diced onion", "quantity": 1, "unit": ""},
        {"name": "kidney beans", "quantity": 2, "unit": "can"}, {"name": "salt", "quantity": 0, "unit": ""},
        {"name": "cumin", "quantity": 1, "unit": "tbsp"}])
    k.add_pantry_item("Ground beef", quantity=3, unit="lb")
    k.add_pantry_item("onions", quantity=1, unit="")
    k.add_pantry_item("Kidney beans", quantity=2, unit="can")
    k.add_pantry_item("Salt", quantity=1, unit="box")
    return k.get_recipe(recipe.recipe_id)


def test_check_and_plan(world):
    recipe = _chili(world)
    rows = {r["name"]: r for r in check(recipe, world.kitchen.all_pantry_items(), 2)}
    assert rows["ground beef"]["need"] == 2 and rows["ground beef"]["have"] == 3 and rows["ground beef"]["state"] == "have"
    assert rows["kidney beans"]["state"] == "short" and rows["cumin"]["state"] == "missing"
    assert rows["salt"]["state"] == "have" and rows["salt"]["draw"] == []  # no amount: nothing taken
    p = plan(recipe, world.kitchen.all_pantry_items(), 1)
    assert p["said"] == ["1 lb ground beef", "1 Diced onion", "2 can kidney beans"]
    assert p["runs_out"] == ["onions", "Kidney beans"] and p["missing"] == ["cumin"]


def test_i_made_this_uses_up_the_pantry(world):
    recipe = _chili(world)
    prop, done = do(world, "meal.cook", recipe_id=recipe.recipe_id)
    assert "uses 1 lb ground beef" in prop.summary and "run out (goes on the grocery list)" in prop.summary
    left = {p.name: p.quantity for p in world.kitchen.all_pantry_items()}
    assert left == {"Ground beef": 2, "onions": 0, "Kidney beans": 0, "Salt": 1}
    assert {g.name for g in world.kitchen.all_grocery_items()} == {"onions", "Kidney beans"}
    assert world.kitchen.times_made(recipe.recipe_id) == 1 and "grocery list" in done.result
    page = recipe_page(world, recipe.recipe_id)
    assert next(i for i in page["ingredients"] if i["name"] == "ground beef")["have"] == "2 lb"
    assert page["forms"]["cook"]["fields"][0]["name"] == "batches"


def test_leaving_the_pantry_alone(world):
    recipe = _chili(world)
    prop, _done = do(world, "meal.cook", recipe_id=recipe.recipe_id, batches="2", pantry="No")
    assert "×2" in prop.summary and "pantry stays" in prop.summary
    assert {p.name: p.quantity for p in world.kitchen.all_pantry_items()}["Ground beef"] == 3
