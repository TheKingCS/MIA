"""
core.flock_actions
====================

Chickens' actions (DEC-0037, core/flock.py) on the action contract:
proposed in plain words, approved, run, undoable.

- `flock.add/edit/delete`: a flock (name, breed, hens, roosters, when they
  came, the good its cartons go into).
- `flock.eggs`: eggs collected (today unless a day is given).
- `flock.feed`: feed bought (pounds, cost), also a cost in the business's
  books (core/ledger_manager.py), like materials bought for a recipe.
- `flock.birds`: birds added (+) or lost (−), and why.
- `flock.use`: loose eggs into a **carton** (goods on hand, at the feed
  cost; core/goods_actions.py add_to_stock), into the **bakery**
  (Materials, at the feed cost each) or eaten at **home**.
- `flock.entry_delete`: take back a line of the log.
"""

from __future__ import annotations

from datetime import date

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_kinds
from core.units import amount_text, convert, kind

FLOCK = Record("flock", "flock", "flock_id", "get_flock", "add_flock", "update_flock", "delete_flock",
               store="flock", fields=(
                   Field("name", "Name (the coop, the layers…)", "text", True),
                   Field("breed", "Breed", "text"),
                   Field("hens", "Hens", "int", default=0, say="hens"),
                   Field("roosters", "Roosters", "int", default=0, say="roosters", quiet_default=True),
                   Field("started", "When they came", "date", say="start"),
                   Field("egg_recipe_id", "Cartons go into (a good under Workshop → Recipes)", "pick",
                         options=("egg_goods",), say="good for cartons"),
                   Field("notes", "Notes", "textarea")))

USE_SAID = {"carton": "into cartons", "baking": "into the bakery", "home": "eaten at home"}


def _money(x: float) -> str:
    from core.region import money

    return money(x)


def _book(context):
    return _need(context, "flock")


def _flock(context, params):
    flocks = _book(context).flocks
    wanted = str(params.get("flock_id") or "")
    found = _book(context).get_flock(wanted) if wanted else (flocks[0] if len(flocks) == 1 else None)
    if found is None:
        raise ActionError("Which flock?" if flocks and not wanted else "That flock isn't there anymore."
                          if wanted else "Add your flock first.")
    return found


def _number(params, name: str, label: str, whole: bool = False, signed: bool = False) -> float:
    raw = params.get(name)
    if raw in (None, ""):
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ActionError(f"{label} has to be a number.") from None
    if value < 0 and not signed:
        raise ActionError(f"{label} can't be negative.")
    if whole and value != int(value):
        raise ActionError(f"{label} has to be a whole number.")
    return value


def _day(params) -> str:
    raw = str(params.get("date") or "").strip()
    if not raw:
        return date.today().isoformat()
    try:
        return date.fromisoformat(raw[:10]).isoformat()
    except ValueError:
        raise ActionError("The date has to look like 2026-10-21.") from None


def _figures(context, f) -> dict:
    from core.flock import figures

    return figures(f, _book(context).entries, date.today())


def _when(day: str) -> str:
    return "" if day == date.today().isoformat() else f" on {day}"


# ---------------------------------------------------------------- eggs, feed, birds


def _eggs(context, params):
    f = _flock(context, params)
    n = _number(params, "count", "How many eggs", whole=True)
    if n <= 0:
        raise ActionError("How many eggs?")
    return f, n, _day(params)


def _eggs_describe(context, params) -> str:
    f, n, day = _eggs(context, params)
    return f"{n:g} eggs from {f.name}{_when(day)}"


def _eggs_run(context, params) -> str:
    from core.gamification import SkillWeight, grant_xp

    f, n, day = _eggs(context, params)
    _book(context).log(f.flock_id, "eggs", day, count=n)
    grant_xp(context, 2, "🥚 Eggs in!", f"{n:g} from {f.name}.", skill_weights=[SkillWeight("animal_care", 2)])
    loose = _figures(context, f)["loose"]
    return f"{n:g} eggs logged. {loose:g} loose on hand."


