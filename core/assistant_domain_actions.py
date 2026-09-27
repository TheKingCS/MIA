"""
core.assistant_domain_actions
===============================

Assistant actions added by the 2026-09-27 conversational audit
(docs/ASSISTANT_AUDIT.md), so what the owner *says* updates the right
records: kitchen (recipes, meals, grocery list, pantry), debts and budget
targets, asset details and notes (including greenhouse/garden plants,
which are Maintenance assets in the Garden/Plant category), and
quantities for parts, materials and products.

Also registers each domain's everyday vocabulary and the names of the
user's own records with the registry (see
AssistantActionRegistry.register_domain_keywords()/register_entity_names()),
so "I watered the tomatoes" or "plywood costs $42 now" reaches the right
tools without the user knowing any trigger phrase.

Every handler is a pure function of (context, arguments) returning a
short sentence to speak back, same contract as core/application.py's
handlers. Record lookup goes through core.assistant_lookup.resolve_by_name()
(tolerant, but only acts on one unambiguous match). Nothing here deletes.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from core.app_context import AppContext
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_lookup import resolve_by_name

_NO_PARAMS = {"type": "object", "properties": {}, "required": []}

_UNIT_WORDS = {
    "lb", "lbs", "pound", "pounds", "oz", "ounce", "ounces", "g", "gram", "grams", "kg", "kgs",
    "cup", "cups", "tbsp", "tablespoon", "tablespoons", "tsp", "teaspoon", "teaspoons",
    "can", "cans", "jar", "jars", "bag", "bags", "box", "boxes", "bottle", "bottles",
    "dozen", "gallon", "gallons", "quart", "quarts", "pint", "pints", "liter", "liters",
    "clove", "cloves", "bunch", "bunches", "head", "heads", "pack", "packs", "loaf", "loaves",
    "stick", "sticks", "slice", "slices", "sheet", "sheets", "ft", "feet", "piece", "pieces",
}
_WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "half": 0.5,
}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def parse_quantity_phrase(text: str) -> tuple[float, str, str]:
    """Pure logic. "2 lb ground venison" -> (2.0, "lb", "ground venison");
    "a dozen eggs" -> (1.0, "dozen", "eggs"); "milk" -> (0.0, "", "milk").
    Handles fractions ("1/2 cup") and mixed numbers ("1 1/2 cups")."""
    words = str(text).strip().split()
    quantity = 0.0
    i = 0
    while i < len(words):
        w = words[i].lower().strip(",")
        if re.fullmatch(r"\d+(\.\d+)?", w):
            quantity += float(w)
        elif re.fullmatch(r"\d+/\d+", w):
            num, den = w.split("/")
            quantity += float(num) / float(den) if float(den) else 0.0
        elif w in _WORD_NUMBERS and i < len(words) - 1:
            quantity += _WORD_NUMBERS[w]
        else:
            break
        i += 1
    unit = ""
    if i < len(words) - 1 and words[i].lower().strip(",.") in _UNIT_WORDS:
        unit = words[i].lower().strip(",.")
        i += 1
        if i < len(words) - 1 and words[i].lower() == "of":
            i += 1
    name = " ".join(words[i:]).strip(" ,.")
    return quantity, unit, name


def _as_list(value) -> list[str]:
    """Tool arguments may arrive as a list or a comma/"and"-separated string."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = [str(v) for v in value]
    else:
        items = re.split(r",|\band\b", str(value))
    return [i.strip() for i in items if i and i.strip()]


