"""
The fitness screens' data (core/web_fitness.py, DEC-0020): today, the
weight line, missions and "is it working?" in one plain sentence, the
meal-plan week, and the endpoints. Placeholder values.
"""

from datetime import date, timedelta

import pytest

from core.actions import ActionCenter
from core.child_accounts import make_child
from core.personal_data import ScopedView
from core.web_fitness import fitness_page, progress, week_page, weight_series
from tests.engine_world import build_world

MON = date(2026, 10, 12)


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.fitness.update_plan({
        "targets": {"protein_g": 180, "calories": 2400, "target_weight": 175},
        "training": {"days": ["Mon", "Wed", "Fri"], "rotation": [{"name": "Push", "exercises": [{"name": "Dips", "sets": 3, "reps": 8}]}]},
        "skill_tree": [{"skill": "Handstand", "daily_minutes": 12, "practice": ["Wall work"],
                        "steps": [{"name": "Wall hold", "target_seconds": 60}]}],
    })
    return context


def test_today_at_a_glance(world):
    world.fitness.log_skill("Handstand", "Wall hold", seconds=42, on=MON.isoformat())
    page = fitness_page(world, MON)
    assert page["today"]["training"]["name"] == "Push"
    assert page["today"]["training"]["steps"] == [{"index": 0, "name": "Dips", "sets": 3, "reps": 8, "hold_seconds": None,
                                                   "done": False}]
    assert page["today"]["skills"][0]["steps"][0]["best_seconds"] == 42
    assert {m["kind"] for m in page["missions"]} == {"training", "skill:handstand", "protein"}
    assert page["today"]["food"]["targets"] == {"kcal": 2400, "protein_g": 180}
    assert fitness_page(world, MON + timedelta(days=1))["today"]["rest_day"] is True


def test_the_weight_line_and_where_its_heading(world):
    for i in range(8):
        world.fitness.log_weight(185 - 0.25 * i, on=(MON - timedelta(days=21 - 3 * i)).isoformat())
    page = fitness_page(world, MON)
    assert page["weight"]["weekly_change"] == pytest.approx(-0.58, abs=0.02)  # weigh-ins keep one decimal
    assert page["weight"]["on_track_for"] is not None
    series = weight_series(world.fitness, MON)
    assert len(series) == 8 and series[-1]["average"] == pytest.approx((183.75 + 183.5 + 183.25) / 3, abs=0.05)


def test_is_it_working_in_one_sentence(world):
    fit = world.fitness
    for i in range(28):
        day = MON - timedelta(days=i)
        fit.log_food("dinner", "Dinner", {"kcal": 2300, "protein_g": 170}, on=day.isoformat())
    for i in (0, 3, 5, 6):  # Mon 12, Fri 9, Wed 7; Tue 6 is a rest day and doesn't count
        fit.complete_training(MON - timedelta(days=i))
    for i in range(8):
        fit.log_weight(185 - 0.25 * i, on=(MON - timedelta(days=21 - 3 * i)).isoformat())
    summary = progress(world, MON)
    assert summary["workouts"] == 3 and summary["planned_workouts"] == 12  # Mon/Wed/Fri over 4 weeks
    assert summary["average_kcal"] == 2300 and summary["average_protein_g"] == 170
    assert summary["sentence"].startswith("4 weeks: 3 of 12 workouts, 2,300 kcal a day (goal 2,400), 170 g protein (goal 180), "
                                          "weight down 0.5")
    assert "lb a week, on track for your goal by" in summary["sentence"]
    empty = progress(build_child_free_world(world), MON)
    assert "Nothing logged yet" in empty["sentence"]
    world.fitness.log_weight(180, on=(MON - timedelta(days=2)).isoformat())  # started on Saturday
    assert progress(world, MON)["sentence"] == "3 days: 0 of 1 workouts."  # Sat, Sun, Mon: one training day so far


def build_child_free_world(world):
    world.fitness._data.update(weigh_ins=[], food=[], training_done=[])
    return world


def test_children_see_no_weight(world):
    make_child(world, world.me.profile_id, [world.other.profile_id])
    assert "weight" not in fitness_page(world, MON)
    assert world.actions.propose is not None


def test_the_week_page(world):
    recipe = world.kitchen.add_recipe("Chili", category="Lunch", servings=4)
    world.kitchen.add_ingredient(recipe.recipe_id, "ground beef", 1, "lb")
    world.fitness.plan_meal(MON.isoformat(), "lunch", recipe.recipe_id)
    week = week_page(world, MON)
    assert week["week_of"] == MON.isoformat() and week["planned"] == 1
    assert week["shopping"]["items"][0]["name"] == "ground beef" and week["shopping"]["items"][0]["quantity"] == 0.25
    assert {r["name"] for r in week["recipes"]} == {"Chili"}


