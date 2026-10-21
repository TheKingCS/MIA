"""
core.goods_actions
====================

Homestead goods' actions (DEC-0036), on the action contract in
core/actions.py: proposed in plain words, approved, run, undoable.

- `goods.sell`: sold some of a recipe's goods, taken from the oldest
  batches first (core/goods.py's fifo); during an open market day the
  sale is that day's.
- `goods.toss`: some of a batch went bad or was given away: out of
  stock, counted as a loss on the batch.
- `market.start`: a day at the stand or the market, with how many of
  each you're taking (`b_<recipe_id>`).
- `market.close`: the day's tally (sold, left, money, what it cost),
  leftovers you're tossing (`t_<recipe_id>`), and XP for the day.
- `goods.label`: what every label says about the business: its name,
  address and the statement the person's own rules require (MIA prints
  what they enter; it never says what the law is).
"""

from __future__ import annotations

from datetime import date

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.units import amount_text


def _money(x: float) -> str:
    from core.region import money

    return money(x)


def _number(params, name: str, label: str) -> float:
    raw = params.get(name)
    if raw in (None, ""):
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ActionError(f"{label} has to be a number.") from None
    if value < 0:
        raise ActionError(f"{label} can't be negative.")
    return value


def _recipe(context, recipe_id: str):
    recipe = _need(context, "craft_recipes").get_recipe(str(recipe_id or ""))
    if recipe is None:
        raise ActionError("That recipe isn't there anymore.")
    return recipe


def _lots(context, recipe_id: str = "") -> list:
    from core.goods import lots

    book = _need(context, "craft_recipes")
    recipes = {r.recipe_id: r for r in book.all_recipes()}
    jobs = context.jobs.all_jobs() if getattr(context, "jobs", None) is not None else []
    ledger = getattr(context, "ledger", None)
    found = lots(jobs, recipes, ledger.all_revenue() if ledger is not None else [])
    return [lot for lot in found if not recipe_id or lot.recipe_id == recipe_id]


def _units(recipe, quantity: float) -> str:
    return amount_text(quantity, recipe.makes_unit) if recipe.makes_unit else f"{quantity:g}"


# ---------------------------------------------------------------- sell


def _selling(context, params) -> tuple:
    from core.goods import fifo

    recipe = _recipe(context, params.get("recipe_id"))
    quantity = _number(params, "quantity", "How many")
    if quantity <= 0:
        raise ActionError("How many did you sell?")
    amount = _number(params, "amount", "What they sold for")
    if amount <= 0:
        amount = round(quantity * (recipe.price or 0), 2)
    if amount <= 0:
        raise ActionError(f"Put in what they sold for ({recipe.name} has no price yet).")
    taken = fifo(_lots(context, recipe.recipe_id), quantity)
    have = sum(q for _l, q in taken)
    if have < quantity:
        left = f"only {_units(recipe, have)} left" if have else "none left"
        raise ActionError(f"{recipe.name}: {left} in stock. Finish a batch first, or sell fewer.")
    business = getattr(context, "business", None)
    market = business.open_market() if business is not None else None
    return recipe, quantity, amount, taken, market


def _sell_describe(context, params) -> str:
    recipe, quantity, amount, taken, market = _selling(context, params)
    where = f" at {market.place}" if market is not None and market.place else ""
    batches = f" (from {len(taken)} batches, oldest first)" if len(taken) > 1 else ""
    return f"Sold {_units(recipe, quantity)} of {recipe.name}{where} for {_money(amount)}{batches}"


def _sell(context, params) -> str:
    from core.goods import market_tag, split_amount

    recipe, quantity, amount, taken, market = _selling(context, params)
    ledger = _need(context, "ledger")
    product_id = recipe.product_id
    note = market_tag(market.market_id) if market is not None else ""
    for (lot, q), piece in zip(taken, split_amount(amount, [q for _l, q in taken])):
        ledger.record_sale(product_id, q, piece, description=f"Sold {recipe.name}", job_id=lot.job_id, notes=note)
    return f"Sold {_units(recipe, quantity)} of {recipe.name}: {_money(amount)}."


