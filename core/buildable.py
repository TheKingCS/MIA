"""
core.buildable
================

What he could build with what he has (Jarvis brainstorm round 7, 2026-11-24; one intelligence: his stock read
against the Library's plans, docs/future/UNIFIED_INTELLIGENCE.md): "what can I build with what I have?", "what could
I build with the lumber in the shop?".

**How.** Every built-in Library plan at its starting size (core/plan_library.py, quantities from core/build_calcs.py)
is laid against the workshop's materials (`shopping_list`: each item, how many are on hand, how many to buy, and the
cost where his workshop has a price). A plan counts by how many of its materials are fully covered; the ones with
the most covered come first, then the cheapest to finish. Each says what's still to buy and its known cost; a
material with no price makes that a floor, said as "at least". Plans with nothing on hand aren't listed. Read-only:
starting one is "let's plan the ..." (core/project_plans.py), which waits for his Confirm.
"""

from __future__ import annotations

from core.logger import get_logger

log = get_logger(__name__)

SHOW = 3  # plans said


def ranked(context) -> list[dict]:
    """The Library's built-in plans against the workshop's stock, best first: each {id, title, covered, partly,
    items, to_buy, cost, unpriced}. `covered` counts materials fully on hand, `partly` those with some; plans with
    nothing on hand are left out. [] without the Library or any stock."""
    from core.plan_library import shopping_list

    library = getattr(context, "plans", None)
    stock = list(getattr(getattr(context, "materials", None), "all_materials", lambda: [])())
    if library is None or not stock:
        return []
    out = []
    for plan in library.built_in():
        shopping = shopping_list(context, plan.get("materials") or {})
        rows = shopping["rows"]
        covered = sum(1 for r in rows if r["have"] and r["buy"] <= 0)
        partly = sum(1 for r in rows if r["have"] and r["buy"] > 0)
        if not rows or not (covered or partly):
            continue
        out.append({"id": plan["id"], "title": plan["title"], "covered": covered, "partly": partly,
                    "items": len(rows), "to_buy": [r["item"] for r in shopping["to_buy"]],
                    "cost": shopping["known_cost"], "unpriced": len(shopping["to_buy"]) - shopping["priced"]})
    return sorted(out, key=lambda p: (-p["covered"] / p["items"], -p["partly"], p["cost"], p["title"]))


def say(context) -> str:
    """The best few (`SHOW`) in words: how much of each is on hand, what's left to buy and its cost."""
    from core.region import money

    if getattr(context, "plans", None) is None:
        return "The Library's plans aren't on this MIA, so I can't lay your stock against them."
    if not list(getattr(getattr(context, "materials", None), "all_materials", lambda: [])()):
        return ("Your workshop has no materials logged yet. Add what's in the shop under Workshop, Materials, and I'll "
                "tell you what you could build with it.")
    best = ranked(context)
    if not best:
        return "None of the Library's builds uses anything in your workshop's stock yet."
    parts = []
    for p in best[:SHOW]:
        line = f"{p['title']}: {p['covered']} of its {p['items']} materials on hand"
        line += f" ({p['partly']} more partly)" if p["partly"] else ""
        if not p["to_buy"]:
            line += ", nothing left to buy"
        else:
            named = ", ".join(p["to_buy"][:3]) + (f" and {len(p['to_buy']) - 3} more" if len(p["to_buy"]) > 3 else "")
            line += f"; still to buy: {named}"
            if p["cost"]:
                line += f", {'at least ' if p['unpriced'] else ''}{money(p['cost'])}"
            elif p["unpriced"]:
                line += " (no prices in your workshop yet)"
        parts.append(line + ".")
    return ("Closest to buildable from your stock, at each plan's starting size: " + " ".join(parts)
            + " Say \"let's plan the\" one you want and I'll draft it at your size.")
