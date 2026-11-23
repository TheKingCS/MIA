"""
core.plan_price
=================

What a Planner build would cost, and what to charge for it (Jarvis brainstorm 5.1; Zac, 2026-11-23: "my businesses
skills"): from the build's own material list at his size (core/plan_library.detail, its quantities from
core/build_calcs.py), every material priced at what it costs him (the workshop's materials, `unit_cost`), the hours
he says at his labor rate (`workshop.labor_rate_per_hour`), and his margin, through the same arithmetic his quotes
use (core/business_book.suggested_price). All of it in code; the model only says it.

A material with no price in his workshop is named, never guessed, and the price is called a floor until they're
priced. Materials already on hand still count: they're used up by the job. Making it a real quote for a customer stays
on the Workshop's Quotes, with his press.
"""

from __future__ import annotations

from typing import Optional

DEFAULT_MARGIN = 20.0  # percent, as a new quote starts (core/business_actions.py)


def costed(items: list, stock: list) -> dict:
    """Pure logic. A material list priced from his stock: {lines: [(name, qty, unit, cost or None)], known, unpriced}.
    Each item's whole quantity counts (what's on hand gets used up too)."""
    from core.plan_library import _match

    lines, known, unpriced = [], 0.0, []
    for item in items:
        qty = float(item.get("qty") or 0)
        match = _match(item["name"], stock)
        cost = round(qty * float(match.unit_cost), 2) if match is not None and match.unit_cost and qty else None
        if cost is None and qty:
            unpriced.append(item["name"])
        else:
            known += cost or 0.0
        lines.append((item["name"], qty, item.get("unit", ""), cost))
    return {"lines": lines, "known": round(known, 2), "unpriced": unpriced}


def find(context, words: str = ""):
    """The Planner build the words name (its title holds them all), else the newest build; None without one."""
    book = getattr(context, "project_plans", None)
    if book is None:
        return None
    builds = [p for p in book.listed() if p.kind == "build" and p.status != "dropped" and p.shelf_plan]
    want = [w for w in str(words or "").lower().split() if len(w) > 2 and w not in ("the", "for", "plan", "build")]
    named = [p for p in builds if want and all(w in p.title.lower() for w in want)]
    return (named or ([] if want else builds) or [None])[0]


def say(context, words: str = "", hours: Optional[float] = None, margin: Optional[float] = None) -> str:
    """The build's cost and price in words: materials (priced, and those with no price), labor, margin, the price."""
    from core.business_book import suggested_price
    from core.plan_library import detail
    from core.region import money

    plan = find(context, words)
    if plan is None:
        return ("I don't have a build in the Planner to price" + (f" called \"{words}\"" if words else "") +
                ". Start one there, like \"plan a 10 by 12 shed\", and I'll price it.")
    page = detail(context, plan.shelf_plan, plan.sizes or None)
    if not page:
        return f"\"{plan.title}\"'s plan isn't on the Library's shelf any more, so I can't read its materials."
    stock = list(getattr(getattr(context, "materials", None), "all_materials", lambda: [])())
    priced = costed(page.get("items", []), stock)
    config = getattr(context, "config", None)
    rate = float(config.get("workshop.labor_rate_per_hour", 0) or 0) if config is not None else 0.0
    margin = DEFAULT_MARGIN if margin is None else max(0.0, float(margin))
    hours = max(0.0, float(hours or 0))
    parts = [f"{plan.title}: materials {money(priced['known'])}"
             + (f" for the {len(priced['lines']) - len(priced['unpriced'])} priced in your workshop" if priced["unpriced"] else "")
             + "."]
    if priced["unpriced"]:
        parts.append("No price yet for " + ", ".join(priced["unpriced"][:6])
                     + (f" and {len(priced['unpriced']) - 6} more" if len(priced["unpriced"]) > 6 else "")
                     + ": add their cost under Workshop, Materials, and this gets complete.")
    if hours and rate:
        parts.append(f"Labor: {hours:g} hours at {money(rate)} an hour is {money(hours * rate)}.")
    elif hours:
        parts.append(f"{hours:g} hours, but no labor rate set: set yours in the Workshop's quotes.")
    else:
        parts.append("Tell me how many hours it'll take you and I'll add the labor.")
    price = suggested_price(priced["known"], hours, rate, 0.0, margin)
    if price:
        word = "at least " if priced["unpriced"] else ""
        parts.append(f"With a {margin:g}% margin, charge {word}{money(price)}. Making it a quote for a customer is on "
                     "the Workshop's Quotes.")
    return " ".join(parts)