# ---------------------------------------------------------------- toss


def _tossing(context, params) -> tuple:
    job = _need(context, "jobs").get_job(str(params.get("job_id") or ""))
    if job is None:
        raise ActionError("That batch isn't there anymore.")
    lot = next((lot for lot in _lots(context) if lot.job_id == job.job_id), None)
    if lot is None:
        raise ActionError(f"Nothing left from {job.name}.")
    quantity = _number(params, "quantity", "How many") or lot.left
    if quantity > lot.left:
        raise ActionError(f"Only {lot.left:g} left from that batch.")
    return job, lot, quantity


def _toss_describe(context, params) -> str:
    job, lot, quantity = _tossing(context, params)
    loss = quantity * lot.unit_cost
    return f"Toss {quantity:g} of {lot.name} (made {lot.made})" + (f": a {_money(loss)} loss" if loss else "")


def _toss(context, params) -> str:
    job, lot, quantity = _tossing(context, params)
    context.jobs.update_job(job.job_id, tossed=round(float(job.tossed or 0) + quantity, 4))
    product_id = next((p.product_id for p in job.products_produced), "")
    products = getattr(context, "products", None)
    if product_id and products is not None and products.get_product(product_id) is not None:
        products.adjust_stock(product_id, -quantity)
    return f"Tossed {quantity:g} of {lot.name}."


# ---------------------------------------------------------------- market days


def _brought(context, params) -> dict:
    book = _need(context, "craft_recipes")
    out = {}
    for name, raw in params.items():
        if not name.startswith("b_") or raw in (None, ""):
            continue
        recipe = book.get_recipe(name[2:])
        if recipe is None:
            raise ActionError("One of those recipes isn't there anymore.")
        q = _number(params, name, recipe.name)
        if q > 0:
            out[recipe.recipe_id] = q
    return out


def _market_start_describe(context, params) -> str:
    business = _need(context, "business")
    if business.open_market() is not None:
        raise ActionError("A market day is already open: close it first.")
    brought = _brought(context, params)
    book = context.craft_recipes
    things = ", ".join(_units(book.get_recipe(r), q) + f" of {book.get_recipe(r).name}" for r, q in brought.items())
    place = str(params.get("place") or "").strip() or "the market"
    return f"Open a market day at {place}" + (f", taking {things}" if things else "")


def _market_start(context, params) -> str:
    brought = _brought(context, params)
    place = str(params.get("place") or "").strip()
    _need(context, "business").start_market(place, str(params.get("date") or date.today().isoformat()), brought)
    return f"Market day open{' at ' + place if place else ''}. Tap what sells."


def _market(context, params):
    business = _need(context, "business")
    market = business.get_market(str(params.get("market_id") or "")) if params.get("market_id") else business.open_market()
    if market is None:
        raise ActionError("There's no market day open.")
    if market.status != "open":
        raise ActionError("That market day is already closed.")
    return market


def market_tally(context, market) -> dict:
    """The day's summary from the books (core/goods.py's market_summary)."""
    from core.goods import lots, market_summary

    book = context.craft_recipes
    recipes = {r.recipe_id: r for r in book.all_recipes()}
    ledger = getattr(context, "ledger", None)
    sales = ledger.all_revenue() if ledger is not None else []
    jobs = context.jobs.all_jobs() if getattr(context, "jobs", None) is not None else []
    summary = market_summary(market, sales, lots(jobs, recipes, sales, include_empty=True))
    for row in summary["rows"]:
        recipe = recipes.get(row["recipe_id"])
        row["name"] = recipe.name if recipe is not None else "Other"
    return summary


