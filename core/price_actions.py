"""
core.price_actions
====================

Prices on the action contract (Procurement P2, DEC-0172; core/price_book.py): proposed in plain words, approved,
run, undoable.

- `price.record`: a price seen ("Lowe's has 2x4 studs at $3.98"), with its store, quantity, unit, specs and link.
- `price.trip_cost`: the person's own cost per mile, given directly or as miles per gallon and a fuel price (Zac,
  2026-11-15: "use my own figures"); their own settings.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _book(context):
    """The person's price observations, or ActionError."""
    return _need(context, "prices")


def _number(value, what: str, required: bool = True):
    """A number from a form or a tool ("$3.98", "12"), never below zero; None when optional and blank; ActionError
    otherwise."""
    if value in (None, ""):
        if required:
            raise ActionError(f"What's the {what}?")
        return None
    try:
        number = float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        raise ActionError(f"What's the {what}?") from None
    if number != number or number < 0 or number == float("inf"):
        raise ActionError(f"The {what} can't be below zero.")
    return number


def _record_describe(context, params) -> str:
    """The approval sentence for `price.record`."""
    from core.region import money

    item, store = " ".join(str(params.get("item") or "").split()), " ".join(str(params.get("store") or "").split())
    if not item or not store:
        raise ActionError("What was it, and at which store?")
    price = _number(params.get("price"), "price")
    qty = _number(params.get("quantity"), "quantity", required=False) or 1
    return f"Keep the price: {item} at {store}, {money(price)}" + (f" for {qty:g}" if qty != 1 else "")


def _record_execute(context, params) -> str:
    """Does `price.record`, and says how it compares with what's been seen."""
    from datetime import datetime

    from core.price_book import judge
    from core.region import money

    book = _book(context)
    try:
        obs = book.record(params.get("item"), params.get("store"), _number(params.get("price"), "price"),
                          _number(params.get("quantity"), "quantity", required=False) or 1,
                          str(params.get("unit") or ""), str(params.get("specs") or ""),
                          was=_number(params.get("was"), "was price", required=False) or 0.0,
                          link=str(params.get("link") or ""), origin=str(params.get("link") or "said"),
                          how="observed" if params.get("link") else "said")
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    earlier = [o for o in book.for_product(obs.product_key) if o.observation_id != obs.observation_id]
    j = judge(earlier, obs.unit_price(), datetime.now(), obs.was)
    note = f" That's {j['said']}." if j["verdict"] != "too_few" else ""
    return f"Kept: {obs.item} at {obs.store}, {money(obs.price)}.{note}" + (f" Note: {j['was_note']}." if j["was_note"] else "")


def _trip_describe(context, params) -> str:
    """The approval sentence for `price.trip_cost`."""
    from core.region import money

    direct = _number(params.get("cost_per_mile"), "cost per mile", required=False)
    if direct:
        return f"Use {money(direct)} a mile for trips"
    mpg = _number(params.get("mpg"), "miles per gallon", required=False)
    fuel = _number(params.get("fuel_price"), "fuel price", required=False)
    if not mpg or not fuel:
        raise ActionError("Give a cost per mile, or miles per gallon and what fuel costs.")
    return f"Work out trips from {mpg:g} miles per gallon and fuel at {money(fuel)} ({money(fuel / mpg)} a mile)"


def _trip_execute(context, params) -> str:
    """Does `price.trip_cost`: the person's own settings."""
    from core import person_settings
    from core.region import money

    direct = _number(params.get("cost_per_mile"), "cost per mile", required=False)
    if direct:
        person_settings.put(context, "procurement.cost_per_mile", direct)
        return f"Trips now count {money(direct)} a mile."
    mpg, fuel = _number(params.get("mpg"), "miles per gallon"), _number(params.get("fuel_price"), "fuel price")
    if not mpg or not fuel:
        raise ActionError("Give a cost per mile, or miles per gallon and what fuel costs.")
    person_settings.put(context, "procurement.cost_per_mile", 0)
    person_settings.put(context, "procurement.mpg", mpg)
    person_settings.put(context, "procurement.fuel_price", fuel)
    return f"Trips now count {money(fuel / mpg)} a mile ({mpg:g} miles per gallon, fuel at {money(fuel)})."


def _register() -> None:
    """Adds the price kinds to ACTION_TYPES. Runs once, when this module is imported."""
    for k in (
        ActionType("price.record", "Record a Price", {"item": "what it is", "store": "where", "price": "what it costs",
                                                      "quantity": "how many that's for", "unit": "unit (optional)",
                                                      "specs": "what it is exactly (optional)",
                                                      "was": "a 'was' price shown (optional)", "link": "link (optional)"},
                   _record_describe, _record_execute),
        ActionType("price.trip_cost", "Trip Cost", {"cost_per_mile": "cost per mile", "mpg": "or miles per gallon",
                                                    "fuel_price": "and fuel price"},
                   _trip_describe, _trip_execute),
    ):
        ACTION_TYPES[k.kind] = k


_register()