def _feed(context, params):
    f = _flock(context, params)
    pounds = _number(params, "pounds", "Pounds")
    cost = _number(params, "cost", "What it cost")
    if not pounds and not cost:
        raise ActionError("How much feed, and what did it cost?")
    return f, pounds, cost, _day(params)


def _feed_describe(context, params) -> str:
    f, pounds, cost, day = _feed(context, params)
    what = " ".join(b for b in (f"{pounds:g} lb" if pounds else "", "of feed", f"for {_money(cost)}" if cost else "") if b)
    tail = "; a cost in the business's books" if cost and getattr(context, "ledger", None) is not None else ""
    return f"Bought {what} for {f.name}{_when(day)}{tail}"


def _feed_run(context, params) -> str:
    f, pounds, cost, day = _feed(context, params)
    _book(context).log(f.flock_id, "feed", day, pounds=pounds, cost=cost)
    ledger = getattr(context, "ledger", None)
    if cost and ledger is not None:
        ledger.add_expense(cost, "Materials", f"Feed for {f.name}", date=day)
    return "Feed logged."


def _birds(context, params):
    f = _flock(context, params)
    change = _number(params, "change", "How many", whole=True, signed=True)
    if not change:
        raise ActionError("How many came or went? (+ added, − lost)")
    if f.hens + change < 0:
        raise ActionError(f"{f.name} only has {f.hens} hens.")
    return f, change, str(params.get("why") or "").strip(), _day(params)


def _birds_describe(context, params) -> str:
    f, change, why, day = _birds(context, params)
    what = f"{change:+g} {'hen' if abs(change) == 1 else 'hens'}".replace("+", "Add ").replace("-", "Lost ")
    return f"{what} ({f.name}: {f.hens} → {f.hens + int(change)}){': ' + why if why else ''}{_when(day)}"


def _birds_run(context, params) -> str:
    f, change, why, day = _birds(context, params)
    _book(context).log(f.flock_id, "birds", day, count=change, note=why)
    return f"{f.name} has {f.hens} hens now."


# ---------------------------------------------------------------- where the eggs go


def _egg_good(context, f, params):
    """The recipe the cartons go into: the flock's own, or the one picked."""
    book = _need(context, "craft_recipes")
    recipe = book.get_recipe(str(params.get("recipe_id") or f.egg_recipe_id or ""))
    if recipe is None:
        raise ActionError("Which good do the cartons go into? Add one under Workshop → Recipes "
                          "(e.g. “Eggs”, makes 1 dozen), then pick it on the flock.")
    return recipe


def _using(context, params):
    f = _flock(context, params)
    use = str(params.get("use") or "").strip().lower()
    if use not in USE_SAID:
        raise ActionError("Into cartons, the bakery, or eaten at home?")
    n = _number(params, "eggs", "How many eggs", whole=True)
    if n <= 0:
        raise ActionError("How many eggs?")
    fig = _figures(context, f)
    if n > fig["loose"]:
        raise ActionError(f"Only {fig['loose']:g} loose eggs on hand: log what was collected first.")
    plan = {"flock": f, "use": use, "eggs": n, "each_egg": fig["feed_per_egg"]}
    if use == "carton":
        recipe = _egg_good(context, f, params)
        unit = recipe.makes_unit or "dozen"
        qty = _number(params, "stock_qty", "How many")
        if not qty:
            # Eggs to the good's unit: dozens, half dozens, eggs. A carton of
            # something else ("carton", "flat") needs saying how many.
            qty = convert(n, "", unit) if kind(unit) == "count" else None
        if not qty:
            raise ActionError(f"How many {amount_text(2, unit).split(' ', 1)[1]} is that?")
        plan.update(recipe=recipe, qty=round(qty, 4), unit=unit,
                    cost_each=round(fig["feed_per_dozen"] * n / 12 / qty, 4) if qty else 0.0)
    elif use == "baking":
        plan["material"] = str(params.get("material") or "").strip() or "Eggs"
    return plan


