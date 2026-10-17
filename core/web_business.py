"""
core.web_business
===================

The Orders & Quotes screen (DEC-0030 phase C): orders (what's owed,
the build's progress), quotes (with what the price is made of),
customers, and the portfolio of finished builds. Put together here from
core/business_book.py, crafting recipes, builds and the workshop ledger;
the web only formats.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def _money(x) -> str:
    from core.region import money

    return money(x)


def business_page(context, today: Optional[date] = None) -> dict:
    from core.business_actions import CUSTOMER, ORDER, QUOTE, quote_figures
    from core.record_actions import record_form
    from core.web_craft import craft_section

    book = getattr(context, "business", None)
    if book is None:
        return {"available": False}
    today = today or date.today()
    ledger = getattr(context, "ledger", None)
    revenue = {r.entry_id: r for r in ledger.all_revenue()} if ledger is not None else {}
    names = {c.customer_id: c.name for c in book.customers}
    craft = craft_section(context)
    builds = {b["id"]: b for b in craft["builds"]}
    recipes = {r["id"]: r["name"] for r in craft["recipes"]}

    orders = []
    for o in sorted(book.orders, key=lambda o: (o.status in ("Delivered", "Cancelled"), o.due_date or "9999", o.created_at)):
        paid = round(sum(revenue[i].amount for i in o.payment_ids if i in revenue), 2)
        build = builds.get(o.job_ids[0]) if o.job_ids else None
        orders.append({
            "id": o.order_id, "title": o.title, "customer": names.get(o.customer_id, ""), "status": o.status,
            "quantity": o.quantity, "recipe": recipes.get(o.recipe_id, ""), "has_recipe": bool(o.recipe_id),
            "price": _money(o.price), "paid": _money(paid), "left": _money(max(0.0, o.price - paid)),
            "left_value": round(max(0.0, o.price - paid), 2), "due": o.due_date,
            "overdue": bool(o.due_date and o.due_date < today.isoformat() and o.status not in ("Delivered", "Cancelled")),
            "build": {"id": build["id"], "steps": f"{build['steps_done']}/{len(build['steps'])}" if build["steps"] else "",
                      "finished": build["finished"], "profit": build["result"]["profit_text"]} if build else None,
            "open": o.status not in ("Delivered", "Cancelled"), "notes": o.notes,
            "values": {f.name: getattr(o, f.name) for f in ORDER.fields}})

    quotes = []
    for q in sorted(book.quotes, key=lambda q: (q.status in ("Accepted", "Declined"), q.created_at), reverse=False):
        f = quote_figures(context, q)
        quotes.append({
            "id": q.quote_id, "title": q.title, "customer": names.get(q.customer_id, ""), "status": q.status,
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
        "picks": {"customers": [{"id": c.customer_id, "name": c.name} for c in book.customers],
                  "recipes": [{"id": r["id"], "name": r["name"]} for r in craft["recipes"]]},
        "forms": {"customer": record_form(CUSTOMER), "quote": record_form(QUOTE), "order": record_form(ORDER)},
    }
