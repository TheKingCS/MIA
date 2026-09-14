"""
tests.test_kitchen_module
============================

Unit tests for modules.kitchen.module's pure row formatters — no Qt
event loop needed, same shape as tests/test_budget_module.py.
"""

from __future__ import annotations

from datetime import date

from core.kitchen_manager import GroceryListItem, MealLogEntry, PantryItem, Recipe
from modules.kitchen.module import (
    format_grocery_row,
    format_last_made_line,
    format_made_count_line,
    format_meal_log_row,
    format_pantry_row,
    format_rating_line,
    format_recipe_row,
    format_suggestion_row,
)


def _recipe(**overrides) -> Recipe:
    defaults = dict(recipe_id="r1", name="Weeknight Chili", category="Dinner", servings=6)
    defaults.update(overrides)
    return Recipe(**defaults)


def _pantry_item(**overrides) -> PantryItem:
    defaults = dict(item_id="p1", name="Ground Beef", quantity=2.0, unit="lbs", category="Meat", expiration_date="")
    defaults.update(overrides)
    return PantryItem(**defaults)


def test_format_recipe_row_includes_name_category_servings():
    recipe = _recipe()
    assert format_recipe_row(recipe) == "Weeknight Chili   [Dinner]   6 servings"


def test_format_recipe_row_includes_total_time_when_set():
    recipe = _recipe(prep_time_minutes=15, cook_time_minutes=45)
    assert format_recipe_row(recipe) == "Weeknight Chili   [Dinner]   6 servings  60 min"


def test_format_made_count_line_zero():
    assert format_made_count_line(0) == "Never made yet"


def test_format_made_count_line_nonzero():
    assert format_made_count_line(8) == "Made 8x"


def test_format_last_made_line_none():
    assert format_last_made_line(None) == "Never logged as made"


def test_format_last_made_line_with_a_date():
    assert format_last_made_line("2026-09-12") == "Last made: 2026-09-12"


def test_format_rating_line_not_rated():
    assert format_rating_line(None) == "Not rated yet"


def test_format_rating_line_with_a_rating():
    assert format_rating_line(4.5) == "Your rating: 4.5/5"


def test_format_recipe_row_omits_time_when_unset():
    recipe = _recipe(prep_time_minutes=0, cook_time_minutes=0)
    assert "min" not in format_recipe_row(recipe)


def test_format_recipe_row_shows_locked_prefix():
    recipe = _recipe(locked=True)
    assert format_recipe_row(recipe) == "(Locked) Weeknight Chili   [Dinner]   6 servings"


def test_format_recipe_row_omits_prefix_when_unlocked():
    recipe = _recipe(locked=False)
    assert not format_recipe_row(recipe).startswith("(Locked)")


def test_format_pantry_row_no_tag_when_expiration_not_tracked():
    item = _pantry_item(expiration_date="")
    row = format_pantry_row(item, date(2026, 9, 10))
    assert "[EXPIRE" not in row
    assert "Ground Beef" in row


def test_format_pantry_row_expired_tag():
    item = _pantry_item(expiration_date="2026-09-01")
    row = format_pantry_row(item, date(2026, 9, 10))
    assert row.startswith("[EXPIRED 9d]")


def test_format_pantry_row_expires_today_tag():
    item = _pantry_item(expiration_date="2026-09-10")
    row = format_pantry_row(item, date(2026, 9, 10))
    assert row.startswith("[EXPIRES TODAY]")


def test_format_pantry_row_expires_in_future_tag():
    item = _pantry_item(expiration_date="2026-09-15")
    row = format_pantry_row(item, date(2026, 9, 10))
    assert row.startswith("[EXPIRES IN 5d]")


def test_format_pantry_row_includes_quantity_unit_category():
    item = _pantry_item(quantity=2.0, unit="lbs", category="Meat")
    row = format_pantry_row(item, date(2026, 9, 10))
    assert "2 lbs" in row
    assert "[Meat]" in row


def test_format_grocery_row_includes_quantity_and_unit():
    item = GroceryListItem(item_id="g1", name="Milk", quantity=1.5, unit="gallon")
    assert format_grocery_row(item) == "Milk   1.5 gallon"


def test_format_grocery_row_flags_recipe_sourced_items():
    item = GroceryListItem(item_id="g1", name="Milk", quantity=1.0, unit="cup", source_recipe_id="r1")
    assert "(from recipe)" in format_grocery_row(item)


def test_format_grocery_row_omits_recipe_flag_for_manual_items():
    item = GroceryListItem(item_id="g1", name="Milk", quantity=1.0, unit="cup", source_recipe_id="")
    assert "(from recipe)" not in format_grocery_row(item)


def test_format_meal_log_row_includes_date_recipe_and_notes():
    entry = MealLogEntry(entry_id="m1", recipe_id="r1", date="2026-09-10", notes="family dinner")
    assert format_meal_log_row(entry, "Weeknight Chili") == "2026-09-10   Weeknight Chili  family dinner"


def test_format_meal_log_row_omits_notes_when_blank():
    entry = MealLogEntry(entry_id="m1", recipe_id="r1", date="2026-09-10", notes="")
    assert format_meal_log_row(entry, "Weeknight Chili") == "2026-09-10   Weeknight Chili"


def test_format_suggestion_row_fully_makeable():
    recipe = _recipe()
    assert format_suggestion_row(recipe, []) == "✓ Weeknight Chili — ready to make"


def test_format_suggestion_row_lists_missing_ingredients():
    recipe = _recipe()
    assert format_suggestion_row(recipe, ["Ground Beef", "Kidney Beans"]) == "Weeknight Chili — missing: Ground Beef, Kidney Beans"
