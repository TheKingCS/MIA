"""
core.nutrition
================

A recipe's nutrition facts per serving (DEC-0020): what the person typed
into the recipe wins, nutrient by nutrient; the rest is worked out from
its ingredients with MIA's built-in food table (core/food_table.py).
Each answer says where it came from, so a screen can show "from your
recipe" or "worked out from the ingredients" and what couldn't be found.
"""

from __future__ import annotations

from core import food_table

TYPED = {"kcal": "calories_per_serving", "protein_g": "protein_g", "carbs_g": "carbs_g", "fat_g": "fat_g"}


def recipe_facts(recipe) -> dict:
    """Per serving: {kcal, protein_g, ...}, `source` ("typed" / "computed"
    / "mixed" / "unknown") and the ingredients MIA couldn't match."""
    typed = {n: getattr(recipe, attr, None) for n, attr in TYPED.items()}
    computed = food_table.recipe_nutrition(getattr(recipe, "ingredients", []) or [], getattr(recipe, "servings", 1) or 1)
    usable = bool(computed["matched"])
    facts = {}
    for n in food_table.NUTRIENTS:
        if typed.get(n) is not None:
            facts[n] = float(typed[n])
        elif usable and computed["complete"]:
            facts[n] = computed["per_serving"].get(n)
        else:
            facts[n] = None  # a partial sum would undercount: say it's unknown instead
    has_typed = any(v is not None for v in typed.values())
    has_computed = usable and computed["complete"] and any(typed.get(n) is None for n in TYPED)
    source = "mixed" if has_typed and has_computed else "typed" if has_typed else "computed" if has_computed else "unknown"
    return {**facts, "source": source, "missing": computed["missing"], "matched": computed["matched"]}


def scaled(facts: dict, servings: float) -> dict:
    """Pure logic. Facts for `servings` servings (unknowns stay unknown)."""
    return {n: (round(facts[n] * servings, 1) if facts.get(n) is not None else None) for n in food_table.NUTRIENTS}
