"""
DEC-0017/0018 (2026-10-06): Kitchen, Workout and Real Estate on the web.
The pages (core/web_screens.py) and every change as an action kind
(core/kitchen_actions.py, core/workout_actions.py, core/estate_actions.py),
each proposed, approved, recorded and undoable; a recipe's amounts scaled to
the servings asked for; workouts and volume week by week; a property's sale,
on the screen and by voice.
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
    """The shared test world with an action center."""
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def run(world, kind, **params):
    """Proposes and approves an action; returns both."""
    proposal = world.actions.propose(world, kind, params)
    return proposal, world.actions.approve(world, proposal.proposal_id)


# ------------------------------------------------------------------ Kitchen


def test_ingredients_one_per_line():
    items = parse_ingredients("2 cups rice\n1 1/2 tsp salt\neggs\n- 1/2 lb chicken")
    assert [(i["quantity"], i["unit"], i["name"]) for i in items] == [
        (2, "cups", "rice"), (1.5, "tsp", "salt"), (0, "", "eggs"), (0.5, "lb", "chicken")]
    assert ingredients_text(items) == "2 cups rice\n1.5 tsp salt\neggs\n0.5 lb chicken"


def test_the_kitchen(world):
    """A recipe, its ingredients and the pantry: the page says what's missing and expiring; what's missing goes to the grocery list; a meal is logged and the recipe favourited."""
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


def test_a_recipe_scales_to_the_servings_asked_for_in_kitchen_fractions(world):
    from core.units import kitchen_amount
    from core.web_screens import recipe_page, scale_factor

    recipe = world.kitchen.add_recipe("Chili", servings=4)
    for name, quantity, unit in (("rice", 1, "cup"), ("salt", 0, ""), ("flour", 300, "g")):
        world.kitchen.add_ingredient(recipe.recipe_id, name, quantity, unit)
    page = recipe_page(world, recipe.recipe_id, TODAY, servings=6)
    assert page["shown_servings"] == 6 and page["servings"] == 4
    assert [i["amount"] for i in page["ingredients"]] == ["1 ½ cups", "", "450 g"]
    assert recipe_page(world, recipe.recipe_id, TODAY)["ingredients"][0]["amount"] == "1 cup"
    assert scale_factor(4, "lots") == (4, 1.0) and scale_factor(4, 0) == (1, 0.25) and scale_factor(2, 999)[0] == 100
    assert (kitchen_amount(0.333, "cup"), kitchen_amount(2.75, "lb"), kitchen_amount(0.02, "tsp")) == ("⅓ cup", "2 ¾ lb", "a pinch")


def test_workouts_and_volume_are_counted_week_by_week():
    from types import SimpleNamespace as N

    from core.web_screens import weekly_training

    sessions = [N(date="2026-11-03", duration_minutes=40, sets_logged=[{"reps": 8, "weight": 135}, {"reps": 8, "weight": 135}]),
                N(date="2026-11-05", duration_minutes=30, sets_logged=[{"reps": 10, "weight": None}]),
                N(date="2026-10-28", duration_minutes=45, sets_logged=[{"reps": 5, "weight": "225"}]),
                N(date="2026-09-01", duration_minutes=60, sets_logged=[])]
    weeks = weekly_training(sessions, date(2026, 11, 7), weeks=3)
    assert [w["week"] for w in weeks] == ["2026-10-19", "2026-10-26", "2026-11-02"]
    assert [(w["workouts"], w["sets"], w["volume"]) for w in weeks] == [(0, 0, 0), (1, 1, 1125), (2, 3, 2160)]
    assert [w["volume_pct"] for w in weeks] == [0, 52, 100] and weeks[-1]["label"] == "Nov 2"
    assert all(w["workouts_pct"] == 0 for w in weekly_training([], date(2026, 11, 7)))


def test_kitchen_is_for_children_too_but_not_deleting_recipes(world):
    recipe = world.kitchen.add_recipe("Toast")
    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert world.actions.propose(world, "meal.log", {"recipe_id": recipe.recipe_id}).status == "proposed"
    with pytest.raises(ActionError, match="grown-ups"):
        world.actions.propose(world, "recipe.delete", {"recipe_id": recipe.recipe_id})


# ------------------------------------------------------------------ Workout


def test_streak_days():
    """The streak counts days in a row up to today, or from yesterday when nothing's logged today yet."""
    from types import SimpleNamespace

    days = [SimpleNamespace(date=(TODAY - timedelta(days=n)).isoformat()) for n in (0, 1, 2, 4)]
    assert _streak_days(days, TODAY) == 3
    assert _streak_days(days[1:], TODAY) == 2  # nothing today yet: the streak still counts from yesterday
    assert _streak_days([], TODAY) == 0


def test_the_workout(world):
    """A workout logged shows as the latest with its notes, counts this week and in the streak, and sets the personal best; templates are gone."""
    run(world, "exercise.add", name="Push-ups", category="Chest", equipment="Bodyweight")
    pushups = world.workout.all_exercises()[0]
    proposal, _ = run(world, "workout.log", exercise_id=pushups.exercise_id, reps="22", sets="1", notes="Felt good")
    assert proposal.summary == "Log a workout: Push-ups: 1 × 22"
    page = workout_page(world, TODAY)
    assert page["latest"]["summary"] == "Push-ups 22 reps · 1 set" and page["latest"]["notes"] == "Felt good"
    assert page["stats"]["this_week"] == 1 and page["stats"]["streak"] == 1
    assert page["exercises"][0]["pr"]["reps"] == 22

    # Workout templates are gone (Zac, 2026-10-16): the plan's training days are the routines.
    assert "templates" not in workout_page(world, TODAY)
    assert not any(k.startswith("workout_template.") for k in ACTION_TYPES)

    with pytest.raises(ActionError, match="Pick an exercise"):
        world.actions.propose(world, "workout.log", {"reps": "5"})


