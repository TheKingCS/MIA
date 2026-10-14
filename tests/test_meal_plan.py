"""
Meal plans, prep and the shopping list (core/meal_plan.py, DEC-0020),
with their actions (meal.*) and missions. Placeholder recipes and values.
"""

from datetime import date, timedelta

import pytest

from core import fitness_missions as fx
from core import meal_plan as mp
from core.actions import ActionCenter, ActionError
from tests.engine_world import build_world

MON = date(2026, 10, 12)
TUE = MON + timedelta(days=1)


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    k = context.kitchen
    context.chili = k.add_recipe("Venison Chili", category="Lunch", servings=6)
    for name, qty, unit in (("ground venison", 2, "lb"), ("black beans", 2, "cans"), ("onion", 1, ""), ("chili powder", 2, "tbsp")):
        k.add_ingredient(context.chili.recipe_id, name, qty, unit)
    context.bowl = k.add_recipe("Chicken Rice Bowl", category="Dinner", servings=2)
    for name, qty, unit in (("chicken breast", 1, "lb"), ("white rice", 1, "cup"), ("broccoli", 2, "cups")):
        k.add_ingredient(context.bowl.recipe_id, name, qty, unit)
    context.pasta = k.add_recipe("Peanut Noodles", category="Dinner", servings=2)
    for name, qty, unit in (("pasta", 8, "oz"), ("peanut butter", 3, "tbsp")):
        k.add_ingredient(context.pasta.recipe_id, name, qty, unit)
    context.oats = k.add_recipe("Protein Oats", category="Breakfast", servings=1, calories_per_serving=450, protein_g=35)
    context.fitness.update_plan({"targets": {"protein_g": 180, "calories": 2600},
                                 "meals": {"packed_lunch": True, "prep_day": "Sun",
                                           "preferences": {"allergies": ["peanut"], "dislikes": []}}})
    return context