# ------------------------------------------------------------------ one recipe, opened (Zac, 2026-10-14)


def test_recipe_steps_are_numbered_however_they_were_typed():
    from core.web_screens import recipe_steps

    assert recipe_steps("Brown the beef.\nAdd beans.\n\nSimmer 1 hour.") == ["Brown the beef.", "Add beans.", "Simmer 1 hour."]
    assert recipe_steps("1. Brown the beef. 2. Add 2 cans of beans. 3) Simmer.") == ["Brown the beef.", "Add 2 cans of beans.", "Simmer."]
    assert recipe_steps("Step 1: Mix\nStep 2: Bake") == ["Mix", "Bake"]
    assert recipe_steps("") == []


def test_the_recipe_page_says_what_the_house_has(world):
    from core.web_screens import recipe_page

    recipe = world.kitchen.add_recipe("Chili", category="Dinner", servings=4, instructions="Brown it.\nSimmer.", protein_g=30)
    for name, qty, unit in (("Ground Beef", 1, "lb"), ("Diced Onions", 1, ""), ("black beans", 2, "can"), ("cumin", 1, "tsp")):
        world.kitchen.add_ingredient(recipe.recipe_id, name, qty, unit)
    world.kitchen.add_pantry_item("onion", 3)  # plural, and "diced", still match
    world.kitchen.add_grocery_item("Black Bean")
    world.fitness.plan_meal(MON.isoformat(), "dinner", recipe.recipe_id, 2)
    page = recipe_page(world, recipe.recipe_id, MON)
    assert {i["name"]: i["status"] for i in page["ingredients"]} == {
        "Ground Beef": "to_buy", "Diced Onions": "have", "black beans": "on_list", "cumin": "to_buy"}
    assert page["to_buy"] == ["Ground Beef", "cumin"]
    assert page["steps"] == ["Brown it.", "Simmer."] and page["nutrition"]["protein_g"] == 30
    assert page["scheduled"] == [{"date": MON.isoformat(), "meal": "dinner", "servings": 2, "eaten": False}]
    assert page["default_meal"] == "dinner" and page["can_schedule"]
    assert recipe_page(world, "nope")["available"] is False


def test_add_to_grocery_list_adds_exactly_what_the_page_says(world):
    from core.web_screens import recipe_page

    recipe = world.kitchen.add_recipe("Eggs", servings=1)
    for name in ("eggs", "Chopped Chives", "butter"):
        world.kitchen.add_ingredient(recipe.recipe_id, name, 1, "")
    world.kitchen.add_pantry_item("egg", 6)
    world.kitchen.add_grocery_item("chive")
    to_buy = recipe_page(world, recipe.recipe_id, MON)["to_buy"]
    proposal = world.actions.propose(world, "grocery.from_recipe", {"recipe_id": recipe.recipe_id})
    assert proposal.summary.endswith(": butter") and to_buy == ["butter"]
    world.actions.approve(world, proposal.proposal_id)
    assert sorted(g.name for g in world.kitchen.all_grocery_items()) == ["butter", "chive"]


def test_scheduling_a_meal_says_what_it_replaces(world):
    chili = world.kitchen.add_recipe("Chili")
    stew = world.kitchen.add_recipe("Stew")
    world.fitness.plan_meal(MON.isoformat(), "dinner", chili.recipe_id)
    proposal = world.actions.propose(world, "meal.plan", {"date": MON.isoformat(), "meal": "dinner", "recipe_id": stew.recipe_id})
    assert proposal.summary == "Plan dinner on Mon Oct 12: Stew (instead of Chili)"


