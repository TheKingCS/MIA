"""
core.make_next
================

"What should I make next?" (Jarvis brainstorm, round 11: his businesses, from his own records): the workshop's
products that sell, against what's on the shelf and what each one earns an hour, so the next build is the one that
both runs out soonest and pays best.

**How** (`ranked`): for each product, the pieces sold in the last `WINDOW_DAYS` (the ledger's sales of that product,
their quantity, else one a sale) as a rate a month; the stock on hand (core/product_manager.py) as months left at
that rate; and what a piece keeps an hour of work (its price less its materials, over its hours: core/product_pricing
.per_piece, from the finished jobs that made it). A product with sales and under `LOW_MONTHS` of stock is one to
make; those are ranked by what they earn an hour (unknown last), then by how soon they run out. A product that
hasn't sold in the window is never suggested.

Read only; every number from his records. Making one is the Workshop's job (a build), his to start.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

WINDOW_DAYS = 90
LOW_MONTHS = 1.0


def ranked(context, today: Optional[date] = None) -> list[dict]:
    """Every product that sold in the window: {name, sold, per_month, stock, months_left, per_hour (None unknown),
    low}, the ones to make first (low stock, best per hour, soonest out) at the top."""
    from core.product_pricing import per_piece

    today = today or date.today()
    products = getattr(context, "products", None)
    ledger = getattr(context, "ledger", None)
    if products is None or ledger is None:
        return []
    since = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    sold: dict = {}
    for r in ledger.all_revenue():
        if r.product_id and str(r.date or "")[:10] >= since:
            sold[r.product_id] = sold.get(r.product_id, 0.0) + (float(r.quantity_sold or 0) or 1.0)
    pieces = per_piece(context)
    rows = []
    for p in products.all_products():
        n = sold.get(p.product_id, 0.0)
        if n <= 0:
            continue
        per_month = n / (WINDOW_DAYS / 30.0)
        stock = max(0.0, float(p.quantity_in_stock or 0))
        piece = pieces.get(p.product_id)
        per_hour = (round((float(p.base_price or 0) - piece["materials"]) / piece["hours"], 2)
                    if piece and piece.get("timed") and piece.get("hours") and p.base_price else None)
        months = stock / per_month if per_month else None
        rows.append({"name": p.name, "sold": n, "per_month": round(per_month, 1), "stock": stock,
                     "months_left": round(months, 1) if months is not None else None, "per_hour": per_hour,
                     "low": months is not None and months < LOW_MONTHS})
    return sorted(rows, key=lambda r: (not r["low"], r["per_hour"] is None, -(r["per_hour"] or 0),
                                       r["months_left"] if r["months_left"] is not None else 99))


def say(context, today: Optional[date] = None) -> str:
    """The answer: the products to make next (up to three) with why, or what's on hand when nothing's running low."""
    from core.region import money

    rows = ranked(context, today)
    if not rows:
        return ("I don't see sales of your products in the last 90 days. Log sales against a product (Workshop, "
                "Sales) and I can say what to make next.")
    low = [r for r in rows if r["low"]][:3]
    if not low:
        best = rows[0]
        return ("Nothing's running low: every product that sells has a month or more on the shelf. "
                f"{best['name']} sells about {best['per_month']:g} a month with {best['stock']:g} on hand.")

    def line(r):
        """One product's reason."""
        stock = "none left" if r["stock"] <= 0 else f"{r['stock']:g} left (about {r['months_left']:g} months)"
        pay = f", and it keeps about {money(r['per_hour'])} an hour of your work" if r["per_hour"] is not None else ""
        return f"{r['name']}: you sell about {r['per_month']:g} a month, {stock}{pay}."
    return "Make these next: " + " ".join(line(r) for r in low)


def _tool(context, arguments: dict) -> str:
    """Tool what_to_make_next."""
    return say(context)


def register_make_next_actions(registry) -> None:
    """Registers what_to_make_next."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="what_to_make_next", domain="business",
        description="Which of his workshop's products to make next: the ones that sell, running low on the shelf, "
                    "and what each keeps an hour of his work. Homestead projects to build are get_homestead_next_step.",
        parameters={"type": "object", "properties": {}},
        handler=_tool, trigger_phrases=("make next", "build next to sell", "running low on stock", "what sells",
                                        "what's selling", "restock", "make more of", "out of stock",
                                        "products running low", "products are running low", "products are low",
                                        "low on products", "products low"),
    ))
