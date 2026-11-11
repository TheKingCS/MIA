"""
core.web_business
===================

The Orders & Quotes screen (DEC-0030 phase C): orders (what's owed,
the build's progress, and where each is on the stage rail with the step
that moves it on: `order_stage`, DEC-0113), quotes (with what the price is made of),
customers, and the portfolio of finished builds. Since DEC-0153 each order
and quote belongs to a business (`entity_id`, Money's business entities),
and the screen can show one business's own (`business=`; "none" for the
ones not sorted yet). Put together here from
core/business_book.py, crafting recipes, builds and the workshop ledger;
the web only formats.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def _money(x) -> str:
    """An amount in the person's currency (core.region.money)."""
    from core.region import money

    return money(x)


STAGES = ("New", "Building", "Ready", "Delivered")


def order_stage(status: str, has_recipe: bool, has_build: bool, left: float, order_id: str) -> dict:
    """Pure logic. Where an order is on the canvas's stage rail (DEC-0113: New, Building, Ready, Delivered) and the
    one step that moves it on: Start Build (from its recipe) or Mark Building while it's new, Mark Ready while it's
    being built, Delivered once it's ready (only after Ready, H-0057), and Payment when it's delivered with money
    still owed (`opens`: the web asks how much). A cancelled order is off the rail (index None, no step)."""
    if status == "Cancelled":
        return {"index": None, "name": "Cancelled", "names": list(STAGES), "next": None}
    index = {"Open": 0, "Building": 1, "Ready": 2, "Delivered": 3}.get(status, 0)

    def to(label, new):
        return {"label": label, "action": {"kind": "order.status", "label": label,
                                           "params": {"order_id": order_id, "status": new}}}
    if index == 0:
        step = ({"label": "Start Build", "action": {"kind": "order.build", "label": "Start Build",
                                                    "params": {"order_id": order_id}}}
                if has_recipe and not has_build else to("Mark Building", "Building"))
    elif index == 1:
        step = to("Mark Ready", "Ready")
    elif index == 2:
        step = to("Delivered", "Delivered")
    else:
        step = {"label": "Payment", "opens": "payment"} if left > 0 else None
    return {"index": index, "name": STAGES[index], "names": list(STAGES), "next": step}


def business_names(context) -> dict:
    """{entity id: name} for the businesses Money keeps (core.budget_manager.BusinessEntity); {} without a budget."""
    budget = getattr(context, "budget", None)
    try:
        return {e.entity_id: e.name for e in budget.all_business_entities()} if budget is not None else {}
    except Exception:  # noqa: BLE001 - no businesses to name
        return {}