def test_my_plan_saves_what_was_typed(world):
    proposal = world.actions.propose(world, "fitness.plan", {"changes": {
        "targets": {"protein_g": "170", "calories": "", "target_weight": "172.5", "weigh_in_days": "mon, Thursday"},
        "training": {"days": "Mon, Wed, Fri", "rotation": [{"name": "Pull", "exercises": "Pull-ups 5x5\nHang 30s"}, {"name": " "}]},
        "skill_tree": [{"skill": "L-sit", "daily_minutes": "10", "practice": "Tuck, one leg", "steps": "Tuck 20s\nFull 10s"}],
        "meals": {"packed_lunch": "true", "preferences": {"allergies": "peanuts, shellfish"}}}})
    assert proposal.summary == "Update your plan: meals, skills, targets, training"
    world.actions.approve(world, proposal.proposal_id)
    plan = world.fitness.plan
    assert plan["targets"]["protein_g"] == 170 and plan["targets"]["calories"] is None
    assert plan["targets"]["target_weight"] == 172.5 and plan["targets"]["weigh_in_days"] == ["Mon", "Thu"]
    assert plan["training"]["rotation"] == [{"name": "Pull", "exercises": [{"name": "Pull-ups", "sets": 5, "reps": 5},
                                                                           {"name": "Hang", "sets": 1, "hold_seconds": 30}]}]
    assert plan["skill_tree"][0]["steps"][0] == {"name": "Tuck", "target_seconds": 20} and plan["skill_tree"][0]["daily_minutes"] == 10
    assert plan["meals"]["packed_lunch"] is True and plan["meals"]["preferences"]["allergies"] == ["peanuts", "shellfish"]
    assert fitness_page(world, MON)["plan_text"]["rotation"] == [{"name": "Pull", "exercises": "Pull-ups 5x5\nHang 30s"}]
    with pytest.raises(Exception, match="Days are"):
        world.actions.propose(world, "fitness.plan", {"changes": {"training": {"days": "Funday"}}})


def test_removing_food_weigh_ins_and_prep(world):
    chili = world.kitchen.add_recipe("Chili")
    world.fitness.plan_meal(MON.isoformat(), "lunch", chili.recipe_id)
    session = world.fitness.add_prep(MON.isoformat(), chili.recipe_id, 4, [f"{MON.isoformat()}:lunch"])
    entry = world.fitness.log_food("snack", "Shake", {"protein_g": 40}, on=MON.isoformat())
    weight = world.fitness.log_weight(180, on=MON.isoformat(), unit="lb")
    for kind, params in (("meal.prep_delete", {"prep_id": session["id"]}), ("fitness.food_delete", {"entry_id": entry["id"]}),
                         ("fitness.weigh_in_delete", {"entry_id": weight["id"]})):
        proposal = world.actions.propose(world, kind, params)
        world.actions.approve(world, proposal.proposal_id)
    assert world.fitness.prep_sessions() == [] and world.fitness.planned(MON.isoformat()) == {}
    assert world.fitness.food_on(MON.isoformat()) == [] and world.fitness.weigh_ins() == []
    assert weight_series(world.fitness, MON) == []


def test_rating_and_cooking_stats_on_the_recipe_page(world):
    """Zac, 2026-10-14: 5-star ratings and how many times you've made it."""
    from core.web_screens import recipe_page

    chili = world.kitchen.add_recipe("Chili", servings=6)
    proposal = world.actions.propose(world, "recipe.rate", {"recipe_id": chili.recipe_id, "rating": "4"})
    assert proposal.summary == "Rate Chili ★★★★☆"
    world.actions.approve(world, proposal.proposal_id)
    world.kitchen.set_recipe_rating("someone-else", chili.recipe_id, 5)
    with pytest.raises(Exception, match="1 to 5"):
        world.actions.propose(world, "recipe.rate", {"recipe_id": chili.recipe_id, "rating": "7"})
    world.kitchen.log_meal(chili.recipe_id, (MON - timedelta(days=40)).isoformat())
    # Meal prep: cooked once, eaten twice; counts as made once.
    session = world.fitness.add_prep(MON.isoformat(), chili.recipe_id, 6, [f"{MON.isoformat()}:lunch", f"{MON.isoformat()}:dinner"])
    world.actions.approve(world, world.actions.propose(world, "meal.prep_done", {"prep_id": session["id"]}).proposal_id)
    for meal in ("lunch", "dinner"):
        world.actions.approve(world, world.actions.propose(world, "fitness.food", {
            "meal": meal, "recipe_id": chili.recipe_id, "date": MON.isoformat(), "planned_id": f"{MON.isoformat()}:{meal}"}).proposal_id)
    stats = recipe_page(world, chili.recipe_id, date.today())["stats"]
    assert stats["rating"] == 4 and stats["others_rated"] == 1 and stats["others_average"] == 5
    assert stats["times_made"] == 2 and stats["made_last_30_days"] == 1 and stats["times_eaten"] == 2
    assert stats["first_made"] == (MON - timedelta(days=40)).isoformat()
    world.actions.approve(world, world.actions.propose(world, "recipe.rate", {"recipe_id": chili.recipe_id, "rating": "0"}).proposal_id)
    assert recipe_page(world, chili.recipe_id)["stats"]["rating"] is None
