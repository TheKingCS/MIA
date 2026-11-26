"""
core.side_hustle
==================

"What's a good side hustle for me?" (the live sweep, 2026-11-26: the model guessed, from a fishing mission and an
overdue bill), answered from what he already has and does, each idea with the one next step:

- **what already sells**: his products by what they've brought in over the last year (the workshop ledger's
  revenue by product, core/ledger_manager), the best first;
- **the flock**: eggs, when he has hens (core/flock), priced from his own feed ("how much should I charge for a
  dozen eggs?");
- **what he's learning**: a course he's on (core/paths) that leads to work people pay for (woodworking, carpentry,
  small engines, soldering);
- **his equipment**: a tool or machine of his (core/maintenance_manager's assets) others hire out (a log splitter, a
  trailer, a mower, a chainsaw), with a word to check insurance first for work on others' property.

Read only; nothing is guessed: with nothing in his records, it says what it would look at.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

SHOWN = 4
SERVICE_COURSES = {"woodworking": "custom pieces and repairs", "carpentry": "small carpentry jobs (decks, sheds, "
                   "fences)", "soldering": "fixing electronics and making sensors"}
CHECK_FIRST = " Check your insurance (and any licence your state wants) before you take money for it."
# (words in an asset's name, the work, whether it needs the insurance word): never a camper's "travel trailer"
HIRE_OUT = ((r"log splitter|splitter", "splitting and selling firewood", False),
            (r"(?<!travel )(?<!camper )(?:utility |dump |flatbed )?trailer", "hauling and dump runs", True),
            (r"(?:lawn ?|riding |push |zero[- ]turn )?mower|lawnmower", "mowing in your area", True),
            (r"tractor", "brush hogging and plowing for neighbours", True),
            (r"chainsaw", "cutting and selling firewood (leave felling near houses to an insured arborist)", True),
            (r"pressure washer", "pressure washing decks and siding", True),
            (r"welder", "welding repairs", True))


def ideas(context, today: Optional[date] = None) -> list[str]:
    """The ideas his own records support, each in a sentence with its next step (work on others' property with a
    word to check insurance first); [] with none."""
    from core.region import money

    today = today or date.today()
    out = []
    ledger, products = getattr(context, "ledger", None), getattr(context, "products", None)
    if ledger is not None and products is not None:
        since = (today - timedelta(days=365)).isoformat()
        names = {p.product_id: p.name for p in products.all_products()}
        earned: dict = {}
        for r in ledger.all_revenue():
            if r.product_id in names and str(r.date or "") >= since:
                earned[r.product_id] = earned.get(r.product_id, 0.0) + float(r.amount or 0)
        for pid, total in sorted(earned.items(), key=lambda kv: -kv[1])[:2]:
            out.append(f"More of your {names[pid]}: it's brought in {money(total)} this past year. Ask \"should I raise "
                       f"my prices?\" to check it pays for your time.")
    flock = getattr(context, "flock", None)
    if flock is not None and any(max(0, getattr(f, "hens", 0) or 0) for f in getattr(flock, "flocks", []) or []):
        out.append("Eggs from your hens: ask \"how much should I charge per dozen eggs?\" and I'll price them from "
                   "your feed.")
    book = getattr(context, "paths", None)
    if book is not None:
        for path_id in book.started():
            if path_id in SERVICE_COURSES:
                out.append(f"{SERVICE_COURSES[path_id][:1].upper() + SERVICE_COURSES[path_id][1:]}, from the course "
                           f"you're on: once you've a few pieces done, they're the portfolio.")
    maintenance = getattr(context, "maintenance", None)
    if maintenance is not None:
        seen = set()
        for asset in maintenance.all_assets():
            name = (asset.name or "").lower()
            for words, work, insure in HIRE_OUT:
                if re.search(rf"\b(?:{words})\b", name) and work not in seen:
                    seen.add(work)
                    out.append(f"{work[:1].upper() + work[1:]}, with your {asset.name}." + (CHECK_FIRST if insure else ""))
    return out[:SHOWN]


def say(context, today: Optional[date] = None) -> str:
    """For "what's a good side hustle for me?": the ideas from his records, or what she'd look at."""
    found = ideas(context, today)
    if not found:
        return ("I don't have enough in your records to say yet. I'd look at what you already sell, your hens, the "
                "courses you're on and the equipment you own: log a sale, your flock or your tools and ask me again.")
    return "From what you already have: " + " ".join(f"{i + 1}. {idea}" for i, idea in enumerate(found))