def _use_describe(context, params) -> str:
    p = _using(context, params)
    text = f"{p['eggs']:g} eggs from {p['flock'].name} {USE_SAID[p['use']]}"
    if p["use"] == "carton":
        text += f": {amount_text(p['qty'], p['unit'])} of {p['recipe'].name} into stock"
        if p["cost_each"]:
            text += f" at {_money(p['cost_each'])} each (feed)"
    elif p["use"] == "baking":
        text += f": into Materials as {p['material']}" + (f" at {_money(p['each_egg'])} each (feed)" if p["each_egg"] else "")
    return text


def _use_run(context, params) -> str:
    p = _using(context, params)
    f = p["flock"]
    _book(context).log(f.flock_id, "use", _day(params), count=p["eggs"], use=p["use"])
    if p["use"] == "carton":
        from core.goods_actions import add_to_stock

        add_to_stock(context, p["recipe"], p["qty"], p["cost_each"], source=f"from {f.name}")
        return f"{amount_text(p['qty'], p['unit'])} of {p['recipe'].name} in stock."
    if p["use"] == "baking":
        from core.craft_recipes import average_cost, key

        materials = _need(context, "materials")
        found = next((m for m in materials.all_materials() if key(m.name) == key(p["material"])), None)
        if found is None:
            materials.add_material(p["material"], unit="", unit_cost=p["each_egg"], quantity_on_hand=p["eggs"])
        else:
            if p["each_egg"]:
                materials.update_material(found.material_id, unit_cost=average_cost(
                    found.quantity_on_hand, found.unit_cost, p["eggs"], p["each_egg"]))
            materials.adjust_quantity(found.material_id, p["eggs"])
        return f"{p['eggs']:g} eggs in Materials for baking."
    return "Noted."


def _entry(context, params):
    book = _book(context)
    entry = next((e for e in book.entries if e.entry_id == str(params.get("entry_id") or "")), None)
    if entry is None:
        raise ActionError("That entry isn't there anymore.")
    return entry


def _entry_said(e) -> str:
    if e.kind == "eggs":
        return f"{e.count:g} eggs collected"
    if e.kind == "feed":
        return "feed bought" + (f" ({_money(e.cost)})" if e.cost else "")
    if e.kind == "birds":
        n = abs(int(e.count))
        return f"{n} {'hen' if n == 1 else 'hens'} {'added' if e.count > 0 else 'lost'}"
    return f"{e.count:g} eggs {USE_SAID.get(e.use, e.use)}"


def _entry_delete_describe(context, params) -> str:
    e = _entry(context, params)
    note = " (what it put into stock or Materials stays; change that there)" if e.kind == "use" else ""
    return f"Take back: {_entry_said(e)} on {e.date}{note}"


def _entry_delete(context, params) -> str:
    e = _entry(context, params)
    _book(context).delete_entry(e.entry_id)
    return "Taken back."


def _register() -> None:
    kinds = list(record_kinds(FLOCK)) + [
        ActionType("flock.eggs", "Log Eggs", {"flock_id": "the flock", "count": "how many", "date": "the day (blank: today)"},
                   _eggs_describe, _eggs_run),
        ActionType("flock.feed", "Bought Feed", {"flock_id": "the flock", "pounds": "pounds", "cost": "what it cost",
                                                 "date": "the day"}, _feed_describe, _feed_run),
        ActionType("flock.birds", "Birds", {"flock_id": "the flock", "change": "+ added, − lost", "why": "why",
                                            "date": "the day"}, _birds_describe, _birds_run),
        ActionType("flock.use", "Use Eggs", {"flock_id": "the flock", "use": "carton, baking or home", "eggs": "how many eggs",
                                             "recipe_id": "the good (cartons)", "stock_qty": "how many of the good",
                                             "material": "the material (baking)", "date": "the day"},
                   _use_describe, _use_run),
        ActionType("flock.entry_delete", "Take Back", {"entry_id": "the line"}, _entry_delete_describe, _entry_delete),
    ]
    for k in kinds:
        ACTION_TYPES[k.kind] = k


_register()