def _num(value, default: Optional[float] = None) -> Optional[float]:
    if value in (None, ""):
        return default
    try:
        return float(str(value).replace("$", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        return default


def _money(amount: float) -> str:
    return f"${amount:,.2f}"


def _qty(quantity: float, unit: str) -> str:
    return f"{quantity:g}{(' ' + unit) if unit else ''}"


def _component_label(c) -> str:
    return " ".join(part for part in (c.value, c.name) if part).strip() or c.name


# ---------------------------------------------------------------------------
# Maintenance / greenhouse: asset details and notes
# ---------------------------------------------------------------------------


def _find_asset(context: AppContext, name: str):
    return resolve_by_name(context.maintenance.all_assets(), name, lambda a: a.name, "tracked item")


def _action_update_maintenance_asset(context: AppContext, arguments: dict) -> str:
    asset, error = _find_asset(context, str(arguments.get("asset_name", "")))
    if error:
        return error
    from core.maintenance_manager import ASSET_CATEGORIES

    fields = {}
    for key in ("manufacturer", "model", "serial_number", "purchase_date"):
        value = str(arguments.get(key, "") or "").strip()
        if value:
            fields[key] = value
    category = str(arguments.get("category", "") or "").strip()
    if category:
        match = next((c for c in ASSET_CATEGORIES if c.lower() == category.lower()), None)
        if match:
            fields["category"] = match
    new_name = str(arguments.get("new_name", "") or "").strip()
    if new_name:
        fields["name"] = new_name
    if not fields:
        return f"What should I update about {asset.name}? I can store its make, model, serial number, purchase date, category or name."
    context.maintenance.update_asset(asset.asset_id, **fields)
    described = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in fields.items())
    return f"Updated {asset.name}: {described}."


def _action_get_maintenance_asset(context: AppContext, arguments: dict) -> str:
    asset, error = _find_asset(context, str(arguments.get("asset_name", "")))
    if error:
        return error
    from core.maintenance_manager import days_until_due

    parts = [f"{asset.name} ({asset.category})"]
    make = " ".join(p for p in (asset.manufacturer, asset.model) if p)
    if make:
        parts.append(f"a {make}")
    if asset.serial_number:
        parts.append(f"serial {asset.serial_number}")
    if asset.purchase_date:
        parts.append(f"bought {asset.purchase_date}")
    lines = [", ".join(parts) + "."]

    task_bits = []
    today = date.today()
    for task in context.maintenance.tasks_for_asset(asset.asset_id):
        remaining = days_until_due(task, today) if task.trigger_type == "calendar" else None
        if remaining is None:
            task_bits.append(task.title)
        elif remaining < 0:
            task_bits.append(f"{task.title} (overdue {-remaining} days)")
        else:
            task_bits.append(f"{task.title} (due in {remaining} days)")
    if task_bits:
        lines.append("Maintenance: " + "; ".join(task_bits) + ".")
    for meter in context.maintenance.asset_meter_names(asset.asset_id):
        readings = context.maintenance.asset_readings(asset.asset_id, meter)
        if readings:
            latest = readings[-1]
            lines.append(f"Latest {meter}: {latest.value:g}{(' ' + latest.unit) if latest.unit else ''}.")
    if asset.documents:
        lines.append(f"{len(asset.documents)} document(s) attached.")
    if asset.notes.strip():
        recent = [n for n in asset.notes.strip().splitlines() if n.strip()][-3:]
        lines.append("Notes: " + " / ".join(recent))
    return " ".join(lines)


def _action_add_asset_note(context: AppContext, arguments: dict) -> str:
    asset, error = _find_asset(context, str(arguments.get("asset_name", "")))
    if error:
        return error
    note = str(arguments.get("note", "") or "").strip()
    if not note:
        return f"What should I note about {asset.name}?"
    line = f"{date.today().isoformat()}: {note}"
    notes = f"{asset.notes.rstrip()}\n{line}" if asset.notes.strip() else line
    context.maintenance.update_asset(asset.asset_id, notes=notes)
    return f"Noted on {asset.name}: {note}"


# ---------------------------------------------------------------------------
# Debts & budget targets
# ---------------------------------------------------------------------------


def _find_debt(context: AppContext, name: str):
    return resolve_by_name(context.budget.all_debts(), name, lambda d: d.name, "debt")


def _action_add_debt(context: AppContext, arguments: dict) -> str:
    from core.budget_manager import DEBT_TYPES

    name = str(arguments.get("name", "") or "").strip()
    balance = _num(arguments.get("balance"))
    if not name or balance is None:
        return "I need the debt's name and current balance."
    rate = _num(arguments.get("interest_rate"), 0.0)
    debt_type = str(arguments.get("debt_type", "") or "").strip()
    debt_type = next((t for t in DEBT_TYPES if t.lower() == debt_type.lower()), "Other" if debt_type else "Credit Card")
    promo = _num(arguments.get("promo_apr"))
    promo_expires = str(arguments.get("promo_expires_date", "") or "").strip() or None
    debt = context.budget.add_debt(
        name=name, balance=max(0.0, balance), interest_rate=max(0.0, rate),
        minimum_payment=max(0.0, _num(arguments.get("minimum_payment"), 0.0)),
        debt_type=debt_type, promo_apr=promo if promo_expires else None, promo_expires_date=promo_expires,
    )
    promo_note = f", {promo:g}% promo until {promo_expires}" if promo is not None and promo_expires else ""
    missing = "" if rate else " What's its interest rate? I'll rank it better once I know."
    return f"Added {debt.name}: {_money(debt.balance)} at {debt.interest_rate:g}% APR{promo_note}.{missing}"


def _action_update_debt(context: AppContext, arguments: dict) -> str:
    debt, error = _find_debt(context, str(arguments.get("debt_name", "")))
    if error:
        return error
    fields = {}
    for key in ("balance", "interest_rate", "minimum_payment", "promo_apr"):
        value = _num(arguments.get(key))
        if value is not None:
            fields[key] = max(0.0, value)
    promo_expires = str(arguments.get("promo_expires_date", "") or "").strip()
    if promo_expires:
        fields["promo_expires_date"] = promo_expires
    if not fields:
        return f"What changed on {debt.name}? I can update the balance, interest rate, minimum payment or promo rate."
    if debt.plaid_account_id and "balance" in fields:
        note = " (It's bank-synced, so the next sync will set the balance from your bank.)"
    else:
        note = ""
    context.budget.update_debt(debt.debt_id, **fields)
    described = ", ".join(f"{k.replace('_', ' ')} {v:g}" if isinstance(v, float) else f"{k.replace('_', ' ')} {v}" for k, v in fields.items())
    return f"Updated {debt.name}: {described}.{note}"


def _action_list_debts(context: AppContext, arguments: dict) -> str:
    from core.budget_manager import effective_apr

    debts = [d for d in context.budget.all_debts() if d.balance > 0]
    if not debts:
        return "You don't have any debts tracked. Nice, or tell me about one to start tracking it."
    today = date.today()
    lines = [f"{d.name}: {_money(d.balance)} at {effective_apr(d, today):g}%" for d in debts]
    total = context.budget.total_debt_balance()
    minimums = context.budget.total_minimum_debt_payments()
    return f"You owe {_money(total)} across {len(debts)} debts, with {_money(minimums)} a month in minimums. " + "; ".join(lines) + "."


def _action_record_debt_payment(context: AppContext, arguments: dict) -> str:
    debt, error = _find_debt(context, str(arguments.get("debt_name", "")))
    if error:
        return error
    amount = _num(arguments.get("amount"))
    if amount is None or amount <= 0:
        return f"How much did you pay toward {debt.name}?"
    paid_on = str(arguments.get("date", "") or "").strip() or None
    context.budget.record_debt_payment(debt.debt_id, amount, date=paid_on)
    remaining = context.budget.get_debt(debt.debt_id).balance
    tail = " That one's paid off!" if remaining <= 0 else f" {_money(remaining)} left."
    return f"Recorded a {_money(amount)} payment on {debt.name}.{tail}"


def _action_get_debt_payoff_plan(context: AppContext, arguments: dict) -> str:
    strategy = str(arguments.get("strategy", "") or "hybrid").strip().lower()
    ranked = context.budget.debt_payoff_priority(strategy=strategy)
    if not ranked:
        return "You don't have any open debts to plan around."
    lines = [f"#{p.rank} {p.debt.name} ({_money(p.debt.balance)}): {p.reason}" for p in ranked[:5]]
    return (
        f"Pay the minimums on everything, then put extra toward #1. "
        + " ".join(lines)
    )


def _action_set_budget_target(context: AppContext, arguments: dict) -> str:
    from core.budget_manager import EXPENSE_CATEGORIES

    wanted = str(arguments.get("category", "") or "").strip()
    amount = _num(arguments.get("monthly_amount"))
    if amount is None:
        return "How much per month should I budget?"
    category, error = resolve_by_name(EXPENSE_CATEGORIES, wanted, str, "budget category")
    if error:
        return error
    context.budget.set_budget_target(category, max(0.0, amount))
    return f"Set your {category} budget to {_money(amount)} a month."


# ---------------------------------------------------------------------------
# Kitchen: recipes & meals
# ---------------------------------------------------------------------------


def _find_recipe(context: AppContext, name: str):
    return resolve_by_name(context.kitchen.all_recipes(), name, lambda r: r.name, "recipe")


def _action_add_recipe(context: AppContext, arguments: dict) -> str:
    from core.kitchen_manager import RECIPE_CATEGORIES

    name = str(arguments.get("name", "") or "").strip()
    if not name:
        return "What's the recipe called?"
    existing = next((r for r in context.kitchen.all_recipes() if r.name.lower() == name.lower()), None)
    if existing is not None:
        return f"You already have a recipe called {existing.name}."
    category = str(arguments.get("category", "") or "").strip()
    category = next((c for c in RECIPE_CATEGORIES if c.lower() == category.lower()), "Dinner")
    servings = int(_num(arguments.get("servings"), 4) or 4)
    recipe = context.kitchen.add_recipe(
        name=name, category=category, servings=servings,
        instructions=str(arguments.get("instructions", "") or "").strip(),
    )
    ingredients = _as_list(arguments.get("ingredients"))
    for line in ingredients:
        quantity, unit, ingredient = parse_quantity_phrase(line)
        if ingredient:
            context.kitchen.add_ingredient(recipe.recipe_id, ingredient, quantity=quantity, unit=unit)
    detail = f" with {len(ingredients)} ingredients" if ingredients else ". Tell me the ingredients whenever you're ready"
    return f"Saved {recipe.name} as a {category.lower()} recipe{detail}."


def _action_list_recipes(context: AppContext, arguments: dict) -> str:
    query = str(arguments.get("query", "") or "").strip().lower()
    recipes = [r for r in context.kitchen.all_recipes() if not query or query in r.name.lower() or query == r.category.lower()]
    if not recipes:
        return "No recipes match that." if query else "You haven't saved any recipes yet."
    names = ", ".join(f"{r.name}{' (locked)' if r.locked else ''}" for r in recipes[:15])
    more = f", and {len(recipes) - 15} more" if len(recipes) > 15 else ""
    return f"You have {len(recipes)} recipe(s): {names}{more}."


def _action_suggest_recipes(context: AppContext, arguments: dict) -> str:
    options = [(r, missing) for r, missing in context.kitchen.recipes_makeable_now() if not r.locked]
    if not options:
        return "I don't have any recipes to suggest yet. Save a few and keep your pantry updated, and I'll match them up."
    ready = [r.name for r, missing in options if not missing]
    close = [(r.name, missing) for r, missing in options if 0 < len(missing) <= 2]
    parts = []
    if ready:
        parts.append("You can make " + ", ".join(ready[:5]) + " with what you have.")
    if close:
        parts.append(" ".join(f"{name} just needs {', '.join(missing)}." for name, missing in close[:3]))
    if not parts:
        return "Nothing's fully covered by your pantry right now. Want me to add a recipe's ingredients to the grocery list?"
    return " ".join(parts)


def _action_log_meal(context: AppContext, arguments: dict) -> str:
    recipe, error = _find_recipe(context, str(arguments.get("recipe_name", "")))
    if error:
        return error
    when = str(arguments.get("date", "") or "").strip() or None
    context.kitchen.log_meal(recipe.recipe_id, date_str=when, notes=str(arguments.get("notes", "") or ""))
    times = context.kitchen.times_made(recipe.recipe_id)
    return f"Logged {recipe.name}. That's {times} time(s) you've made it."


# ---------------------------------------------------------------------------
# Groceries & pantry
# ---------------------------------------------------------------------------


def _action_add_grocery_item(context: AppContext, arguments: dict) -> str:
    items = _as_list(arguments.get("items")) or _as_list(arguments.get("name"))
    if not items:
        return "What should I add to the grocery list?"
    open_names = {g.name.lower() for g in context.kitchen.all_grocery_items() if not g.checked}
    added, skipped = [], []
    for line in items:
        quantity, unit, name = parse_quantity_phrase(line)
        if not name:
            continue
        if name.lower() in open_names:
            skipped.append(name)
            continue
        context.kitchen.add_grocery_item(name, quantity=quantity, unit=unit)
        open_names.add(name.lower())
        added.append(name)
    reply = f"Added {', '.join(added)} to the grocery list." if added else ""
    if skipped:
        reply += f" {', '.join(skipped)} {'was' if len(skipped) == 1 else 'were'} already on it."
    return reply.strip() or "Nothing new to add."


def _action_list_grocery_list(context: AppContext, arguments: dict) -> str:
    open_items = [g for g in context.kitchen.all_grocery_items() if not g.checked]
    if not open_items:
        return "Your grocery list is empty."
    names = [f"{_qty(g.quantity, g.unit)} {g.name}" if g.quantity else g.name for g in open_items]
    return f"On the grocery list: {', '.join(names)}."


def _action_check_off_grocery_item(context: AppContext, arguments: dict) -> str:
    items = _as_list(arguments.get("items")) or _as_list(arguments.get("name"))
    open_items = [g for g in context.kitchen.all_grocery_items() if not g.checked]
    if not items:
        return "Which item did you get?"
    done, problems = [], []
    for wanted in items:
        item, error = resolve_by_name(open_items, parse_quantity_phrase(wanted)[2] or wanted, lambda g: g.name, "grocery list item")
        if error:
            problems.append(error)
            continue
        context.kitchen.set_grocery_item_checked(item.item_id, True)
        open_items.remove(item)
        done.append(item.name)
    reply = f"Checked off {', '.join(done)}." if done else ""
    return " ".join(p for p in [reply, *problems] if p)


def _action_add_recipe_ingredients_to_grocery_list(context: AppContext, arguments: dict) -> str:
    recipe, error = _find_recipe(context, str(arguments.get("recipe_name", "")))
    if error:
        return error
    if not recipe.ingredients:
        return f"{recipe.name} doesn't have any ingredients saved yet."
    added = context.kitchen.add_missing_ingredients_to_grocery_list(recipe.recipe_id)
    if not added:
        return f"You already have (or have listed) everything for {recipe.name}."
    return f"Added what you need for {recipe.name}: {', '.join(g.name for g in added)}."


def _find_pantry(context: AppContext, name: str):
    return resolve_by_name(context.kitchen.all_pantry_items(), name, lambda p: p.name, "pantry item")


def _action_add_pantry_item(context: AppContext, arguments: dict) -> str:
    from core.kitchen_manager import PANTRY_CATEGORIES

    raw_name = str(arguments.get("name", "") or "").strip()
    if not raw_name:
        return "What should I add to the pantry?"
    parsed_qty, parsed_unit, parsed_name = parse_quantity_phrase(raw_name)
    name = parsed_name or raw_name
    quantity = _num(arguments.get("quantity"), parsed_qty or 0.0)
    unit = str(arguments.get("unit", "") or parsed_unit).strip()
    existing = next((p for p in context.kitchen.all_pantry_items() if p.name.lower() == name.lower()), None)
    if existing is not None:
        context.kitchen.update_pantry_item(existing.item_id, quantity=quantity, unit=unit or existing.unit)
        return f"Updated {existing.name} in the pantry to {_qty(quantity, unit or existing.unit)}."
    category = str(arguments.get("category", "") or "").strip()
    category = next((c for c in PANTRY_CATEGORIES if c.lower() == category.lower()), "Pantry/Dry Goods")
    item = context.kitchen.add_pantry_item(name, quantity=quantity, unit=unit, category=category)
    return f"Added {_qty(item.quantity, item.unit)} {item.name} to the pantry." if item.quantity else f"Added {item.name} to the pantry."


def _action_update_pantry_item(context: AppContext, arguments: dict) -> str:
    item, error = _find_pantry(context, str(arguments.get("name", "")))
    if error:
        return error
    quantity = _num(arguments.get("quantity"))
    if quantity is None:
        return f"How much {item.name} do you have now?"
    unit = str(arguments.get("unit", "") or item.unit).strip()
    context.kitchen.update_pantry_item(item.item_id, quantity=max(0.0, quantity), unit=unit)
    if quantity <= 0:
        return f"Marked {item.name} as out. Want me to add it to the grocery list?"
    return f"{item.name} is now at {_qty(quantity, unit)}."


def _action_list_pantry(context: AppContext, arguments: dict) -> str:
    items = context.kitchen.all_pantry_items()
    if not items:
        return "Your pantry list is empty."
    have = [f"{_qty(p.quantity, p.unit)} {p.name}" if p.quantity else p.name for p in items if p.quantity > 0]
    out = [p.name for p in items if p.quantity <= 0]
    reply = f"In the pantry: {', '.join(have)}." if have else ""
    if out:
        reply += f" You're out of {', '.join(out)}."
    return reply.strip()


# ---------------------------------------------------------------------------
# Parts, materials, products: quantities & details
# ---------------------------------------------------------------------------


def _action_adjust_component_quantity(context: AppContext, arguments: dict) -> str:
    component, error = resolve_by_name(context.components.all_components(), str(arguments.get("name", "")), _component_label, "part")
    if error:
        return error
    delta = _num(arguments.get("delta"))
    if delta is None or delta == 0:
        return f"How many {_component_label(component)} did you use or add?"
    updated = context.components.adjust_quantity(component.component_id, int(delta))
    verb = "Added" if delta > 0 else "Used"
    return f"{verb} {abs(int(delta))} {_component_label(component)}. You have {updated.quantity} now."


def _action_adjust_material_quantity(context: AppContext, arguments: dict) -> str:
    material, error = resolve_by_name(context.materials.all_materials(), str(arguments.get("name", "")), lambda m: m.name, "material")
    if error:
        return error
    delta = _num(arguments.get("delta"))
    if delta is None or delta == 0:
        return f"How much {material.name} did you use or add?"
    updated = context.materials.adjust_quantity(material.material_id, delta)
    verb = "Added" if delta > 0 else "Used"
    low = " That's at or below your reorder level." if updated.reorder_threshold and updated.quantity_on_hand <= updated.reorder_threshold else ""
    return f"{verb} {_qty(abs(delta), material.unit)} of {material.name}. {_qty(updated.quantity_on_hand, material.unit)} on hand.{low}"


def _action_update_material(context: AppContext, arguments: dict) -> str:
    material, error = resolve_by_name(context.materials.all_materials(), str(arguments.get("name", "")), lambda m: m.name, "material")
    if error:
        return error
    fields = {}
    for key in ("unit_cost", "reorder_threshold", "quantity_on_hand"):
        value = _num(arguments.get(key))
        if value is not None:
            fields[key] = max(0.0, value)
    for key in ("unit", "supplier", "location"):
        value = str(arguments.get(key, "") or "").strip()
        if value:
            fields[key] = value
    if not fields:
        return f"What changed about {material.name}? I can update its cost, unit, supplier, location, amount on hand or reorder level."
    context.materials.update_material(material.material_id, **fields)
    described = ", ".join(
        f"{k.replace('_', ' ')} {_money(v) if k == 'unit_cost' else (f'{v:g}' if isinstance(v, float) else v)}"
        for k, v in fields.items()
    )
    return f"Updated {material.name}: {described}."


def _action_adjust_product_stock(context: AppContext, arguments: dict) -> str:
    product, error = resolve_by_name(context.products.all_products(), str(arguments.get("name", "")), lambda p: p.name, "product")
    if error:
        return error
    delta = _num(arguments.get("delta"))
    if delta is None or delta == 0:
        return f"How many {product.name} did you make or remove?"
    updated = context.products.adjust_stock(product.product_id, delta)
    verb = "Added" if delta > 0 else "Removed"
    return f"{verb} {abs(delta):g} {product.name}. {updated.quantity_in_stock:g} in stock."


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _obj(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _s(description: str) -> dict:
    return {"type": "string", "description": description}


def _n(description: str) -> dict:
    return {"type": "number", "description": description}


def _list(description: str) -> dict:
    return {"type": "array", "items": {"type": "string"}, "description": description}


def register_domain_actions(registry: AssistantActionRegistry) -> None:
    # -- maintenance (assets incl. greenhouse/garden plants) --------------
    registry.register(AssistantAction(
        name="update_maintenance_asset", domain="maintenance",
        description="Save details the user states about one of their tracked vehicles, tools, appliances or plants: make, model, serial number, purchase date, category, or a new name.",
        parameters=_obj({
            "asset_name": _s("The item as the user referred to it, e.g. 'mower' or 'truck'."),
            "manufacturer": _s("Make/brand, e.g. 'John Deere'."), "model": _s("Model, e.g. 'Z315E'."),
            "serial_number": _s("Serial number or VIN."), "purchase_date": _s("ISO date YYYY-MM-DD."),
            "category": _s("Vehicle, Power Equipment, Appliance, Property, Garden/Plant, Tool or Other."),
            "new_name": _s("A new name, if the user is renaming it."),
        }, ["asset_name"]),
        handler=_action_update_maintenance_asset,
        trigger_phrases=("serial number", "is a john deere", "model number", "vin is", "bought it in", "rename my"),
    ))
    registry.register(AssistantAction(
        name="get_maintenance_asset", domain="maintenance",
        description="Tell the user everything MIA knows about one tracked vehicle, tool, appliance or plant: details, maintenance status, latest readings and notes.",
        parameters=_obj({"asset_name": _s("The item as the user referred to it.")}, ["asset_name"]),
        handler=_action_get_maintenance_asset,
        trigger_phrases=("tell me about my", "what do you know about", "details on my"),
    ))
    registry.register(AssistantAction(
        name="add_asset_note", domain="maintenance",
        description="Record an observation about a tracked item or plant (e.g. 'deck belt is fraying', 'peppers are flowering'). Saved with today's date.",
        parameters=_obj({"asset_name": _s("The item or plant."), "note": _s("The observation, in plain words.")}, ["asset_name", "note"]),
        handler=_action_add_asset_note,
        trigger_phrases=("make a note on", "is fraying", "are flowering", "is leaking"),
    ))
    # Deliberately specific: generic words ("plant", "equipment") would
    # pull tools into ordinary conversation, and a too-broad gate has
    # already caused a live-model hallucination here once (see the
    # log_maintenance_reading comment in core/application.py). The user's
    # own asset names (entity matching below) cover "the mower", "the
    # tomatoes", etc.
    registry.register_domain_keywords("maintenance", (
        "maintenance", "oil change", "changed the oil", "mileage", "odometer", "miles on", "hours on",
        "engine hours", "serviced", "tune-up", "greenhouse", "watered", "fertilized", "pruned",
        "raised bed",
    ))
    registry.register_entity_names("maintenance", lambda ctx: [a.name for a in ctx.maintenance.all_assets()] if ctx.maintenance else [])

    # -- debts --------------------------------------------------------------
    registry.register(AssistantAction(
        name="add_debt", domain="debts",
        description="Start tracking a credit card, loan or other debt (not a mortgage, which lives with Real Estate). Needs a name and balance; interest rate and minimum payment help rank payoff.",
        parameters=_obj({
            "name": _s("e.g. 'Chase Freedom', 'Truck Loan'."), "balance": _n("Current balance owed."),
            "interest_rate": _n("Standard APR percent, e.g. 24.99."), "minimum_payment": _n("Monthly minimum."),
            "debt_type": _s("Credit Card, Personal Loan, Auto Loan, Student Loan, Medical Debt or Other."),
            "promo_apr": _n("Promotional APR percent, if any."), "promo_expires_date": _s("Promo end date YYYY-MM-DD."),
        }, ["name", "balance"]),
        handler=_action_add_debt,
        trigger_phrases=("i owe", "add a debt", "track a debt", "add my loan", "add my credit card", "new debt"),
    ))
    registry.register(AssistantAction(
        name="update_debt", domain="debts",
        description="Change a tracked debt's balance, interest rate, minimum payment, or promo rate/end date.",
        parameters=_obj({
            "debt_name": _s("The debt as the user referred to it."), "balance": _n("New balance."),
            "interest_rate": _n("New APR percent."), "minimum_payment": _n("New monthly minimum."),
            "promo_apr": _n("Promo APR percent."), "promo_expires_date": _s("Promo end date YYYY-MM-DD."),
        }, ["debt_name"]),
        handler=_action_update_debt,
        trigger_phrases=("balance is now", "rate went up", "rate is now", "minimum payment is"),
    ))
    registry.register(AssistantAction(
        name="list_debts", domain="debts",
        description="Summarize every open debt: balances, current interest rates, total owed and monthly minimums.",
        parameters=_NO_PARAMS, handler=_action_list_debts,
        trigger_phrases=("list my debts", "how much debt", "how much do i owe", "what do i owe", "my debts"),
    ))
    registry.register(AssistantAction(
        name="record_debt_payment", domain="debts",
        description="Record a payment the user made toward a tracked debt; reduces its balance and logs the expense.",
        parameters=_obj({
            "debt_name": _s("The debt as the user referred to it."), "amount": _n("Amount paid."),
            "date": _s("YYYY-MM-DD if not today."),
        }, ["debt_name", "amount"]),
        handler=_action_record_debt_payment,
        trigger_phrases=("paid toward", "toward my", "toward the", "payment on my", "loan payment", "card payment", "paid down", "paid off"),
    ))
    registry.register(AssistantAction(
        name="get_debt_payoff_plan", domain="debts",
        description="Rank debts in the order to pay them off and explain why (interest rates, expiring promo rates). Strategy: hybrid (default), avalanche or snowball.",
        parameters=_obj({"strategy": _s("hybrid, avalanche or snowball.")}, []),
        handler=_action_get_debt_payoff_plan,
        trigger_phrases=("pay off first", "payoff plan", "pay off plan", "which debt", "debt strategy", "snowball", "avalanche"),
    ))
    registry.register_domain_keywords("debts", ("debt", "debts", "loan", "loans", "credit card", "apr", "payoff", "owe", "interest rate"))
    registry.register_entity_names(
        "debts", lambda ctx: [d.name for d in ctx.budget.all_debts()] if ctx.budget else [], match_all_words=True,
    )

    # -- budget targets -----------------------------------------------------
    registry.register(AssistantAction(
        name="set_budget_target", domain="budget",
        description="Set the monthly budget for one spending category (e.g. Groceries $600).",
        parameters=_obj({
            "category": _s("Spending category, e.g. Groceries, Utilities, Transportation."),
            "monthly_amount": _n("Planned monthly amount."),
        }, ["category", "monthly_amount"]),
        handler=_action_set_budget_target,
        trigger_phrases=("budget to", "set my budget", "budget for", "monthly budget"),
    ))
    # Not "budget"/"paycheck"/"spent": "what's a good way to budget my paycheck?" is advice, not a record.
    registry.register_domain_keywords("budget", ("bill", "bills", "expense", "expenses"))

    # -- kitchen: recipes & meals ------------------------------------------
    registry.register(AssistantAction(
        name="add_recipe", domain="kitchen",
        description="Save a new recipe. Ingredients are optional, as a list like '2 lb ground venison'.",
        parameters=_obj({
            "name": _s("Recipe name."), "category": _s("Breakfast, Lunch, Dinner, Dessert, Snack, Side, Drink or Other."),
            "servings": _n("Number of servings."), "ingredients": _list("Ingredient lines, e.g. '2 cups flour'."),
            "instructions": _s("Steps, if the user gave them."),
        }, ["name"]),
        handler=_action_add_recipe,
        trigger_phrases=("add a recipe", "save a recipe", "new recipe", "recipe for"),
    ))
    registry.register(AssistantAction(
        name="list_recipes", domain="kitchen", description="List saved recipes, optionally filtered by name or category.",
        parameters=_obj({"query": _s("Optional word to filter by.")}, []), handler=_action_list_recipes,
        trigger_phrases=("what recipes", "list my recipes", "show my recipes", "my recipes"),
    ))
    registry.register(AssistantAction(
        name="suggest_recipes", domain="kitchen",
        description="Suggest recipes the user can make from what's in the pantry, and ones that need only an item or two.",
        parameters=_NO_PARAMS, handler=_action_suggest_recipes,
        trigger_phrases=("what can i make", "what can i cook", "what should i make", "what should i cook", "for dinner tonight", "cook tonight"),
    ))
    registry.register(AssistantAction(
        name="log_meal", domain="kitchen", description="Record that the user made/ate a saved recipe.",
        parameters=_obj({"recipe_name": _s("The recipe as the user referred to it."), "date": _s("YYYY-MM-DD if not today."),
                         "notes": _s("Optional notes.")}, ["recipe_name"]),
        handler=_action_log_meal,
        trigger_phrases=("i made the", "we made the", "i cooked", "we cooked", "we had the", "we ate"),
    ))
    registry.register_domain_keywords("kitchen", ("recipe", "recipes"))
    registry.register_entity_names("kitchen", lambda ctx: [r.name for r in ctx.kitchen.all_recipes()] if ctx.kitchen else [])

    # -- groceries & pantry -------------------------------------------------
    registry.register(AssistantAction(
        name="add_grocery_item", domain="groceries",
        description="Add one or more items to the grocery/shopping list.",
        parameters=_obj({"items": _list("Items, e.g. ['eggs', '2 gallons milk'].")}, ["items"]),
        handler=_action_add_grocery_item,
        trigger_phrases=("grocery list", "shopping list", "need to buy", "pick up some"),
    ))
    registry.register(AssistantAction(
        name="list_grocery_list", domain="groceries", description="Read back what's still on the grocery list.",
        parameters=_NO_PARAMS, handler=_action_list_grocery_list,
        trigger_phrases=("on my grocery list", "on the grocery list", "on my shopping list", "what do i need to buy"),
    ))
    registry.register(AssistantAction(
        name="check_off_grocery_item", domain="groceries",
        description="Check items off the grocery list once the user has bought them.",
        parameters=_obj({"items": _list("Items bought.")}, ["items"]),
        handler=_action_check_off_grocery_item,
        trigger_phrases=("check off", "i bought the", "cross off"),
    ))
    registry.register(AssistantAction(
        name="add_recipe_ingredients_to_grocery_list", domain="groceries",
        description="Add whatever a saved recipe needs that isn't in the pantry to the grocery list.",
        parameters=_obj({"recipe_name": _s("The recipe.")}, ["recipe_name"]),
        handler=_action_add_recipe_ingredients_to_grocery_list,
        trigger_phrases=("what i need for", "ingredients for", "everything for the"),
    ))
    registry.register(AssistantAction(
        name="add_pantry_item", domain="groceries",
        description="Record something the user has in the pantry/fridge and how much (updates the amount if it's already listed).",
        parameters=_obj({"name": _s("Item, e.g. 'flour'."), "quantity": _n("Amount on hand."), "unit": _s("e.g. lb, cans."),
                         "category": _s("Produce, Dairy, Meat, Frozen, Pantry/Dry Goods, Spices, Condiments, Beverages or Other.")}, ["name"]),
        handler=_action_add_pantry_item,
        trigger_phrases=("in the pantry", "in the fridge", "in the freezer", "to the pantry"),
    ))
    registry.register(AssistantAction(
        name="update_pantry_item", domain="groceries",
        description="Change how much of a pantry item is left. Use quantity 0 when the user is out of it.",
        parameters=_obj({"name": _s("Pantry item."), "quantity": _n("Amount left (0 if out)."), "unit": _s("Optional unit.")}, ["name", "quantity"]),
        handler=_action_update_pantry_item,
        trigger_phrases=("out of", "ran out", "running low", "used up the", "only have"),
    ))
    registry.register(AssistantAction(
        name="list_pantry", domain="groceries", description="Read back what's in the pantry and what's run out.",
        parameters=_NO_PARAMS, handler=_action_list_pantry,
        trigger_phrases=("in the pantry", "what's in the pantry", "what food do i have", "pantry"),
    ))
    registry.register_domain_keywords("groceries", ("grocery list", "shopping list", "pantry", "fridge", "freezer"))
    registry.register_entity_names("groceries", lambda ctx: (
        [p.name for p in ctx.kitchen.all_pantry_items()] + [g.name for g in ctx.kitchen.all_grocery_items() if not g.checked]
    ) if ctx.kitchen else [])

    # -- parts, materials, products -----------------------------------------
    registry.register(AssistantAction(
        name="adjust_component_quantity", domain="components",
        description="Change how many of an electronics part the user has: negative when they used some, positive when they got more.",
        parameters=_obj({"name": _s("The part, e.g. '10k resistor'."), "delta": _n("Change in count, e.g. -2 or 20.")}, ["name", "delta"]),
        handler=_action_adjust_component_quantity,
        trigger_phrases=("resistors", "capacitors", "transistors"),
    ))
    registry.register_domain_keywords("components", (
        "part", "parts", "component", "components", "resistor", "resistors", "capacitor", "capacitors",
        "transistor", "transistors", "diode", "diodes", "led", "leds", "555", "timers", "microcontroller", "arduino",
    ))
    registry.register_entity_names("components", lambda ctx: [_component_label(c) for c in ctx.components.all_components()] if ctx.components else [])

    registry.register(AssistantAction(
        name="adjust_material_quantity", domain="materials",
        description="Change how much of a fabrication material is on hand: negative when used, positive when bought.",
        parameters=_obj({"name": _s("The material, e.g. 'plywood'."), "delta": _n("Change, e.g. 4 or -1.5.")}, ["name", "delta"]),
        handler=_action_adjust_material_quantity,
        trigger_phrases=("more sheets", "sheets of"),
    ))
    registry.register(AssistantAction(
        name="update_material", domain="materials",
        description="Update a material's details: cost per unit, unit, supplier, storage location, amount on hand, or reorder level.",
        parameters=_obj({
            "name": _s("The material."), "unit_cost": _n("Cost per unit."), "unit": _s("e.g. sheet, ft, kg."),
            "supplier": _s("Where it's bought."), "location": _s("Where it's stored."),
            "quantity_on_hand": _n("Exact amount on hand now."), "reorder_threshold": _n("Reorder when at or below this."),
        }, ["name"]),
        handler=_action_update_material,
        trigger_phrases=("a sheet now", "price of", "reorder"),
    ))
    registry.register_domain_keywords("materials", (
        "materials", "plywood", "lumber", "2x4", "2x4s", "board feet", "filament", "acrylic", "sheet goods",
    ))
    registry.register_entity_names("materials", lambda ctx: [m.name for m in ctx.materials.all_materials()] if ctx.materials else [])

    registry.register(AssistantAction(
        name="adjust_product_stock", domain="products",
        description="Change how many of a finished product are in stock: positive when the user made more, negative for giveaways/losses. Use record_sale for sales.",
        parameters=_obj({"name": _s("The product."), "delta": _n("Change in stock, e.g. 5 or -1.")}, ["name", "delta"]),
        handler=_action_adjust_product_stock,
        trigger_phrases=("made more", "in stock", "more cutting boards"),
    ))
    registry.register_domain_keywords("products", ("product", "products", "in stock"))
    registry.register_entity_names("products", lambda ctx: [p.name for p in ctx.products.all_products()] if ctx.products else [])
