"""
core.web_flock
================

The Chickens screen (DEC-0037): each flock's numbers (eggs today and this
week, the lay rate, loose eggs, feed cost per dozen), the last two weeks
of eggs, the log, and the egg cartons on hand. Put together here from
core/flock.py and homestead goods (core/goods.py), so the web only
formats. Served as /api/flock.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def _money(x) -> str:
    from core.region import money

    return money(x)


def flock_page(context, today: Optional[date] = None) -> dict:
    from core.flock import figures, week_series
    from core.flock_actions import FLOCK, USE_SAID, _entry_said
    from core.goods import freshness, lots
    from core.record_actions import record_form
    from core.units import amount_text

    today = today or date.today()
    book = getattr(context, "flock", None)
    if book is None:
        return {"available": False}
    recipes_book = getattr(context, "craft_recipes", None)
    recipes = {r.recipe_id: r for r in recipes_book.all_recipes()} if recipes_book is not None else {}
    jobs = getattr(context, "jobs", None)
    ledger = getattr(context, "ledger", None)
    on_hand = lots(jobs.all_jobs(), recipes, ledger.all_revenue() if ledger is not None else []) if jobs is not None else []

    flocks = []
    for f in book.flocks:
        fig = figures(f, book.entries, today)
        recipe = recipes.get(f.egg_recipe_id)
        cartons = [lot for lot in on_hand if recipe is not None and lot.recipe_id == recipe.recipe_id]
        unit = recipe.makes_unit if recipe is not None else ""
        cartons_left = round(sum(lot.left for lot in cartons), 4)
        log = sorted(book.entries_for(f.flock_id)[::-1], key=lambda e: e.date, reverse=True)[:25]  # newest first
        flocks.append({
            "id": f.flock_id, "name": f.name, "breed": f.breed, "hens": f.hens, "roosters": f.roosters,
            "started": f.started, "notes": f.notes,
            "figures": {**fig, "feed_per_dozen_text": _money(fig["feed_per_dozen"]) if fig["feed_per_dozen"] else "",
                        "feed_month_text": _money(fig["feed_cost_month"]) if fig["feed_cost_month"] else "",
                        "lay_rate_text": f"{round(fig['lay_rate'] * 100)}%" if fig["lay_rate"] is not None else ""},
            "series": week_series(f.flock_id, book.entries, today),
            "good": {"id": recipe.recipe_id, "name": recipe.name, "unit": unit,
                     "on_hand_text": amount_text(cartons_left, unit) if unit else f"{cartons_left:g}",
                     "on_hand": cartons_left, "price_text": _money(recipe.price) if recipe.price else "",
                     "oldest": freshness(cartons[0], today) if cartons else None,
                     "oldest_made": cartons[0].made if cartons else ""} if recipe is not None else None,
            "log": [{"id": e.entry_id, "date": e.date, "kind": e.kind, "text": _entry_said(e),
                     "note": e.note} for e in log],
            "values": {fl.name: getattr(f, fl.name) for fl in FLOCK.fields},
        })
    total = {
        "hens": sum(f["hens"] for f in flocks),
        "today": sum(f["figures"]["today"] for f in flocks),
        "week": sum(f["figures"]["week"] for f in flocks),
        "loose": sum(f["figures"]["loose"] for f in flocks),
    }
    egg_goods = [{"id": r.recipe_id, "name": r.name} for r in sorted(recipes.values(), key=lambda r: r.name.lower())]
    return {"available": True, "as_of": today.isoformat(), "flocks": flocks, "total": total,
            "forms": {"flock": record_form(FLOCK)}, "picks": {"egg_goods": egg_goods},
            "uses": [{"id": k, "label": v} for k, v in USE_SAID.items()]}
