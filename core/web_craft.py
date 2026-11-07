"""
core.web_craft
================

The Workshop's Recipes and Builds tabs (DEC-0030 phase B): put together
here from core/craft_recipes.py, Materials, Jobs, Products and the
Ledger, so the web only formats. Part of `workshop_page()`. The Goods
tab (DEC-0036: homestead goods on hand, batch by batch, the market day
and labels) is `goods_section()`. For the design canvas's Builds tab
(DEC-0113) it also gives each build its budget and next step, the best
earner per hour (`best_earner`) and the batches to sell first
(`sell_first`).
"""

from __future__ import annotations

from typing import Optional

from core.craft_recipes import build_result, check, makes_text


def _money(x) -> str:
    """An amount in the person's currency."""
    from core.region import money

    return money(x)


def _row(r: dict) -> dict:
    """One material row of a recipe, with its cost, its line ("2 boards plywood") and what's left after, as text."""
    from core.units import amount_text

    return {**r, "unit_cost_text": _money(r["unit_cost"]) if r["unit_cost"] else "",
            "line_text": f"{r['need']:g} {r['unit'] + ' ' if r['unit'] else ''}{r['name']}",
            "after_text": amount_text(r["after"], r["unit"]) if r.get("after") is not None else ""}


def craft_section(context) -> dict:
    """The Workshop's crafting part: each recipe with what it needs from the shelf and its steps, each build
    with its steps done, the step that's next, what its recipe says it should cost, photos and result (sold, cost,
    profit, per hour, after labor), the best earner per hour, the labor rate, and the receipts and forms.
    """
    from core.build_media import media
    from core.craft_actions import CRAFT_RECIPE, receive_form
    from core.record_actions import record_form

    book = getattr(context, "craft_recipes", None)
    jobs = getattr(context, "jobs", None)
    materials = getattr(context, "materials", None)
    ledger = getattr(context, "ledger", None)
    if book is None:
        return {"recipes": [], "builds": [], "forms": {}, "receipts": []}
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
        planned = check(recipe, stock, job.times)["est_material_cost"] if recipe is not None else 0.0
        card = {"id": job.job_id, "name": job.name, "recipe_id": job.recipe_id,
                # the canvas's build card (DEC-0113): what the recipe says it should cost, and the step that's next
                "budget": round(planned, 2), "budget_text": _money(planned) if planned else "",
                "next": next((s for i, s in enumerate(steps) if i not in job.steps_done), None),
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
        # A batch sells what it makes; a one-off sells one (DEC-0036).
        est_profit = round(recipe.price * recipe.makes - state["est_material_cost"], 2) if recipe.price else None
        shopping_fields = receive_form(state["shopping"])
        recipes.append({
            "id": recipe.recipe_id, "name": recipe.name, "category": recipe.category, "description": recipe.description,
            "dimensions": recipe.dimensions, "cut_list": recipe.cut_list, "tools": recipe.tools,
            "steps": recipe.step_list, "notes": recipe.notes, "est_hours": recipe.est_hours,
            "price": recipe.price, "price_text": _money(recipe.price) if recipe.price else "",
            # DEC-0036: what a batch makes, what one costs, lines whose units can't compare.
            "is_batch": bool(recipe.makes_unit) or recipe.makes != 1, "makes_text": makes_text(recipe),
            "per_piece_text": _money(state["per_piece"]) if state["per_piece"] and recipe.makes != 1 else "",
            "mismatched": state["mismatched"], "shelf_days": recipe.shelf_days,
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
                       if sold and avg("hours", sold) else "",
                       "per_hour_value": round(avg("profit", sold) / avg("hours", sold), 2)
                       if sold and avg("hours", sold) else None},
            "values": {f.name: getattr(recipe, f.name) for f in CRAFT_RECIPE.fields},
        })
    from core.receipt_match import receipts

    return {"recipes": recipes, "builds": builds, "forms": {"craft_recipe": record_form(CRAFT_RECIPE)},
            "best_earner": best_earner(recipes),
            "labor_rate": labor_rate,
            "receipts": [{"id": r["id"], "name": r["name"]} for r in receipts(context)]}


def best_earner(recipes: list) -> Optional[dict]:
    """Pure logic. The recipe that has earned the most per hour, from builds sold with their hours logged (the
    canvas's "Best Earner · Per Hour", DEC-0113): {"name", "per_hour_text"}; None until one has earned anything."""
    scored = [r for r in recipes if ((r.get("actual") or {}).get("per_hour_value") or 0) > 0]
    if not scored:
        return None
    top = max(scored, key=lambda r: r["actual"]["per_hour_value"])
    return {"name": top["name"], "per_hour_text": top["actual"]["per_hour"]}


