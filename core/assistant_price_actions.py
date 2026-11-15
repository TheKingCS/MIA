"""
core.assistant_price_actions
==============================

Prices and comparisons by voice (Procurement P2, DEC-0172, DEC-0125):
- "Lowe's has 2x4 studs at $3.98" (`record_price`).
- "Is $3.98 a good price for 2x4 studs?" (`check_price`): against the prices seen, never a guess.
- "Compare prices for the greenhouse fans" (`compare_need`): each store's latest price for a need, its fit to the
  need's specs and the total cost with what isn't known.
- "My truck gets 17 miles per gallon and gas is $2.89" (`set_trip_cost`).
"""

from __future__ import annotations

from datetime import datetime

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run


def _record(context, arguments: dict) -> str:
    """Tool record_price: proposes `price.record`."""
    keys = ("item", "store", "price", "quantity", "unit", "specs", "was", "link")
    return _run(context, "price.record", {k: arguments.get(k) or "" for k in keys})


def _check(context, arguments: dict) -> str:
    """Tool check_price: a price against what's been seen for the same product (core/price_book.judge)."""
    from core.price_book import judge, money_in
    from core.region import money

    book = getattr(context, "prices", None)
    if book is None:
        return "Prices aren't kept on this MIA."
    item = str(arguments.get("item") or "")
    price = money_in(arguments.get("price") or "")
    if not item or price is None:
        return "Which item, and at what price?"
    seen = book.for_item(item, str(arguments.get("specs") or ""))
    j = judge(seen, price, datetime.now())
    if j["verdict"] == "too_few":
        alike = book.best(item, days=10 ** 5)
        if not seen and alike:  # prices for things like it, but not this exact product: never mixed into a verdict
            stores = ", ".join(f"{o.store} {money(o.unit_price())} ({o.item})" for o in alike[:3])
            return (f"I haven't seen this exact one, so I can't judge the price. Things like it: {stores}. "
                    f"Tell me its size or specs and I'll compare.")
        return j["said"][0].upper() + j["said"][1:] + "."
    return (f"{money(price)} is {j['said']} (I've seen {money(j['lowest'])} to {money(j['highest'])} across "
            f"{j['seen']} prices).")


def compare_sentence(context, project_words: str, item_words: str) -> str:
    """Each store's latest price for a need, with its fit to the need's specs and its total cost (what's unknown
    named)."""
    from core import product_specs
    from core.price_book import cost_per_mile, total_cost
    from core.region import money

    reqs, book, projects = (getattr(context, n, None) for n in ("requirements", "prices", "projects"))
    if reqs is None or book is None or projects is None:
        return "Needs and prices aren't kept on this MIA."
    words = " ".join(str(project_words or "").lower().split())
    project = next((p for p in projects.all_projects() if words and words in p.name.lower()), None)
    line = reqs.find(project.project_id if project else "", item_words)
    if line is None:
        return "Which need? Say the item and the project."
    offers = book.best(line.item, line.specs)
    if not offers:
        return f"I haven't seen a price for {line.item} yet. Tell me one, or record it on the Needs tab."
    per_mile = cost_per_mile(context)
    said = []
    for o in offers[:4]:
        fit = product_specs.verdict(f"{line.item} {line.specs}", o.item)
        cost = total_cost(o.unit_price(), line.quantity - line.have if line.status == "partial" else line.quantity)
        unknown = f" plus {', '.join(cost['unknown'])} not known" if cost["unknown"] else ""
        said.append(f"{o.store}: {money(o.unit_price())} each, {fit['verdict']}, {money(cost['known_total'])}{unknown}")
    trip = "" if per_mile else " Tell me your truck's miles per gallon and fuel price and I'll count the trips."
    return f"For {line.item}: " + "; ".join(said) + "." + trip


def _compare(context, arguments: dict) -> str:
    """Tool compare_need: compare_sentence for the need named."""
    return compare_sentence(context, arguments.get("project") or "", arguments.get("item") or "")


def _trip(context, arguments: dict) -> str:
    """Tool set_trip_cost: proposes `price.trip_cost`."""
    return _run(context, "price.trip_cost", {k: arguments.get(k) or "" for k in ("cost_per_mile", "mpg", "fuel_price")})


def register_price_actions(registry: AssistantActionRegistry) -> None:
    """Registers the price tools: record_price, check_price, compare_need and set_trip_cost."""
    s = {"type": "string"}
    registry.register(AssistantAction(
        name="record_price", domain="prices", description="Keep a price seen at a store.",
        parameters={"type": "object", "properties": {
            "item": {**s, "description": "what it is"}, "store": {**s, "description": "where"},
            "price": {**s, "description": "what it costs"}, "quantity": {**s, "description": "how many that's for"},
            "unit": {**s, "description": "optional"}, "specs": {**s, "description": "what it is exactly (optional)"},
            "was": {**s, "description": "a 'was' price shown (optional)"}, "link": {**s, "description": "optional"}},
            "required": ["item", "store", "price"]},
        handler=_record,
        trigger_phrases=("has it for", "the price at", "costs at", "record a price", "keep that price"),
        subjects=("price",),
    ))
    registry.register(AssistantAction(
        name="check_price", domain="prices", description="Whether a price is good, against prices seen before.",
        parameters={"type": "object", "properties": {"item": {**s, "description": "what it is"},
                                                     "price": {**s, "description": "the price"},
                                                     "specs": {**s, "description": "optional"}},
                    "required": ["item", "price"]},
        handler=_check,
        trigger_phrases=("is that a good price", "good price for", "is that a good deal", "good deal on"),
        subjects=("price", "deal"),
    ))
    registry.register(AssistantAction(
        name="compare_need", domain="prices",
        description="Compare the prices seen for something a project needs: fit, total cost.",
        parameters={"type": "object", "properties": {"project": {**s, "description": "the project"},
                                                     "item": {**s, "description": "the need's item"}},
                    "required": ["item"]},
        handler=_compare,
        trigger_phrases=("compare prices for", "where's the cheapest", "cheapest place for"),
        subjects=("price", "need"),
    ))
    registry.register(AssistantAction(
        name="set_trip_cost", domain="prices", description="Set the person's own cost per mile for trips.",
        parameters={"type": "object", "properties": {"cost_per_mile": {**s, "description": "optional"},
                                                     "mpg": {**s, "description": "miles per gallon"},
                                                     "fuel_price": {**s, "description": "fuel price"}},
                    "required": []},
        handler=_trip,
        trigger_phrases=("miles per gallon", "mpg", "cost per mile", "gas is"),
        subjects=("trip", "fuel"),
    ))
