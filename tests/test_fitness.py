"""
A person's fitness plan and logs (core/fitness_manager.py, DEC-0020,
H-0026) and recipe nutrition facts (core/nutrition.py). Placeholder
numbers only (DEC-0002).
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
from core import fitness_manager as fm
from core import nutrition
from core.config_manager import ConfigManager

MON = date(2026, 10, 12)  # a Monday


@pytest.fixture
def fit(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = SimpleNamespace(config=ConfigManager())
    return fm.FitnessManager(context, data_dir=tmp_path / "robin")


def test_the_trend_is_an_average_and_a_weekly_rate():
    points = [(MON - timedelta(days=21 - 3 * i), 200 - 0.3 * i) for i in range(8)]  # down 0.7 lb a week
    picture = fm.trend(points, MON)
    assert picture["weekly_change"] == pytest.approx(-0.7, abs=0.01)
    assert picture["average_7d"] == pytest.approx((198.5 + 198.2 + 197.9) / 3, abs=0.1)  # the last 3 are within 7 days
    assert picture["since_start"] == pytest.approx(-2.1) and picture["count"] == 8
    assert fm.trend(points[:2], MON)["weekly_change"] is None  # too few to say
    assert fm.trend([], MON)["latest"] is None


def test_when_the_goal_weight_is_reached():
    assert fm.eta(190, -0.5, 185, MON) == (MON + timedelta(weeks=10)).isoformat()
    assert fm.eta(190, 0.5, 185, MON) is None  # heading the other way: no date, no scolding
    assert fm.eta(190, None, 185, MON) is None and fm.eta(190, -0.5, None, MON) is None


def test_weigh_ins_one_a_day_in_the_persons_units(fit):
    assert fit.plan["units"] == "lb"  # the country's (US by default)
    fit.log_weight(182.4, on="2026-10-10")
    fit.log_weight(181.0, on="2026-10-12")
    fit.log_weight(180.6, on="2026-10-12")  # the same day again: replaces
    assert [w["weight"] for w in fit.weigh_ins()] == [182.4, 180.6]
    fit.log_weight(82, on="2026-10-11", unit="kg")
    assert fit.weight_trend(MON)["average_7d"] == pytest.approx((182.4 + 180.78 + 180.6) / 3, abs=0.1)
    with pytest.raises(ValueError):
        fit.log_weight(5)


def test_a_day_of_food_against_the_targets(fit):
    fit.update_plan({"targets": {"protein_g": 180, "calories": 2400}})
    fit.log_food("breakfast", "Eggs and oats", {"kcal": 520, "protein_g": 32}, on="2026-10-12")
    fit.log_food("lunch", "Chicken and rice", {"kcal": 480, "protein_g": 41, "fat_g": 9.6}, on="2026-10-12")
    fit.log_food("snack", "Protein shake", {"protein_g": 25}, on="2026-10-12")  # calories not known
    day = fit.day_totals("2026-10-12")
    assert day["totals"]["protein_g"] == 98 and day["totals"]["kcal"] == 1000  # counts what's known
    assert day["totals"]["sodium_mg"] is None  # nobody knows: unknown, not zero
    assert day["targets"] == {"kcal": 2400, "protein_g": 180}
    assert day["meals_logged"] == ["breakfast", "lunch", "snack"]
    assert fit.day_totals("2026-10-11")["totals"]["kcal"] is None


def test_the_rotation_moves_on_only_when_a_day_is_done(fit):
    fit.update_plan({"training": {"days": ["Mon", "Wed", "Fri"], "rotation": [
        {"name": "Push"}, {"name": "Pull"}, {"name": "Legs + carry"}]}})
    assert fit.today_training(MON)["name"] == "Push"
    assert fit.today_training(MON + timedelta(days=1)) is None  # Tuesday: rest
    fit.complete_training(MON)
    assert fit.today_training(MON)["done"] is True and fit.today_training(MON)["name"] == "Push"
    assert fit.today_training(MON + timedelta(days=2))["name"] == "Pull"
    # Missed Wednesday: Friday is still Pull, nothing skipped or doubled.
    assert fit.today_training(MON + timedelta(days=4))["name"] == "Pull"


def test_skill_practice_is_timed(fit):
    fit.log_skill("Handstand", "Wall hold", seconds=35)
    fit.log_skill("Handstand", "Wall hold", seconds=48)
    fit.log_skill("Handstand", minutes=12)
    assert fit.best_hold("handstand", "Wall hold") == 48
    assert fit.practice_minutes("Handstand") == 12


def test_milestones_and_the_plan_merge(fit):
    fit.update_plan({"milestones": [{"name": "60 s wall handstand"}, {"name": "First muscle-up"}],
                     "meals": {"prep_day": "Sun"}})
    plan = fit.plan
    assert plan["meals"]["prep_day"] == "Sun" and plan["meals"]["packed_lunch"] is False  # merged, not replaced
    first = plan["milestones"][0]
    assert first["done_on"] is None
    assert fit.complete_milestone(first["id"], on="2026-10-12")["done_on"] == "2026-10-12"
    with pytest.raises(ValueError):
        fit.complete_milestone("nope")


def test_everything_is_kept_and_read_back(fit, tmp_path):
    fit.log_weight(180, on="2026-10-12")
    fit.log_food("dinner", "Chili", {"kcal": 600})
    again = fm.FitnessManager(fit.context, data_dir=tmp_path / "robin")
    assert again.weigh_ins()[0]["weight"] == 180 and again.food_on(date.today().isoformat())[0]["name"] == "Chili"


def test_fitness_is_personal():
    from core.personal_data import PERSONAL_STORES

    assert ("fitness", fm.FitnessManager) in PERSONAL_STORES


def test_recipe_facts_typed_values_win():
    recipe = SimpleNamespace(servings=6, calories_per_serving=500.0, protein_g=None, carbs_g=None, fat_g=None, ingredients=[
        {"name": "chicken breast", "quantity": 2, "unit": "lb"}, {"name": "white rice", "quantity": 2, "unit": "cups"},
    ])
    facts = nutrition.recipe_facts(recipe)
    assert facts["kcal"] == 500 and facts["source"] == "mixed"
    assert 35 < facts["protein_g"] < 40  # 907 g chicken + 370 g rice, over 6
    assert nutrition.scaled(facts, 2)["kcal"] == 1000


def test_recipe_facts_never_undercount():
    recipe = SimpleNamespace(servings=2, calories_per_serving=None, protein_g=None, carbs_g=None, fat_g=None,
                             ingredients=[{"name": "chicken breast", "quantity": 1, "unit": "lb"},
                                          {"name": "dragon fruit", "quantity": 1, "unit": ""}])
    facts = nutrition.recipe_facts(recipe)
    assert facts["kcal"] is None and facts["source"] == "unknown" and facts["missing"] == ["dragon fruit"]


def test_plan_lines_typed_on_a_phone():
    from core.fitness_manager import exercise_text, parse_exercise, parse_skill_step, skill_step_text

    assert parse_exercise("Dips 3x8") == {"name": "Dips", "sets": 3, "reps": 8}
    assert parse_exercise("  L-sit 3 × 20s ") == {"name": "L-sit", "sets": 3, "hold_seconds": 20}
    assert parse_exercise("Plank 60 sec") == {"name": "Plank", "sets": 1, "hold_seconds": 60}
    assert parse_exercise("Farmer carry") == {"name": "Farmer carry"} and parse_exercise(" ") is None
    for line in ("Dips 3x8", "L-sit 3x20s", "Plank 60s", "Farmer carry"):
        assert exercise_text(parse_exercise(line)) == line
    assert parse_skill_step("Wall hold 60s") == {"name": "Wall hold", "target_seconds": 60}
    assert parse_skill_step("Tuck 10 reps") == {"name": "Tuck", "target_reps": 10}
    assert skill_step_text(parse_skill_step("Tuck 10 reps")) == "Tuck 10 reps"