def business_page(context, today: Optional[date] = None, business: Optional[str] = None) -> dict:
    """The Business screen's data: customers, quotes (with their figures) and orders, each with its customer, its
    business (DEC-0153), the build or recipe it's for, its revenue entry, its stage and next step, and its form, plus
    the craft section (builds and recipes). `business`: only that business's orders and quotes ("none": the ones with no
    business yet); the customers stay everyone's. Not available without a business book."""
    from core.business_actions import CUSTOMER, ORDER, QUOTE, quote_figures
    from core.record_actions import record_form
    from core.web_craft import craft_section

    book = getattr(context, "business", None)
    if book is None:
        return {"available": False}
    today = today or date.today()
    entities = business_names(context)
    want = None if business is None else ("" if business == "none" else business)

    def mine(record) -> bool:
        """Whether an order or quote is the asked-for business's (every one when none was asked for)."""
        return want is None or record.entity_id == want
    ledger = getattr(context, "ledger", None)
    revenue = {r.entry_id: r for r in ledger.all_revenue()} if ledger is not None else {}
    names = {c.customer_id: c.name for c in book.customers}
    craft = craft_section(context)
    builds = {b["id"]: b for b in craft["builds"]}
    recipes = {r["id"]: r["name"] for r in craft["recipes"]}

    orders = []
    for o in sorted([o for o in book.orders if mine(o)], key=lambda o: (o.status in ("Delivered", "Cancelled"), o.due_date or "9999", o.created_at)):
        paid = round(sum(revenue[i].amount for i in o.payment_ids if i in revenue), 2)
        build = builds.get(o.job_ids[0]) if o.job_ids else None
        orders.append({
            "id": o.order_id, "title": o.title, "customer": names.get(o.customer_id, ""), "status": o.status,
            "business": entities.get(o.entity_id, ""),
            "quantity": o.quantity, "recipe": recipes.get(o.recipe_id, ""), "has_recipe": bool(o.recipe_id),
            "price": _money(o.price), "paid": _money(paid), "left": _money(max(0.0, o.price - paid)),
            "left_value": round(max(0.0, o.price - paid), 2), "due": o.due_date,
            "overdue": bool(o.due_date and o.due_date < today.isoformat() and o.status not in ("Delivered", "Cancelled")),
            "build": {"id": build["id"], "steps": f"{build['steps_done']}/{len(build['steps'])}" if build["steps"] else "",
                      "finished": build["finished"], "profit": build["result"]["profit_text"]} if build else None,
            "open": o.status not in ("Delivered", "Cancelled"), "notes": o.notes,
            "stage": order_stage(o.status, bool(o.recipe_id), bool(build), max(0.0, o.price - paid), o.order_id),
            "values": {f.name: getattr(o, f.name) for f in ORDER.fields}})

    quotes = []
    for q in sorted([q for q in book.quotes if mine(q)], key=lambda q: (q.status in ("Accepted", "Declined"), q.created_at), reverse=False):
        f = quote_figures(context, q)
        quotes.append({
            "id": q.quote_id, "title": q.title, "customer": names.get(q.customer_id, ""), "status": q.status,
            "business": entities.get(q.entity_id, ""),
            "quantity": q.quantity, "recipe": f["recipe"], "price": _money(f["price"]),
            "suggested": _money(f["suggested"]) if f["suggested"] else "", "custom_price": bool(q.price),
            "parts": [p for p in (
                ("Materials", _money(f["materials"])) if f["materials"] else None,
                (f"Labor {f['hours']:g} h × {_money(f['rate'])}", _money(f["labor"])) if f["labor"] else None,
                ("Extras", _money(f["extras"])) if f["extras"] else None,
                (f"Margin {f['margin']:g}%", "") if f["margin"] else None) if p] if f["suggested"] else [],
            "valid_until": q.valid_until, "open": q.status in ("Draft", "Sent"), "notes": q.notes,
            "values": {fld.name: getattr(q, fld.name) for fld in QUOTE.fields}})

    customers = []
    for c in sorted(book.customers, key=lambda c: c.name.lower()):
        theirs = [o for o in orders if o["values"]["customer_id"] == c.customer_id]
        spent = sum(revenue[i].amount for o in book.orders if o.customer_id == c.customer_id
                    for i in o.payment_ids if i in revenue)
        customers.append({"id": c.customer_id, "name": c.name, "phone": c.phone, "email": c.email, "notes": c.notes,
                          "orders": len(theirs), "open_orders": sum(1 for o in theirs if o["open"]),
                          "spent": _money(spent) if spent else "",
                          "values": {f.name: getattr(c, f.name) for f in CUSTOMER.fields}})

    portfolio = []
    for b in craft["builds"]:
        if not b["finished"]:
            continue
        recipe = next((r for r in craft["recipes"] if r["id"] == b["recipe_id"]), None)
        portfolio.append({"id": b["id"], "name": b["name"], "featured": b["id"] in book.featured,
                          "dimensions": recipe["dimensions"] if recipe else "",
                          "description": recipe["description"] if recipe else "",
                          "sold": b["result"]["sold_text"] if b["result"]["is_sold"] else "",
                          "photos": b["photos"], "finished": b["started"]})
    portfolio.sort(key=lambda p: (not p["featured"], book.featured.index(p["id"]) if p["featured"] else 0))

    owed = sum(o["left_value"] for o in orders if o["open"])
    return {
        "available": True, "as_of": today.isoformat(),
        "orders": orders, "quotes": quotes, "customers": customers, "portfolio": portfolio,
        "counts": {"open_orders": sum(1 for o in orders if o["open"]), "open_quotes": sum(1 for q in quotes if q["open"]),
                   "customers": len(customers), "owed": _money(owed)},
        # DEC-0153: whose orders and quotes these are (None: every business's)
        "business": None if want is None else {"id": business, "name": entities.get(want, "Not sorted yet")},
        "picks": {"customers": [{"id": c.customer_id, "name": c.name} for c in book.customers],
                  "businesses": [{"id": i, "name": n} for i, n in entities.items()],
                  "recipes": [{"id": r["id"], "name": r["name"]} for r in craft["recipes"]]},
        "forms": {"customer": record_form(CUSTOMER), "quote": record_form(QUOTE), "order": record_form(ORDER)},
    }
