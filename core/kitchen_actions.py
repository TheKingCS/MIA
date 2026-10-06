"""
core.kitchen_actions
======================

Every change the Kitchen screen makes (2026-10-06, DEC-0017/0018), as
action kinds on the contract in core/actions.py, from the shared table in
core/record_actions.py: recipes (add, edit, delete, their ingredients
written one per line), the pantry (add, edit, delete), the grocery list
(add, check off, remove, clear the checked ones, add a recipe's missing
ingredients), the meal log (log a meal, remove one), and each person's
own favorites. The kitchen is the household's and in CHILD_APPS, so these
are child-safe, except deleting a recipe.
"""

from __future__ import annotations

import re

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import (Field, Record, add_describe, add_execute, delete_describe, delete_execute, field_dict,
                                 get, parse, record_form, record_kinds)


def _lists():
    from core.kitchen_manager import PANTRY_CATEGORIES, RECIPE_CATEGORIES

    return tuple(RECIPE_CATEGORIES), tuple(PANTRY_CATEGORIES)


_RECIPES, _PANTRY = _lists()

RECORDS: dict[str, Record] = {r.key: r for r in (
    Record("recipe", "recipe", "recipe_id", "get_recipe", "add_recipe", "update_recipe", "delete_recipe",
           store="kitchen", delete_note="The meals you logged with it stay in the meal log.", fields=(
               Field("name", "Name", "text", True),
               Field("category", "Meal", "choice", options=_RECIPES, default="Dinner", say="meal"),
               Field("servings", "Servings", "int", default=4),
               Field("prep_time_minutes", "Prep (minutes)", "int", default=0, say="prep"),
               Field("cook_time_minutes", "Cook (minutes)", "int", default=0, say="cook"),
               Field("calories_per_serving", "Calories per serving", "amount", say="calories"),
               Field("instructions", "Steps", "textarea"),
               Field("source", "From", "text", say="from"),
               Field("notes", "Notes", "textarea"),
           )),
    Record("pantry", "pantry item", "item_id", "get_pantry_item", "add_pantry_item", "update_pantry_item",
           "delete_pantry_item", store="kitchen", fields=(
               Field("name", "Name", "text", True),
               Field("quantity", "How much", "amount", default=0.0, say="amount"),
               Field("unit", "Unit", "text"),
               Field("category", "Shelf", "choice", options=_PANTRY, default="Pantry/Dry Goods", say="shelf",
                     quiet_default=True),
               Field("expiration_date", "Use by", "date", say="use by"),
               Field("notes", "Notes", "textarea"),
           )),
)}

GROCERY = Record("grocery", "grocery item", "item_id", "get_grocery_item", "add_grocery_item", "", "delete_grocery_item",
                 store="kitchen", fields=(Field("name", "Item", "text", True), Field("quantity", "How much", "amount", default=0.0, say="amount"),
                                          Field("unit", "Unit", "text")))

# ------------------------------------------------------------------ ingredients, one per line

_INGREDIENTS = Field("ingredients", "Ingredients (one per line, e.g. \"2 cups rice\")", "textarea")
_UNITS = r"cups?|c|tbsp|tablespoons?|tsp|teaspoons?|g|grams?|kg|lbs?|pounds?|oz|ounces?|ml|l|liters?|cans?|cloves?|pcs?|pieces?|slices?|pinch(?:es)?|bunch(?:es)?"
_LINE = re.compile(rf"^\s*(\d+\s+\d+/\d+|\d+(?:\.\d+)?(?:/\d+)?)?\s*({_UNITS})?\.?\s+(.+?)\s*$", re.IGNORECASE)


