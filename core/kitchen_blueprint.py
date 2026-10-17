"""
core.kitchen_blueprint
========================

Kitchen recipes as blueprints (DEC-0028 #9, the kitchen half; Zac,
2026-10-17), the same way Workshop recipes work (core/craft_recipes.py):
the recipe is the blueprint, the pantry is the materials.

- `check()` reads each ingredient against the pantry for one batch or
  more: how much you need, how much you have, and whether you're short.
  Amounts are only compared when the units match (same rule as
  kitchen_manager.recipe_missing_ingredients); otherwise having it at all
  counts, and nothing is subtracted.
- `use_up()` is cooking it: the matched pantry items go down by what
  the batches used. Anything that runs out goes on the grocery list.
  The kitchen writes through atomic_write_text, so it can be undone.
"""

from __future__ import annotations

from typing import Optional


def _num(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def check(recipe, pantry: list, batches: float = 1.0) -> list[dict]:
    """Pure logic. One row per ingredient: need (for these batches), have
    (in the same unit; None when the pantry has it in another unit or
    without an amount), the pantry items it draws on, and its state:
    "have", "short" or "missing"."""
    from core.kitchen_manager import ingredient_key

    by_key: dict[str, list] = {}
    for item in pantry:
        by_key.setdefault(ingredient_key(item.name), []).append(item)
    rows = []
    for ingredient in recipe.ingredients:
        name = str(ingredient.get("name", "")).strip()
        if not name:
            continue
        unit = str(ingredient.get("unit", "")).strip()
        need = round(_num(ingredient.get("quantity")) * batches, 3)
        matches = by_key.get(ingredient_key(name), [])
        same = [m for m in matches if m.unit.strip().lower() == unit.lower()] if unit or need else []
        have: Optional[float] = round(sum(_num(m.quantity) for m in same), 3) if same else None
        if not matches:
            state = "missing"
        elif same and need and have < need:
            state = "short"
        else:
            state = "have"
        rows.append({"name": name, "unit": unit, "need": need, "have": have, "state": state,
                     "draw": [m.item_id for m in same] if need else []})
    return rows


def _amount(x: float, unit: str) -> str:
    return f"{x:g} {unit}".strip()


def plan(recipe, pantry: list, batches: float = 1.0) -> dict:
    """Pure logic. What cooking these batches takes out of the pantry:
    [(item_id, take)] in order, the lines to say, what runs out, and
    what's short or missing (cooked anyway: the person says they made it)."""
    by_id = {p.item_id: p for p in pantry}
    takes, said, runs_out = [], [], []
    for row in check(recipe, pantry, batches):
        if not row["draw"] or not row["need"]:
            continue
        left = row["need"]
        taken = 0.0
        for item_id in row["draw"]:
            item = by_id[item_id]
            take = min(left, _num(item.quantity))
            if take <= 0:
                continue
            takes.append((item_id, round(take, 3)))
            taken += take
            left = round(left - take, 3)
            if _num(item.quantity) - take <= 1e-9:
                runs_out.append(item.name)
            if left <= 0:
                break
        if taken > 0:
            said.append(_amount(round(taken, 3), row["unit"]) + " " + row["name"])
    rows = check(recipe, pantry, batches)
    return {"takes": takes, "said": said, "runs_out": runs_out,
            "short": [r["name"] for r in rows if r["state"] == "short"],
            "missing": [r["name"] for r in rows if r["state"] == "missing"]}


def use_up(kitchen, recipe, batches: float = 1.0) -> dict:
    """Take what these batches used out of the pantry; what ran out goes
    on the grocery list (once). Returns plan() plus `listed`."""
    from core.kitchen_manager import ingredient_key

    pantry = kitchen.all_pantry_items()
    result = plan(recipe, pantry, batches)
    by_id = {p.item_id: p for p in pantry}
    for item_id, take in result["takes"]:
        item = by_id[item_id]
        kitchen.update_pantry_item(item_id, quantity=round(max(0.0, _num(item.quantity) - take), 3))
    listed = {ingredient_key(g.name) for g in kitchen.all_grocery_items()}
    added = []
    for name in result["runs_out"]:
        if ingredient_key(name) not in listed:
            item = next(p for p in pantry if p.name == name)
            kitchen.add_grocery_item(name=name, unit=item.unit, source_recipe_id=recipe.recipe_id)
            listed.add(ingredient_key(name))
            added.append(name)
    return {**result, "listed": added}