def act(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    return proposal, world.actions.approve(world, proposal.proposal_id)


def test_a_day_of_planned_meals_adds_up(world):
    fit = world.fitness
    fit.plan_meal(MON.isoformat(), "breakfast", world.oats.recipe_id)
    fit.plan_meal(MON.isoformat(), "dinner", world.bowl.recipe_id, servings=1)
    day = mp.day_plan(world, MON)
    assert [m["meal"] for m in day["meals"]] == ["breakfast", "dinner"]
    assert day["meals"][0]["kcal"] == 450 and day["meals"][0]["protein_g"] == 35  # typed values win
    assert 55 < day["meals"][1]["protein_g"] < 65  # half of: a pound of chicken, a cup of rice, 2 cups broccoli
    assert day["totals"]["protein_g"] == pytest.approx(35 + day["meals"][1]["protein_g"], abs=0.2)
    assert day["targets"] == {"kcal": 2600, "protein_g": 180}


def test_prep_covers_the_weeks_lunches(world):
    covers = [f"{(MON + timedelta(days=i)).isoformat()}:lunch" for i in range(5)]
    proposal, done = act(world, "meal.prep", date=(MON - timedelta(days=1)).isoformat(),
                         recipe_id=world.chili.recipe_id, servings="6", covers=",".join(covers))
    assert proposal.summary == "Prep on Sun Oct 11: Venison Chili × 6, covering 5 meals" and done.status == "executed"
    week = mp.week_plan(world, MON)
    assert [d["meals"][0]["name"] for d in week["days"][:5]] == ["Venison Chili"] * 5
    # Prep on Sunday the 11th belongs to the week of the 5th; this week's plan shows its covered lunches.
    assert week["planned"] == 5


def test_the_shopping_list_scales_combines_and_subtracts(world):
    fit, k = world.fitness, world.kitchen
    for day in (MON, TUE):
        fit.plan_meal(day.isoformat(), "dinner", world.bowl.recipe_id, servings=2)  # 4 servings: twice the recipe
    fit.plan_meal(TUE.isoformat(), "lunch", world.pasta.recipe_id, servings=2)
    k.add_pantry_item("White rice", 5, "cup")  # plenty
    k.add_grocery_item("Broccoli", 1, "head")  # already on the list
    shopping = mp.shopping_list(world, MON)
    items = {i["name"]: i for i in shopping["items"]}
    assert items["chicken breast"]["quantity"] == 2 and items["chicken breast"]["unit"] == "lb"
    assert "white rice" in shopping["in_pantry"] and "broccoli" in shopping["on_list"]
    assert items["peanut butter"]["allergy"] is True and items["pasta"]["allergy"] is False
    proposal, done = act(world, "meal.shop", date=MON.isoformat())
    assert "⚠ peanut butter matches an allergy" in proposal.summary
    names = [g.name for g in k.all_grocery_items()]
    assert "chicken breast" in names and names.count("Broccoli") == 1


def test_suggesting_a_week_avoids_allergies_and_aims_at_protein(world):
    picks = mp.suggest_week(world, MON)
    assert len(picks) == 14  # lunch and dinner, seven days
    assert all(p["name"] != "Peanut Noodles" for p in picks)  # the allergy
    dinners = [p["name"] for p in picks if p["meal"] == "dinner"]
    assert set(dinners) <= {"Chicken Rice Bowl", "Venison Chili"}
    world.fitness.update_plan({"meals": {"lunch_rotation": [world.chili.recipe_id]}})
    assert {p["name"] for p in mp.suggest_week(world, MON) if p["meal"] == "lunch"} == {"Venison Chili"}
    proposal, done = act(world, "meal.suggest", date=MON.isoformat())
    assert done.status == "executed" and mp.week_plan(world, MON)["planned"] == 14


def test_planned_meals_become_missions_and_eating_one_logs_it(world, monkeypatch):
    fit = world.fitness
    fit.plan_meal(MON.isoformat(), "breakfast", world.oats.recipe_id)
    fit.plan_meal(MON.isoformat(), "lunch", world.chili.recipe_id)
    missions = {fx._kind(m): m for m in fx.ensure(world, MON)}
    meals = missions["meals"]
    assert [o.description for o in meals.objectives] == ["Breakfast: Protein Oats", "Lunch: Venison Chili"]
    assert missions["meal_plan"].objectives[0].description == "Eat the 2 planned meals"
    fx.tick(world, world.missions.get_mission(meals.mission_id), 1, MON)  # lunch eaten
    eaten = fit.food_on(MON.isoformat())
    assert eaten[0]["name"] == "Venison Chili" and eaten[0]["planned_id"] == f"{MON.isoformat()}:lunch"
    assert world.missions.get_mission(missions["lunch"].mission_id).status == "completed"  # packed lunch, too
    fx.tick(world, world.missions.get_mission(meals.mission_id), 0, MON)
    assert world.missions.get_mission(meals.mission_id).status == "completed"
    assert world.missions.get_mission(missions["meal_plan"].mission_id).status == "completed"
    with pytest.raises(ActionError):
        world.actions.propose(world, "objective.tick", {"mission_id": missions["meal_plan"].mission_id, "index": "0"})


def test_changing_the_plan_today_updates_the_mission(world):
    fit = world.fitness
    fit.plan_meal(MON.isoformat(), "dinner", world.bowl.recipe_id)
    meals = {fx._kind(m): m for m in fx.ensure(world, MON)}["meals"]
    fit.plan_meal(MON.isoformat(), "dinner", world.chili.recipe_id)
    again = {fx._kind(m): m for m in fx.ensure(world, MON)}["meals"]
    assert again.mission_id == meals.mission_id
    assert [o.description for o in world.missions.get_mission(meals.mission_id).objectives] == ["Dinner: Venison Chili"]


def test_saying_todays_lunch_complete_eats_the_planned_lunch(world):
    from core.quick_commands import parse

    planned = {"lunch": {"recipe_id": world.chili.recipe_id, "servings": 1}}
    kind, params = parse("today's lunch complete", world.fitness.plan, None, planned)
    assert kind == "fitness.food" and params["recipe_id"] == world.chili.recipe_id
    assert params["planned_id"].endswith(":lunch")
