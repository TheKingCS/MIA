"""
core.meal_plan
================

The week's meals (DEC-0020, docs/KITCHEN_FITNESS_PLAN.md phase 3): what's
planned each day, the prep sessions that cook ahead, the nutrition the
plan adds up to against the person's targets, a shopping list for the
whole week, and a suggested week from the person's own recipes. The plan
is the person's (core/fitness_manager.py); recipes, pantry and the
grocery list are the household's Kitchen (core/kitchen_manager.py).

Shopping list: every planned meal's recipe, scaled from the recipe's
servings to the servings planned (a prep session cooks its servings
once), lines with the same ingredient and unit added together, minus
what the pantry has in that unit, minus what's already on the grocery
list; anything matching an allergy is flagged, never dropped silently.

Suggesting a week: no model. From the person's unlocked recipes that
avoid their dislikes and allergies, lunches follow their lunch rotation
if they set one, and each day's dinner is picked to bring the day's
protein closest to the target without going far over the calories.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core.fitness_manager import MEALS, add_up


def week_of(day: date) -> list[date]:
    start = day - timedelta(days=day.weekday())
    return [start + timedelta(days=i) for i in range(7)]


def _recipe(context, recipe_id: str):
    kitchen = getattr(context, "kitchen", None)
    return kitchen.get_recipe(recipe_id) if kitchen is not None and recipe_id else None


def _facts(context, recipe_id: str, servings: float) -> dict:
    from core.nutrition import recipe_facts, scaled

    recipe = _recipe(context, recipe_id)
    return scaled(recipe_facts(recipe), servings) if recipe is not None else {}


def day_plan(context, day: date) -> dict:
    """One day: its planned meals (recipe, servings, nutrition, eaten?),
    the planned totals, and the targets beside them."""
    fit = context.fitness
    key = day.isoformat()
    eaten = fit.eaten_planned(key)
    meals = []
    for meal, slot in sorted(fit.planned(key).items(), key=lambda m: MEALS.index(m[0])):
        recipe = _recipe(context, slot["recipe_id"])
        facts = _facts(context, slot["recipe_id"], slot.get("servings", 1))
        meals.append({"meal": meal, "recipe_id": slot["recipe_id"], "name": recipe.name if recipe else "(a removed recipe)",
                      "servings": slot.get("servings", 1), "prep_id": slot.get("prep_id", ""), "eaten": meal in eaten,
                      **{k: facts.get(k) for k in ("kcal", "protein_g", "carbs_g", "fat_g")}})
    targets = fit.plan["targets"]
    return {"date": key, "meals": meals, "totals": add_up(meals),
            "targets": {"kcal": targets.get("calories"), "protein_g": targets.get("protein_g")}}


def week_plan(context, day: date) -> dict:
    fit = context.fitness
    days = [day_plan(context, d) for d in week_of(day)]
    first, last = days[0]["date"], days[-1]["date"]
    preps = []
    for session in fit.prep_sessions(first, last):
        recipe = _recipe(context, session["recipe_id"])
        preps.append({**session, "name": recipe.name if recipe else "(a removed recipe)"})
    planned = sum(len(d["meals"]) for d in days)
    eaten = sum(1 for d in days for m in d["meals"] if m["eaten"])
    return {"week_of": first, "days": days, "prep": preps, "planned": planned, "eaten": eaten}


# ------------------------------------------------------------------ shopping


def _key(name: str) -> str:
    from core.kitchen_manager import ingredient_key

    return ingredient_key(name)


def _allergic(name: str, allergies: list) -> bool:
    words = set(_key(name).split())
    return any(set(_key(a).split()) <= words or _key(a) in _key(name) for a in allergies if a.strip())


def shopping_list(context, day: date) -> dict:
    """What the week's plan needs that the house doesn't have:
    [{name, quantity, unit, recipes, allergy}] and what was already covered."""
    fit, kitchen = context.fitness, getattr(context, "kitchen", None)
    if kitchen is None:
        return {"items": [], "in_pantry": [], "on_list": []}
    week = week_of(day)
    servings: dict[str, float] = {}
    cooked_by_prep = {p["id"] for p in fit.prep_sessions(week[0].isoformat(), week[-1].isoformat())}
    for d in week:
        for slot in fit.planned(d.isoformat()).values():
            if slot.get("prep_id") in cooked_by_prep:
                continue  # its prep session buys for it
            servings[slot["recipe_id"]] = servings.get(slot["recipe_id"], 0) + float(slot.get("servings") or 1)
    for session in fit.prep_sessions(week[0].isoformat(), week[-1].isoformat()):
        servings[session["recipe_id"]] = servings.get(session["recipe_id"], 0) + float(session["servings"])
    need: dict[tuple, dict] = {}
    for recipe_id, count in servings.items():
        recipe = kitchen.get_recipe(recipe_id)
        if recipe is None:
            continue
        scale = count / max(1, recipe.servings or 1)
        for ingredient in recipe.ingredients or []:
            name = str(ingredient.get("name", "")).strip()
            if not name:
                continue
            unit = str(ingredient.get("unit", "")).strip().lower()
            line = need.setdefault((_key(name), unit), {"name": name, "quantity": 0.0, "unit": unit, "recipes": []})
            line["quantity"] += float(ingredient.get("quantity") or 0) * scale
            if recipe.name not in line["recipes"]:
                line["recipes"].append(recipe.name)
    pantry = {(_key(p.name), (p.unit or "").lower()): p.quantity for p in kitchen.all_pantry_items()}
    pantry_names = {_key(p.name) for p in kitchen.all_pantry_items() if (p.quantity or 0) > 0}
    on_list = {_key(g.name) for g in kitchen.all_grocery_items() if not g.checked}
    allergies = fit.plan["meals"]["preferences"].get("allergies") or []
    items, in_pantry, listed = [], [], []
    for (key, unit), line in sorted(need.items(), key=lambda kv: kv[1]["name"].lower()):
        have = pantry.get((key, unit))
        if have is not None and line["quantity"] and have >= line["quantity"]:
            in_pantry.append(line["name"])
            continue
        if key in on_list:
            listed.append(line["name"])
            continue
        quantity = line["quantity"] - (have or 0) if have is not None else line["quantity"]
        items.append({**line, "quantity": round(max(quantity, 0), 2), "allergy": _allergic(line["name"], allergies),
                      "have_some": have is None and key in pantry_names})
    return {"items": items, "in_pantry": in_pantry, "on_list": listed}


# ------------------------------------------------------------------ suggesting a week


def _avoid(recipe, preferences: dict) -> bool:
    bad = [w for w in (preferences.get("dislikes") or []) + (preferences.get("allergies") or []) if w.strip()]
    text = " ".join([recipe.name] + [str(i.get("name", "")) for i in recipe.ingredients or []]).lower()
    return any(re.search(r"\b" + re.escape(_key(w)), _key(text)) for w in bad)


def suggest_week(context, day: date, meals: tuple = ("lunch", "dinner")) -> list[dict]:
    """A suggested plan for the week's empty slots: [{date, meal, recipe_id, name, servings}]."""
    fit, kitchen = context.fitness, getattr(context, "kitchen", None)
    if kitchen is None:
        return []
    plan = fit.plan
    preferences = plan["meals"]["preferences"]
    usable = [r for r in kitchen.all_recipes() if not getattr(r, "locked", False) and not _avoid(r, preferences)]
    if not usable:
        return []
    from core.nutrition import recipe_facts

    facts = {r.recipe_id: recipe_facts(r) for r in usable}
    by_category = {c: [r for r in usable if r.category == c] for c in ("Breakfast", "Lunch", "Dinner")}
    rotation = [r for r in plan["meals"].get("lunch_rotation") or [] if r in facts]
    protein_target = plan["targets"].get("protein_g") or 0
    calorie_target = plan["targets"].get("calories") or 0
    out, used = [], {}
    for index, d in enumerate(week_of(day)):
        key = d.isoformat()
        planned = fit.planned(key)
        day_protein = sum((facts.get(s["recipe_id"], {}).get("protein_g") or 0) * s.get("servings", 1) for s in planned.values())
        day_kcal = sum((facts.get(s["recipe_id"], {}).get("kcal") or 0) * s.get("servings", 1) for s in planned.values())
        for meal in meals:
            if meal in planned:
                continue
            pool = by_category.get(meal.capitalize()) or usable
            if meal == "lunch" and rotation:
                choice = next(r for r in usable if r.recipe_id == rotation[index % len(rotation)])
            else:
                def fit_score(r):
                    f = facts[r.recipe_id]
                    protein_gap = abs(protein_target - day_protein - (f.get("protein_g") or 0)) if protein_target else 0
                    over = max(0, day_kcal + (f.get("kcal") or 0) - calorie_target) if calorie_target else 0
                    return protein_gap + over / 20 + 15 * used.get(r.recipe_id, 0)  # variety: repeats cost
                choice = min(pool, key=fit_score)
            used[choice.recipe_id] = used.get(choice.recipe_id, 0) + 1
            f = facts[choice.recipe_id]
            day_protein += f.get("protein_g") or 0
            day_kcal += f.get("kcal") or 0
            out.append({"date": key, "meal": meal, "recipe_id": choice.recipe_id, "name": choice.name, "servings": 1})
    return out