def find_build(context, job_id: str) -> Optional[dict]:
    """One build's card by id, or None."""
    return next((b for b in craft_section(context)["builds"] if b["id"] == job_id), None)


def sell_first(goods: list, limit: int = 4) -> list[dict]:
    """Pure logic. The batches to sell before they turn (the canvas's "Sell First", DEC-0113): each lot whose
    freshness says sell first or past its sell-by, soonest first, with what's left: [{"name", "sell_by",
    "days_left", "left_text", "state"}]."""
    rows = [{"name": g["name"], "sell_by": lot["sell_by"], "days_left": lot["days_left"], "left_text": lot["left_text"],
             "state": lot["state"]}
            for g in goods for lot in g["lots"] if lot["state"] in ("sell first", "past")]
    rows.sort(key=lambda r: (r["days_left"] if r["days_left"] is not None else 10_000, r["name"].lower()))
    return rows[:limit]


def goods_section(context, today=None) -> dict:
    """The Goods tab (DEC-0036): what's made and not sold, per recipe and
    batch (freshness, sell-by), the batches to sell first, the open market
    day's tally, the last ones, how many usually sell, and each lot's
    label."""
    from datetime import date as _date

    from core.goods import demand, freshness, label, lots
    from core.goods_actions import LABEL_FORM, market_tally
    from core.units import amount_text

    today = today or _date.today()
    book = getattr(context, "craft_recipes", None)
    jobs = getattr(context, "jobs", None)
    ledger = getattr(context, "ledger", None)
    business = getattr(context, "business", None)
    if book is None or jobs is None:
        return {"goods": [], "market": None, "markets": [], "label": {}, "label_form": LABEL_FORM, "starters": []}
    recipes = {r.recipe_id: r for r in book.all_recipes()}
    sales = ledger.all_revenue() if ledger is not None else []
    settings = dict(business.label) if business is not None else {}
    on_hand = lots(jobs.all_jobs(), recipes, sales)
    markets = list(business.markets) if business is not None else []
    tallies = {m.market_id: market_tally(context, m) for m in markets}
    usual = demand(markets, tallies)

    goods = []
    for recipe in recipes.values():
        mine = [lot for lot in on_hand if lot.recipe_id == recipe.recipe_id]
        if not mine and not (recipe.makes_unit or recipe.makes != 1):
            continue  # one-off builds stay in Builds
        unit = recipe.makes_unit
        rows = []
        for lot in mine:
            fresh = freshness(lot, today)
            rows.append({"job_id": lot.job_id, "made": lot.made, "sell_by": lot.sell_by, "left": lot.left,
                         "left_text": amount_text(lot.left, unit) if unit else f"{lot.left:g}",
                         "state": fresh["state"], "days_left": fresh["days_left"],
                         "unit_cost_text": _money(lot.unit_cost) if lot.unit_cost else "",
                         "label": label(recipe, lot.made, settings)})
        total = round(sum(lot.left for lot in mine), 4)
        hint = usual.get(recipe.recipe_id)
        goods.append({
            "recipe_id": recipe.recipe_id, "name": recipe.name, "unit": unit, "price": recipe.price,
            "price_text": _money(recipe.price) if recipe.price else "",
            "on_hand": total, "on_hand_text": amount_text(total, unit) if unit else f"{total:g}",
            "lots": rows, "sell_first": sum(1 for r in rows if r["state"] in ("sell first", "past")),
            "usual": {**hint, "text": f"usually sells {hint['avg_sold']:g} a market"
                      + (f", sold out {hint['sold_out']} of {hint['markets']}" if hint["sold_out"] else "")
                      + f"; bring {hint['bring']}"} if hint else None,
            "label": label(recipe, today.isoformat(), settings),
        })
    goods.sort(key=lambda g: (-g["sell_first"], -g["on_hand"], g["name"].lower()))

    def card(m) -> dict:
        t = tallies[m.market_id]
        return {"id": m.market_id, "place": m.place, "date": m.date, "status": m.status,
                "rows": [{**r, "revenue_text": _money(r["revenue"])} for r in t["rows"]],
                "revenue_text": _money(t["revenue"]), "cost_text": _money(t["cost"]),
                "profit_text": _money(t["profit"]), "profit": t["profit"], "sold": t["sold"]}

    open_day = business.open_market() if business is not None else None
    closed = [m for m in markets if m.status == "closed"]
    closed.sort(key=lambda m: (m.date, m.created_at), reverse=True)
    from core.goods_starters import starter_list

    return {"goods": goods, "sell_first": sell_first(goods),
            "market": card(open_day) if open_day is not None else None,
            "markets": [card(m) for m in closed[:8]], "label": settings, "label_form": LABEL_FORM,
            "starters": starter_list()}
