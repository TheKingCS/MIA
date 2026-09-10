"""
tests.test_kitchen_manager
=============================

Unit tests for core.kitchen_manager. Isolates _DATA_DIR/the four
per-record-type file constants into a tmp_path scratch area, same
monkeypatch pattern as test_real_estate_manager.py's isolated_paths.
"""

from __future__ import annotations

from datetime import date

import pytest

import core.kitchen_manager as kitchen_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.kitchen_manager import (
    GroceryListItem,
    KitchenManager,
    PantryItem,
    Recipe,
    days_until_expiration,
    recipe_missing_ingredients,
    recipes_makeable_from_pantry,
)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(kitchen_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(kitchen_manager_module, "_RECIPES_FILE", data_dir / "kitchen_recipes.json")
    monkeypatch.setattr(kitchen_manager_module, "_PANTRY_FILE", data_dir / "kitchen_pantry.json")
    monkeypatch.setattr(kitchen_manager_module, "_GROCERY_LIST_FILE", data_dir / "kitchen_grocery_list.json")
    monkeypatch.setattr(kitchen_manager_module, "_MEAL_LOG_FILE", data_dir / "kitchen_meal_log.json")
    return data_dir


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


def _make_manager(context: AppContext) -> KitchenManager:
    manager = KitchenManager(context)
    context.kitchen = manager
    return manager


def _recipe(recipe_id="r1", ingredients=None) -> Recipe:
    return Recipe(recipe_id=recipe_id, name="Weeknight Chili", ingredients=ingredients or [])


def _pantry_item(name="Ground Beef", quantity=2.0, unit="lbs", expiration_date="") -> PantryItem:
    return PantryItem(item_id="p1", name=name, quantity=quantity, unit=unit, expiration_date=expiration_date)


# ------------------------------------------------------------------
# Recipe CRUD
# ------------------------------------------------------------------

def test_add_recipe_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_recipe(name="Weeknight Chili", category="Dinner", servings=6)

    reloaded = KitchenManager(context)
    recipes = reloaded.all_recipes()
    assert len(recipes) == 1
    assert recipes[0].name == "Weeknight Chili"
    assert recipes[0].servings == 6


def test_add_recipe_rejects_unknown_category(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X", category="Nonsense")
    assert recipe.category == "Other"


def test_add_recipe_clamps_negative_servings_and_times(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X", servings=-5, prep_time_minutes=-10, cook_time_minutes=-10)
    assert recipe.servings == 1
    assert recipe.prep_time_minutes == 0
    assert recipe.cook_time_minutes == 0


def test_update_recipe_changes_fields(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.update_recipe(recipe.recipe_id, name="Y", servings=8)
    updated = manager.get_recipe(recipe.recipe_id)
    assert updated.name == "Y"
    assert updated.servings == 8


def test_delete_recipe_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.delete_recipe(recipe.recipe_id)
    assert manager.get_recipe(recipe.recipe_id) is None


def test_recipe_nutrition_defaults_to_none_not_zero(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    assert recipe.calories_per_serving is None
    assert recipe.protein_g is None
    assert recipe.carbs_g is None
    assert recipe.fat_g is None


# ------------------------------------------------------------------
# Ingredients
# ------------------------------------------------------------------

def test_add_ingredient_appends_to_recipe(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.add_ingredient(recipe.recipe_id, "Flour", 2.0, "cups", "sifted")
    updated = manager.get_recipe(recipe.recipe_id)
    assert updated.ingredients == [{"name": "Flour", "quantity": 2.0, "unit": "cups", "notes": "sifted"}]


def test_remove_ingredient_by_index(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.add_ingredient(recipe.recipe_id, "Flour", 2.0, "cups")
    manager.add_ingredient(recipe.recipe_id, "Sugar", 1.0, "cup")
    manager.remove_ingredient(recipe.recipe_id, 0)
    updated = manager.get_recipe(recipe.recipe_id)
    assert len(updated.ingredients) == 1
    assert updated.ingredients[0]["name"] == "Sugar"


def test_remove_ingredient_out_of_range_is_a_no_op(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.add_ingredient(recipe.recipe_id, "Flour", 2.0, "cups")
    manager.remove_ingredient(recipe.recipe_id, 5)
    assert len(manager.get_recipe(recipe.recipe_id).ingredients) == 1


# ------------------------------------------------------------------
# Pantry CRUD
# ------------------------------------------------------------------

def test_add_pantry_item_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_pantry_item(name="Flour", quantity=5.0, unit="lbs", category="Pantry/Dry Goods")

    reloaded = KitchenManager(context)
    items = reloaded.all_pantry_items()
    assert len(items) == 1
    assert items[0].name == "Flour"
    assert items[0].quantity == 5.0


def test_add_pantry_item_rejects_unknown_category(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    item = manager.add_pantry_item(name="X", category="Nonsense")
    assert item.category == "Other"


def test_update_pantry_item_clamps_negative_quantity(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    item = manager.add_pantry_item(name="X", quantity=5.0)
    manager.update_pantry_item(item.item_id, quantity=-3.0)
    assert manager.get_pantry_item(item.item_id).quantity == 0.0


def test_delete_pantry_item_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    item = manager.add_pantry_item(name="X")
    manager.delete_pantry_item(item.item_id)
    assert manager.get_pantry_item(item.item_id) is None


# ------------------------------------------------------------------
# days_until_expiration — pure logic
# ------------------------------------------------------------------

def test_days_until_expiration_none_when_not_tracked():
    item = _pantry_item(expiration_date="")
    assert days_until_expiration(item, date(2026, 9, 10)) is None


def test_days_until_expiration_negative_when_expired():
    item = _pantry_item(expiration_date="2026-09-01")
    assert days_until_expiration(item, date(2026, 9, 10)) == -9


def test_days_until_expiration_zero_when_today():
    item = _pantry_item(expiration_date="2026-09-10")
    assert days_until_expiration(item, date(2026, 9, 10)) == 0


def test_days_until_expiration_positive_when_future():
    item = _pantry_item(expiration_date="2026-09-15")
    assert days_until_expiration(item, date(2026, 9, 10)) == 5


# ------------------------------------------------------------------
# recipe_missing_ingredients / recipes_makeable_from_pantry
# ------------------------------------------------------------------

def test_recipe_missing_ingredients_empty_when_fully_stocked():
    recipe = _recipe(ingredients=[{"name": "Flour", "quantity": 2.0, "unit": "cups", "notes": ""}])
    pantry = [_pantry_item(name="Flour", quantity=5.0, unit="cups")]
    assert recipe_missing_ingredients(recipe, pantry) == []


def test_recipe_missing_ingredients_when_absent():
    recipe = _recipe(ingredients=[{"name": "Flour", "quantity": 2.0, "unit": "cups", "notes": ""}])
    assert recipe_missing_ingredients(recipe, []) == ["Flour"]


def test_recipe_missing_ingredients_matching_unit_checks_quantity():
    recipe = _recipe(ingredients=[{"name": "Eggs", "quantity": 3.0, "unit": "each", "notes": ""}])
    pantry = [_pantry_item(name="Eggs", quantity=2.0, unit="each")]
    assert recipe_missing_ingredients(recipe, pantry) == ["Eggs"]


def test_recipe_missing_ingredients_mismatched_unit_falls_back_to_presence_only():
    # Pantry has 5 lbs of flour; recipe wants 2 cups — units don't
    # match, so this is a real, honest "presence only" case, not a
    # fabricated cross-unit quantity comparison.
    recipe = _recipe(ingredients=[{"name": "Flour", "quantity": 2.0, "unit": "cups", "notes": ""}])
    pantry = [_pantry_item(name="Flour", quantity=5.0, unit="lbs")]
    assert recipe_missing_ingredients(recipe, pantry) == []


def test_recipe_missing_ingredients_case_insensitive_name_match():
    recipe = _recipe(ingredients=[{"name": "FLOUR", "quantity": 1.0, "unit": "", "notes": ""}])
    pantry = [_pantry_item(name="flour", quantity=1.0, unit="")]
    assert recipe_missing_ingredients(recipe, pantry) == []


def test_recipes_makeable_from_pantry_sorts_fewest_missing_first():
    fully_makeable = _recipe(recipe_id="r1", ingredients=[{"name": "Eggs", "quantity": 1.0, "unit": "each", "notes": ""}])
    fully_makeable.name = "A Recipe"
    partly_makeable = _recipe(recipe_id="r2", ingredients=[
        {"name": "Eggs", "quantity": 1.0, "unit": "each", "notes": ""},
        {"name": "Milk", "quantity": 1.0, "unit": "cup", "notes": ""},
    ])
    partly_makeable.name = "B Recipe"
    pantry = [_pantry_item(name="Eggs", quantity=5.0, unit="each")]

    results = recipes_makeable_from_pantry([partly_makeable, fully_makeable], pantry)
    assert [r.recipe_id for r, _ in results] == ["r1", "r2"]
    assert results[0][1] == []
    assert results[1][1] == ["Milk"]


# ------------------------------------------------------------------
# Grocery list CRUD + add_missing_ingredients_to_grocery_list
# ------------------------------------------------------------------

def test_add_grocery_item_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_grocery_item(name="Milk", quantity=1.0, unit="gallon")

    reloaded = KitchenManager(context)
    items = reloaded.all_grocery_items()
    assert len(items) == 1
    assert items[0].name == "Milk"


def test_set_grocery_item_checked(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    item = manager.add_grocery_item(name="Milk")
    manager.set_grocery_item_checked(item.item_id, True)
    assert manager.get_grocery_item(item.item_id).checked is True


def test_clear_checked_grocery_items_removes_only_checked(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    checked = manager.add_grocery_item(name="Milk")
    unchecked = manager.add_grocery_item(name="Eggs")
    manager.set_grocery_item_checked(checked.item_id, True)
    manager.clear_checked_grocery_items()
    remaining = manager.all_grocery_items()
    assert len(remaining) == 1
    assert remaining[0].item_id == unchecked.item_id


def test_add_missing_ingredients_to_grocery_list_adds_only_missing(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.add_ingredient(recipe.recipe_id, "Flour", 2.0, "cups")
    manager.add_ingredient(recipe.recipe_id, "Eggs", 2.0, "each")
    manager.add_pantry_item(name="Flour", quantity=5.0, unit="cups")

    added = manager.add_missing_ingredients_to_grocery_list(recipe.recipe_id)
    assert [a.name for a in added] == ["Eggs"]
    assert [g.name for g in manager.all_grocery_items()] == ["Eggs"]


def test_add_missing_ingredients_to_grocery_list_skips_existing_duplicates(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.add_ingredient(recipe.recipe_id, "Eggs", 2.0, "each")
    manager.add_grocery_item(name="eggs")  # already on the list, different casing

    added = manager.add_missing_ingredients_to_grocery_list(recipe.recipe_id)
    assert added == []
    assert len(manager.all_grocery_items()) == 1


# ------------------------------------------------------------------
# Meal log + meal-frequency queries
# ------------------------------------------------------------------

def test_log_meal_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.log_meal(recipe.recipe_id, "2026-09-01", "family dinner")

    reloaded = KitchenManager(context)
    entries = reloaded.all_meal_log_entries()
    assert len(entries) == 1
    assert entries[0].recipe_id == recipe.recipe_id
    assert entries[0].notes == "family dinner"


def test_log_meal_defaults_to_today(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    entry = manager.log_meal(recipe.recipe_id)
    assert entry.date == date.today().isoformat()


def test_times_made_counts_within_range(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.log_meal(recipe.recipe_id, "2026-01-01")
    manager.log_meal(recipe.recipe_id, "2026-06-01")
    manager.log_meal(recipe.recipe_id, "2026-09-01")

    assert manager.times_made(recipe.recipe_id) == 3
    assert manager.times_made(recipe.recipe_id, start_date="2026-05-01") == 2
    assert manager.times_made(recipe.recipe_id, start_date="2026-05-01", end_date="2026-07-01") == 1


def test_last_made_date_returns_most_recent(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.log_meal(recipe.recipe_id, "2026-01-01")
    manager.log_meal(recipe.recipe_id, "2026-09-01")
    assert manager.last_made_date(recipe.recipe_id) == "2026-09-01"


def test_last_made_date_none_when_never_made(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    assert manager.last_made_date(recipe.recipe_id) is None


def test_delete_meal_log_entry_removes_it(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    entry = manager.log_meal(recipe.recipe_id, "2026-09-01")
    manager.delete_meal_log_entry(entry.entry_id)
    assert manager.all_meal_log_entries() == []


# ------------------------------------------------------------------
# recipes_makeable_now — manager convenience wrapper
# ------------------------------------------------------------------

def test_recipes_makeable_now_uses_current_recipes_and_pantry(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    recipe = manager.add_recipe(name="X")
    manager.add_ingredient(recipe.recipe_id, "Eggs", 2.0, "each")
    manager.add_pantry_item(name="Eggs", quantity=6.0, unit="each")

    results = manager.recipes_makeable_now()
    assert len(results) == 1
    assert results[0][0].recipe_id == recipe.recipe_id
    assert results[0][1] == []