def parse_ingredients(text: str) -> list[dict]:
    """Pure logic. "2 cups rice\\n1/2 tsp salt\\neggs" -> the recipe's ingredient list."""
    found = []
    for line in (text or "").splitlines():
        line = line.strip(" -•\t")
        if not line:
            continue
        match = _LINE.match(" " + line) if line[0].isdigit() else None
        quantity, unit, name = 0.0, "", line
        if match and match.group(3):
            raw = (match.group(1) or "").strip()
            try:
                if " " in raw:
                    whole, frac = raw.split()
                    quantity = float(whole) + float(frac.split("/")[0]) / float(frac.split("/")[1])
                elif "/" in raw:
                    top, bottom = raw.split("/")
                    quantity = float(top) / float(bottom)
                elif raw:
                    quantity = float(raw)
            except (ValueError, ZeroDivisionError):
                quantity = 0.0
            unit, name = (match.group(2) or "").lower(), match.group(3)
        found.append({"name": name, "quantity": round(quantity, 3), "unit": unit, "notes": ""})
    return found


def ingredients_text(ingredients: list) -> str:
    """Pure logic. The other way round, for the edit form."""
    lines = []
    for item in ingredients or []:
        qty = item.get("quantity") or 0
        lines.append(" ".join(p for p in (f"{qty:g}" if qty else "", item.get("unit") or "", item.get("name") or "") if p))
    return "\n".join(lines)


def _recipe(context, params):
    return get(context, RECORDS["recipe"], params)


def _describe_ingredients(context, params) -> str:
    recipe = _recipe(context, params)
    items = parse_ingredients(params.get("ingredients", ""))
    return f"Set {recipe.name}'s ingredients ({len(items)}): " + (", ".join(i["name"] for i in items[:6]) or "none") + (
        "…" if len(items) > 6 else "")


def _set_ingredients(context, params) -> str:
    recipe = _recipe(context, params)
    context.kitchen.update_recipe(recipe.recipe_id, ingredients=parse_ingredients(params.get("ingredients", "")))
    return f"{recipe.name}'s ingredients are saved."


# ------------------------------------------------------------------ the grocery list


def _grocery(context, params):
    return get(context, GROCERY, params)


def _describe_check(context, params) -> str:
    item = _grocery(context, params)
    checked = params.get("checked", True) not in (False, "false", 0, "0")
    return f"{'Check off' if checked else 'Uncheck'} {item.name}"


def _check(context, params) -> str:
    item = _grocery(context, params)
    checked = params.get("checked", True) not in (False, "false", 0, "0")
    context.kitchen.set_grocery_item_checked(item.item_id, checked)
    return f"{item.name} is {'checked off' if checked else 'back on the list'}."


def _describe_clear(context, params) -> str:
    checked = [i for i in _need(context, "kitchen").all_grocery_items() if i.checked]
    if not checked:
        raise ActionError("Nothing is checked off yet.")
    return f"Clear {len(checked)} checked item{'s' if len(checked) != 1 else ''} off the grocery list"


def _clear(context, params) -> str:
    context.kitchen.clear_checked_grocery_items()
    return "The checked items are cleared."


def _describe_missing(context, params) -> str:
    from core.kitchen_manager import recipe_missing_ingredients

    recipe = _recipe(context, params)
    missing = recipe_missing_ingredients(recipe, context.kitchen.all_pantry_items())
    if not missing:
        raise ActionError(f"You have everything for {recipe.name}.")
    listed = {g.name.strip().lower() for g in context.kitchen.all_grocery_items()}
    to_add = [n for n in missing if n.strip().lower() not in listed]
    if not to_add:
        raise ActionError(f"What {recipe.name} needs is already on the grocery list.")
    return f"Add what's missing for {recipe.name} to the grocery list: " + ", ".join(to_add)


def _add_missing(context, params) -> str:
    recipe = _recipe(context, params)
    added = context.kitchen.add_missing_ingredients_to_grocery_list(recipe.recipe_id)
    return f"Added {len(added)} item{'s' if len(added) != 1 else ''} to the grocery list."


# ------------------------------------------------------------------ meals and favorites

_DATE = Field("date", "Date", "date")
_NOTES = Field("notes", "Notes", "textarea")


def _describe_meal(context, params) -> str:
    recipe = _recipe(context, params)
    if recipe.locked:
        raise ActionError(f"{recipe.name} is still locked.")
    when = parse(_DATE, params.get("date"))
    return f"Log a meal: {recipe.name}" + (f" on {when}" if when else " today")