# ------------------------------------------------------------------ Real Estate


def test_real_estate(world):
    """A rental's card shows its status, rent, equity, this month's money, the upkeep needing attention and its depreciation once it has a price; deleting it says its money stays in Money."""
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
    assert card["depreciation"] is None  # no purchase price yet: nothing to depreciate
    world.real_estate.update_property(house.property_id, purchase_price=330000.0, land_value=55000.0,
                                      purchase_date="2024-11-07")
    dep = estate_page(world, TODAY)["properties"][0]["depreciation"]
    assert dep["year"] == 10000.0 and 19000 < dep["so_far"] < 21000  # 275,000 over 27.5 years, two years in
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


def test_a_recipe_photo(world, tmp_path):
    """Zac, 2026-10-16: a picture of each recipe, on its page, its card and the glasses."""
    from fastapi.testclient import TestClient

    import server.app as server_app
    from core.glasses import glasses_panel

    recipe = world.kitchen.add_recipe("Toast")
    assert kitchen_page(world)["recipes"][0]["photo"] == ""
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    path = f"/api/kitchen/recipe/{recipe.recipe_id}/photo"
    assert client.get(path).status_code == 404
    assert client.post(path, content=b"text", headers={"X-Filename": "notes.txt"}).status_code == 400
    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 64
    assert client.post(path, content=jpeg, headers={"X-Filename": "toast.jpg"}).status_code == 200
    got = client.get(path)
    assert got.status_code == 200 and got.content == jpeg
    url = kitchen_page(world)["recipes"][0]["photo"]
    assert url.startswith(path + "?v=")
    card = glasses_panel(world, "kitchen", "recipes-all")["lines"][0]
    assert card["recipe"]["photo"] == url
    # a new picture replaces the old one
    assert client.post(path, content=b"\x89PNG" + b"1" * 32, headers={"X-Filename": "toast.png"}).status_code == 200
    assert world.kitchen.recipe_photo_path(recipe.recipe_id).suffix == ".png"
    assert len(list((world.kitchen.data_dir / "recipe_photos").iterdir())) == 1


def test_a_rented_property_with_no_rent_in_this_month_says_rent_due():
    from core.web_screens import property_badge

    assert property_badge("Rented", 1450, 0) == {"text": "Rent Due", "tone": "attention"}
    assert property_badge("Rented", 1450, 1450) == {"text": "Rented", "tone": "ok"}
    assert property_badge("Vacant", 0, 0)["tone"] == "attention"  # needs you, never an error
    assert property_badge("Primary Residence", 0, 0) == {"text": "Primary Residence", "tone": ""}


def test_a_sale_is_recorded_with_what_it_came_to_leaves_the_totals_and_undoes(world):
    """Selling a rental keeps the price, costs, the loan paid off and the depreciation as of the sale; its card shows
    the cash left and the gain (an estimate), it leaves the portfolio's equity, a second sale is refused, and Undo
    puts it back."""
    from core.real_estate_manager import sale_summary

    run(world, "property.add", name="Oak", property_type="Rental", monthly_rent="1500", current_value="300000",
        mortgage_balance="100000")
    oak = world.real_estate.all_properties()[0]
    world.real_estate.update_property(oak.property_id, purchase_price=200000.0, land_value=35000.0,
                                      purchase_date="2021-01-01")
    proposal, sold = run(world, "property.sell", property_id=oak.property_id, sale_price="320000",
                         selling_costs="20000", date="2026-01-01")
    assert proposal.summary.startswith("Record Oak as sold for $320,000.00 on 2026-01-01")
    oak = world.real_estate.get_property(oak.property_id)
    s = sale_summary(oak)
    assert oak.status == "Sold" and oak.payoff_at_sale == 100000.0 and s["net_proceeds"] == 200000.0
    assert 29000 < s["depreciation"] < 31000 and s["recapture"] == s["depreciation"]  # 165,000 over 27.5, five years
    assert s["gain"] == 300000.0 - (200000.0 - s["depreciation"])
    card = estate_page(world, TODAY)["properties"][0]
    assert card["sale"]["net_proceeds"] == 200000.0 and card["equity"] == 0 and card["depreciation"] is None
    with pytest.raises(ActionError, match="already recorded as sold"):
        world.actions.propose(world, "property.sell", {"property_id": oak.property_id, "sale_price": "1"})
    world.actions.undo(world, sold.proposal_id)
    assert world.real_estate.get_property(oak.property_id).sale_date == ""


def test_a_sale_said_to_mia_is_recorded_by_the_same_store(world):
    """"We sold Pine for 250,000" through record_property_sale: recorded, the cash and gain said, a missing price or
    an unknown property says so."""
    from core.application import MIAApplication

    world.real_estate.add_property(name="Pine", property_type="Rental", current_value=240000.0,
                                   mortgage_balance=50000.0)
    tool = MIAApplication._action_record_property_sale
    assert "price" in tool(world, {"property_name": "Pine", "sale_price": "lots"})
    said = tool(world, {"property_name": "Pine", "sale_price": 250000, "selling_costs": 15000})
    assert said.startswith("Recorded 'Pine' as sold for $250,000: about $185,000 after costs")
    assert "already recorded as sold" in tool(world, {"property_name": "Pine", "sale_price": 1})
