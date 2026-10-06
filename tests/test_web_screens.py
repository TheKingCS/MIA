"""
DEC-0017/0018 (2026-10-06): Kitchen, Workout and Real Estate on the web.
The pages (core/web_screens.py) and every change as an action kind
(core/kitchen_actions.py, core/workout_actions.py, core/estate_actions.py),
each proposed, approved, recorded and undoable.
"""

from datetime import date, timedelta

import pytest

from core.actions import ACTION_TYPES, ActionCenter, ActionError
from core.child_accounts import make_child
from core.kitchen_actions import ingredients_text, parse_ingredients
from core.web_screens import _streak_days, estate_page, kitchen_page, workout_page
from tests.engine_world import build_world

TODAY = date.today()


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def run(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    return proposal, world.actions.approve(world, proposal.proposal_id)


# ------------------------------------------------------------------ Kitchen


def test_ingredients_one_per_line():
    items = parse_ingredients("2 cups rice\n1 1/2 tsp salt\neggs\n- 1/2 lb chicken")
    assert [(i["quantity"], i["unit"], i["name"]) for i in items] == [
        (2, "cups", "rice"), (1.5, "tsp", "salt"), (0, "", "eggs"), (0.5, "lb", "chicken")]
    assert ingredients_text(items) == "2 cups rice\n1.5 tsp salt\neggs\n0.5 lb chicken"


def test_the_kitchen(world):
    proposal, _ = run(world, "recipe.add", name="Fried rice", category="Dinner", servings="2", prep_time_minutes="10",
                      cook_time_minutes="15")
    assert proposal.summary == "Add the recipe Fried rice: meal Dinner, servings 2, prep 10, cook 15"
    recipe = world.kitchen.all_recipes()[0]
    run(world, "recipe.ingredients", recipe_id=recipe.recipe_id, ingredients="2 cups rice\n2 eggs\nsoy sauce")
    run(world, "pantry.add", name="rice", quantity="5", unit="lb", expiration_date=(TODAY + timedelta(days=2)).isoformat())
    run(world, "pantry.add", name="eggs", quantity="12")
    page = kitchen_page(world, TODAY)
    [card] = page["recipes"]
    assert card["minutes"] == 25 and card["missing"] == ["soy sauce"] and not card["makeable"]
    assert card["ingredients_text"] == "2 cups rice\n2 eggs\nsoy sauce"
    assert page["counts"] == {"recipes": 1, "pantry": 2, "expiring": 1, "grocery": 0}
    assert page["pantry"][0]["name"] == "rice" and page["pantry"][0]["expiring"]

    proposal, _ = run(world, "grocery.from_recipe", recipe_id=recipe.recipe_id)
    assert proposal.summary == "Add what's missing for Fried rice to the grocery list: soy sauce"
    with pytest.raises(ActionError, match="already on the grocery list"):
        world.actions.propose(world, "grocery.from_recipe", {"recipe_id": recipe.recipe_id})
    run(world, "grocery.add", name="Milk", quantity="1", unit="gal")
    milk = next(g for g in world.kitchen.all_grocery_items() if g.name == "Milk")
    proposal, _ = run(world, "grocery.check", item_id=milk.item_id, checked=True)
    assert proposal.summary == "Check off Milk"
    assert kitchen_page(world, TODAY)["counts"]["grocery"] == 1
    run(world, "grocery.clear_checked")
    assert [g.name for g in world.kitchen.all_grocery_items()] == ["soy sauce"]

    proposal, _ = run(world, "meal.log", recipe_id=recipe.recipe_id)
    assert proposal.summary == "Log a meal: Fried rice today"
    page = kitchen_page(world, TODAY)
    assert page["meals"][0]["recipe"] == "Fried rice" and page["recipes"][0]["times_made"] == 1

    run(world, "recipe.favorite", recipe_id=recipe.recipe_id, favorite=True)
    assert kitchen_page(world, TODAY)["recipes"][0]["favorite"]


def test_a_locked_recipe_says_which_mission_unlocks_it(world):
    recipe = world.kitchen.add_recipe("Ramen", locked=True)
    world.missions.add_mission("Cook 3 healthy meals", recipe_unlocks=[recipe.recipe_id])
    [card] = kitchen_page(world, TODAY)["recipes"]
    assert card["locked"] and card["unlocked_by_mission"] == "Cook 3 healthy meals"
    with pytest.raises(ActionError, match="still locked"):
        world.actions.propose(world, "meal.log", {"recipe_id": recipe.recipe_id})


def test_kitchen_is_for_children_too_but_not_deleting_recipes(world):
    recipe = world.kitchen.add_recipe("Toast")
    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert world.actions.propose(world, "meal.log", {"recipe_id": recipe.recipe_id}).status == "proposed"
    with pytest.raises(ActionError, match="grown-ups"):
        world.actions.propose(world, "recipe.delete", {"recipe_id": recipe.recipe_id})


# ------------------------------------------------------------------ Workout


def test_streak_days():
    from types import SimpleNamespace

    days = [SimpleNamespace(date=(TODAY - timedelta(days=n)).isoformat()) for n in (0, 1, 2, 4)]
    assert _streak_days(days, TODAY) == 3
    assert _streak_days(days[1:], TODAY) == 2  # nothing today yet: the streak still counts from yesterday
    assert _streak_days([], TODAY) == 0


def test_the_workout(world):
    run(world, "exercise.add", name="Push-ups", category="Chest", equipment="Bodyweight")
    pushups = world.workout.all_exercises()[0]
    proposal, _ = run(world, "workout.log", exercise_id=pushups.exercise_id, reps="22", sets="1", notes="Felt good")
    assert proposal.summary == "Log a workout: Push-ups: 1 × 22"
    page = workout_page(world, TODAY)
    assert page["latest"]["summary"] == "Push-ups 22 reps · 1 set" and page["latest"]["notes"] == "Felt good"
    assert page["stats"]["this_week"] == 1 and page["stats"]["streak"] == 1
    assert page["exercises"][0]["pr"]["reps"] == 22

    run(world, "workout_template.add", name="Upper body")
    template = world.workout.all_templates()[0]
    proposal, _ = run(world, "workout_template.exercise_add", template_id=template.template_id,
                      exercise_id=pushups.exercise_id, target_sets="3", target_reps="15")
    assert proposal.summary == "Add Push-ups to Upper body: 3 × 15"
    proposal, _ = run(world, "workout.log", template_id=template.template_id, duration_minutes="25")
    assert proposal.summary == "Log a workout: Upper body (3 sets), 25 min"
    assert workout_page(world, TODAY)["stats"]["total"] == 2
    _, removed = run(world, "workout_template.exercise_remove", template_id=template.template_id, index="0")
    assert world.workout.get_template(template.template_id).exercises == []
    world.actions.undo(world, removed.proposal_id)
    assert len(world.workout.get_template(template.template_id).exercises) == 1

    with pytest.raises(ActionError, match="Pick an exercise"):
        world.actions.propose(world, "workout.log", {"reps": "5"})


# ------------------------------------------------------------------ Real Estate


def test_real_estate(world):
    proposal, _ = run(world, "property.add", name="Maple House", property_type="Rental", status="Rented",
                      location="Town, ST", monthly_rent="1200", current_value="200000", mortgage_balance="150000")
    assert proposal.summary.startswith("Add the property Maple House: kind Rental, status Rented, in Town, ST, rent $1,200.00")
    house = world.real_estate.all_properties()[0]
    proposal, _ = run(world, "property.rent", property_id=house.property_id)
    assert proposal.summary == "Record $1,200.00 rent from Maple House today"
    run(world, "property.expense", property_id=house.property_id, amount="80", description="Filters")
    proposal, _ = run(world, "property.track_upkeep", property_id=house.property_id)
    house = world.real_estate.get_property(house.property_id)
    world.maintenance.add_task(house.maintenance_asset_id, "HVAC filter", interval_days=30,
                               last_completed=(TODAY - timedelta(days=35)).isoformat())
    page = estate_page(world, TODAY)
    [card] = page["properties"]
    assert (card["status"], card["location"], card["rent"], card["equity"]) == ("Rented", "Town, ST", 1200.0, 50000.0)
    assert card["income_month"] == 1200.0 and card["expenses_month"] == 80.0
    assert [t["title"] for t in card["tasks"]] == ["HVAC filter"] and card["tasks"][0]["needs_attention"]
    assert page["totals"]["attention"] == 1
    with pytest.raises(ActionError, match="already tracked"):
        world.actions.propose(world, "property.track_upkeep", {"property_id": house.property_id})

    proposal, deleted = run(world, "property.delete", property_id=house.property_id)
    assert proposal.summary == "Delete the property Maple House ($1,200.00). Its rent and expenses stay in Money."
    world.actions.undo(world, deleted.proposal_id)
    assert world.real_estate.get_property(house.property_id).status == "Rented"


def test_a_mortgage_gives_a_payment_and_cash_flow(world):
    run(world, "property.add", name="Elm", monthly_rent="1500", original_loan_amount="200000", interest_rate_pct="6",
        loan_term_months="360")
    [card] = estate_page(world, TODAY)["properties"]
    assert card["payment"] == 1199.1 and card["cash_flow"] == 300.9


def test_the_latest_workout_is_the_last_one_logged_that_day(world):
    run(world, "exercise.add", name="Squats")
    run(world, "exercise.add", name="Lunges")
    ids = {e.name: e.exercise_id for e in world.workout.all_exercises()}
    for name in ("Lunges", "Squats", "Lunges"):
        run(world, "workout.log", exercise_id=ids[name], reps="10")
    assert workout_page(world, TODAY)["latest"]["summary"].startswith("Lunges")


def test_old_saved_properties_still_load():
    from core.real_estate_manager import Property

    prop = Property.from_dict({"property_id": "p1", "name": "Old"})
    assert (prop.status, prop.location, prop.monthly_rent) == ("", "", 0.0)


def test_the_endpoints_and_a_child(world):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    for path in ("/api/kitchen", "/api/workout", "/api/real-estate"):
        assert client.get(path).status_code == 200, path
    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert client.get("/api/kitchen").status_code == 200 and client.get("/api/workout").status_code == 200
    assert client.get("/api/real-estate").status_code == 403
    assert not any(ACTION_TYPES[k].child_ok for k in ACTION_TYPES if k.startswith("property."))
