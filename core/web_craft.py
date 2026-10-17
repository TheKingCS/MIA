"""
core.web_craft
================

The Workshop's Recipes and Builds tabs (DEC-0030 phase B): put together
here from core/craft_recipes.py, Materials, Jobs, Products and the
Ledger, so the web only formats. Part of `workshop_page()`.
"""

from __future__ import annotations

from typing import Optional

from core.craft_recipes import build_result, check


def _money(x) -> str:
    from core.region import money

    return money(x)


def _row(r: dict) -> dict:
    return {**r, "unit_cost_text": _money(r["unit_cost"]) if r["unit_cost"] else "",
            "line_text": f"{r['need']:g} {r['unit'] + ' ' if r['unit'] else ''}{r['name']}"}


def craft_section(context) -> dict:
    from core.build_media import media
    from core.craft_actions import CRAFT_RECIPE, receive_form
    from core.record_actions import record_form

    book = getattr(context, "craft_recipes", None)
    jobs = getattr(context, "jobs", None)
    materials = getattr(context, "materials", None)
    ledger = getattr(context, "ledger", None)
    if book is None:
        return {"recipes": [], "builds": [], "forms": {}}
    stock = materials.all_materials() if materials is not None else []
    sales = ledger.all_revenue() if ledger is not None else []
    expenses = ledger.all_expenses() if ledger is not None else []
    all_jobs = jobs.all_jobs() if jobs is not None else []
    labor_rate = float(context.config.get("workshop.labor_rate_per_hour", 0) or 0) if getattr(context, "config", None) else 0.0

    builds, by_recipe = [], {}
    for job in all_jobs:
        if not job.recipe_id:
            continue
        recipe = book.get_recipe(job.recipe_id)
        steps = recipe.step_list if recipe is not None else []
        result = build_result(job, sales, expenses)
        done = job.status == "Complete"
        try:
            photos = media(context, job.job_id)
        except (OSError, ValueError):
            photos = []
        card = {"id": job.job_id, "name": job.name, "recipe_id": job.recipe_id,
                "recipe": recipe.name if recipe is not None else "(recipe deleted)", "times": job.times,
                "status": job.status, "finished": done, "started": (job.created_at or "")[:10],
                "steps": [{"index": i, "text": s, "done": i in job.steps_done} for i, s in enumerate(steps)],
                "steps_done": sum(1 for i in range(len(steps)) if i in job.steps_done),
                "hours": job.labor_hours, "photos": photos,
                "result": {**result, "sold_text": _money(result["sold"]), "cost_text": _money(result["cost"]),
                           "materials_text": _money(result["materials"]), "other_text": _money(result["other"]),
                           "profit_text": _money(result["profit"]),
                           "per_hour_text": _money(result["per_hour"]) + "/h" if result["per_hour"] is not None else "",
                           "after_labor_text": _money(result["profit"] - result["hours"] * labor_rate)
                           if labor_rate and result["hours"] and result["is_sold"] else ""},
                "in_stock": done and not result["is_sold"]}
        builds.append(card)
        by_recipe.setdefault(job.recipe_id, []).append(card)

    recipes = []
    for recipe in book.all_recipes():
        state = check(recipe, stock, 1)
        history = [b for b in by_recipe.get(recipe.recipe_id, []) if b["finished"]]
        sold = [b for b in history if b["result"]["is_sold"]]
        avg = (lambda key, rows: round(sum(b["result"][key] for b in rows) / len(rows), 2) if rows else None)
        est_profit = round(recipe.price - state["est_material_cost"], 2) if recipe.price else None
        shopping_fields = receive_form(state["shopping"])
        recipes.append({
            "id": recipe.recipe_id, "name": recipe.name, "category": recipe.category, "description": recipe.description,
            "dimensions": recipe.dimensions, "cut_list": recipe.cut_list, "tools": recipe.tools,
            "steps": recipe.step_list, "notes": recipe.notes, "est_hours": recipe.est_hours,
            "price": recipe.price, "price_text": _money(recipe.price) if recipe.price else "",
            "rows": [_row(r) for r in state["rows"]], "ready": state["ready"] and bool(state["rows"]),
            "short": len(state["shopping"]), "unpriced": state["unpriced"],
            "est_cost_text": _money(state["est_material_cost"]),
            "shopping_text": _money(state["shopping_cost"]) if state["shopping_cost"] else "",
            "shopping": [_row(r) for r in state["shopping"]],
            "shopping_list": "\n".join(f"{r['short']:g} {r['unit'] + ' ' if r['unit'] else ''}{r['name']}"
                                       + (f" (~{_money(r['short'] * r['unit_cost'])})" if r["unit_cost"] else "")
                                       for r in state["shopping"]),
            "receive_fields": shopping_fields,
            "est_profit_text": _money(est_profit) if est_profit is not None else "",
            "est_profit": est_profit,
            "built": len(history), "sold": len(sold),
            "actual": {"cost": _money(avg("cost", history)) if history else "",
                       "profit": _money(avg("profit", sold)) if sold else "",
                       "hours": avg("hours", history) if history else None,
                       "per_hour": _money(avg("profit", sold) / avg("hours", sold)) + "/h"
                       if sold and avg("hours", sold) else ""},
            "values": {f.name: getattr(recipe, f.name) for f in CRAFT_RECIPE.fields},
        })
    return {"recipes": recipes, "builds": builds, "forms": {"craft_recipe": record_form(CRAFT_RECIPE)},
            "labor_rate": labor_rate}


def find_build(context, job_id: str) -> Optional[dict]:
    return next((b for b in craft_section(context)["builds"] if b["id"] == job_id), None)