def _log_meal(context, params) -> str:
    recipe = _recipe(context, params)
    context.kitchen.log_meal(recipe.recipe_id, parse(_DATE, params.get("date")), parse(_NOTES, params.get("notes")))
    return f"{recipe.name} is in the meal log."


def _meal(context, params):
    entry_id = str(params.get("entry_id", ""))
    entry = next((e for e in _need(context, "kitchen").all_meal_log_entries() if e.entry_id == entry_id), None)
    if entry is None:
        raise ActionError("That meal isn't in the log anymore.")
    recipe = context.kitchen.get_recipe(entry.recipe_id)
    return entry, recipe.name if recipe else "a meal"


def _describe_meal_delete(context, params) -> str:
    entry, name = _meal(context, params)
    return f"Remove {name} on {entry.date} from the meal log"


def _meal_delete(context, params) -> str:
    entry, name = _meal(context, params)
    context.kitchen.delete_meal_log_entry(entry.entry_id)
    return f"{name} on {entry.date} is removed."


def _who(context) -> str:
    from core.person_settings import person_id

    pid = person_id(context)
    if not pid:
        raise ActionError("Favorites belong to a person; sign in first.")
    return pid


def _describe_favorite(context, params) -> str:
    recipe = _recipe(context, params)
    on = params.get("favorite", True) not in (False, "false", 0, "0")
    return f"{'Add' if on else 'Remove'} {recipe.name} {'to' if on else 'from'} your favorites"


def _favorite(context, params) -> str:
    recipe = _recipe(context, params)
    on = params.get("favorite", True) not in (False, "false", 0, "0")
    context.kitchen.set_recipe_favorite(_who(context), recipe.recipe_id, on)
    return f"{recipe.name} is {'a favorite' if on else 'no longer a favorite'}."


# ------------------------------------------------------------------ the kinds


def _kinds() -> list[ActionType]:
    kinds = []
    for record in RECORDS.values():
        kinds += record_kinds(record, child_ok=True)
    kinds = [k for k in kinds if k.kind != "recipe.delete"] + [
        ActionType("recipe.delete", "Delete", {"recipe_id": "the recipe"}, delete_describe(RECORDS["recipe"]),
                   delete_execute(RECORDS["recipe"])),
        ActionType("recipe.ingredients", "Ingredients", {"recipe_id": "the recipe", "ingredients": "one per line"},
                   _describe_ingredients, _set_ingredients, True),
        ActionType("grocery.add", "Add", {"name": "the item", "quantity": "optional", "unit": "optional"},
                   add_describe(GROCERY), add_execute(GROCERY), True),
        ActionType("grocery.delete", "Remove", {"item_id": "the item"}, delete_describe(GROCERY), delete_execute(GROCERY), True),
        ActionType("grocery.check", "Check off", {"item_id": "the item", "checked": "true or false"}, _describe_check, _check, True),
        ActionType("grocery.clear_checked", "Clear checked", {}, _describe_clear, _clear, True),
        ActionType("grocery.from_recipe", "Add what's missing", {"recipe_id": "the recipe"}, _describe_missing, _add_missing, True),
        ActionType("meal.log", "Log meal", {"recipe_id": "the recipe", "date": "optional", "notes": "optional"},
                   _describe_meal, _log_meal, True),
        ActionType("meal.delete", "Remove", {"entry_id": "the meal"}, _describe_meal_delete, _meal_delete, True),
        ActionType("recipe.favorite", "Favorite", {"recipe_id": "the recipe", "favorite": "true or false"},
                   _describe_favorite, _favorite, True),
    ]
    return kinds


KITCHEN_ACTIONS: dict[str, ActionType] = {k.kind: k for k in _kinds()}
ACTION_TYPES.update(KITCHEN_ACTIONS)


def form_spec() -> dict:
    forms = {key: record_form(r) for key, r in RECORDS.items()}
    forms["grocery"] = record_form(GROCERY)
    forms["ingredients"] = {"noun": "ingredients", "id_param": "recipe_id", "fields": [field_dict(_INGREDIENTS)]}
    forms["meal"] = {"noun": "meal", "id_param": "recipe_id", "fields": [field_dict(_DATE), field_dict(_NOTES)]}
    return forms