def _tosses(context, params) -> list[tuple]:
    from core.goods import fifo

    out = []
    for name, raw in params.items():
        if not name.startswith("t_") or raw in (None, ""):
            continue
        recipe = _recipe(context, name[2:])
        q = _number(params, name, recipe.name)
        if q > 0:
            taken = fifo(_lots(context, recipe.recipe_id), q)
            if sum(t for _l, t in taken) < q:
                raise ActionError(f"There aren't {q:g} of {recipe.name} left to toss.")
            out.append((recipe, q, taken))
    return out


def _xp_for(revenue: float) -> int:
    """Pure logic. A day's XP: 10 for showing up, 1 more per 5 earned, up to 100."""
    return min(100, 10 + int(revenue // 5))


def _market_close_describe(context, params) -> str:
    market = _market(context, params)
    tally = market_tally(context, market)
    tossing = _tosses(context, params)
    sold = ", ".join(f"{r['sold']:g} {r['name']}" for r in tally["rows"] if r["sold"]) or "nothing sold"
    text = f"Close the market day: {sold}, {_money(tally['revenue'])}"
    if tally["cost"]:
        text += f" (cost {_money(tally['cost'])}, profit {_money(tally['profit'])})"
    if tossing:
        text += "; toss " + ", ".join(f"{q:g} {r.name}" for r, q, _t in tossing)
    return text


def _market_close(context, params) -> str:
    from datetime import datetime

    from core.gamification import SkillWeight, grant_xp

    market = _market(context, params)
    for _recipe_, _q, taken in _tosses(context, params):
        for lot, q in taken:
            _toss(context, {"job_id": lot.job_id, "quantity": q})
    tally = market_tally(context, market)
    context.business.update_market(market.market_id, status="closed",
                                   closed_at=datetime.now().isoformat(timespec="seconds"))
    xp = _xp_for(tally["revenue"])
    grant_xp(context, xp, "✅ Sale complete!", f"{tally['sold']:g} sold, {_money(tally['revenue'])} today.",
             skill_weights=[SkillWeight("hospitality", 5)])
    return f"Market day closed: {_money(tally['revenue'])} from {tally['sold']:g} sold."


def _label_values(params) -> dict:
    from core.business_book import LABEL_FIELDS

    return {k: str(params.get(k) or "").strip() for k in LABEL_FIELDS if k in params}


def _label_describe(context, params) -> str:
    _need(context, "business")
    values = _label_values(params)
    if not values:
        raise ActionError("Nothing to change.")
    said = {"business": "business name", "address": "address", "statement": "statement"}
    return "Labels: " + "; ".join(f"{said[k]} “{v}”" if v else f"no {said[k]}" for k, v in values.items())


def _label(context, params) -> str:
    context.business.set_label(**_label_values(params))
    return "Labels updated."


LABEL_FORM = [
    {"name": "business", "label": "Business name", "type": "text", "required": False, "options": [], "default": None},
    {"name": "address", "label": "Address (as it goes on the label)", "type": "textarea", "required": False,
     "options": [], "default": None},
    {"name": "statement", "label": "Required statement (your state's or county's exact wording)", "type": "textarea",
     "required": False, "options": [], "default": None},
]


def _register() -> None:
    for kind in (
        ActionType("goods.sell", "Sold", {"recipe_id": "the recipe", "quantity": "how many",
                                          "amount": "what they sold for (blank: the recipe's price each)"},
                   _sell_describe, _sell),
        ActionType("goods.toss", "Toss", {"job_id": "the batch", "quantity": "how many (blank: all that's left)"},
                   _toss_describe, _toss),
        ActionType("market.start", "Open Market Day", {"place": "where", "date": "the day (blank: today)",
                                                       "b_<recipe_id>": "how many you're taking"},
                   _market_start_describe, _market_start),
        ActionType("goods.label", "Save", {"business": "business name", "address": "address", "statement": "required statement"},
                   _label_describe, _label),
        ActionType("market.close", "Close The Day", {"market_id": "the day (blank: the open one)",
                                                     "t_<recipe_id>": "leftovers you're tossing"},
                   _market_close_describe, _market_close),
    ):
        ACTION_TYPES[kind.kind] = kind


_register()
