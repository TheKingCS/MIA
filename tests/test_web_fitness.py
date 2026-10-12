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
