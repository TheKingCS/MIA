"""
core.web_businesses
=====================

Finances › Businesses (DEC-0153, Zac 2026-11-11): "a sub dashboard under
Finances with a quick view of each businesses info where you can click
into each business to bring up its own dashboard", and "orders and quotes
will be a section under each business with info specific to that
business".

What it shows: each business Money keeps (core.budget_manager.BusinessEntity)
with this month's and this year's money (its own tagged income and
expenses), what it still owes, its properties (Real Estate) and its open
orders and quotes (core/business_book.py, by `entity_id`); and, per
business, its own dashboard: the money with where it went, the latest
income and expenses, its properties, its orders and quotes (the same rows
as Orders & Quotes, only its own), its debts, and the apps it uses.

How: everything is read from the stores that own it; nothing is copied.
`businesses_page(context, today)` is the subdashboard;
`business_dashboard(context, entity_id, today)` one business (None for an
unknown id). Served as `/api/businesses` and `/api/businesses/<id>`;
`web/businesses.html` and `web/biz.html` only draw them.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

RECENT = 6  # latest income and expense lines on a business's dashboard


def _money(x: float) -> str:
    """An amount in the person's currency (core.region.money)."""
    from core.region import money

    return money(x)


def _figures(budget, entity_id: str, start: str, end: str) -> dict:
    """Income, expenses and what's left for one business between two ISO dates, as numbers and words."""
    income = budget.total_income(start, end, entity_id=entity_id)
    spent = budget.total_expenses(start, end, entity_id=entity_id)
    net = income - spent
    return {"income": _money(income), "expenses": _money(spent), "net": _money(net), "net_value": round(net, 2),
            "income_value": round(income, 2), "expenses_value": round(spent, 2)}


def _properties(context, entity_id: str) -> list:
    """The Real Estate properties a business owns."""
    store = getattr(context, "real_estate", None)
    try:
        return [p for p in (store.all_properties() if store is not None else []) if p.entity_id == entity_id]
    except Exception:  # noqa: BLE001 - no properties to read
        log.exception("Businesses: properties failed")
        return []


def _book_rows(context, entity_id: str, today: date) -> dict:
    """A business's orders and quotes as Orders & Quotes shows them (core.web_business.business_page, its own only)."""
    from core.web_business import business_page

    try:
        page = business_page(context, today, business=entity_id or "none")
    except Exception:  # noqa: BLE001 - the book unreadable: no rows
        log.exception("Businesses: orders and quotes failed")
        return {"orders": [], "quotes": []}
    if not page.get("available"):
        return {"orders": [], "quotes": []}
    return {"orders": page["orders"], "quotes": page["quotes"]}


def _apps(has_properties: bool, has_book: bool, entity_id: str) -> list[dict]:
    """The apps a business uses, each opening on its part: Real Estate for its properties, Orders & Quotes (its own)
    and the Workshop for one that takes orders."""
    out = []
    if has_properties:
        out.append({"id": "real_estate", "name": "Real Estate", "page": "real-estate.html"})
    if has_book:
        out += [{"id": "business", "name": "Orders & Quotes", "page": f"business.html?business={entity_id}"},
                {"id": "workshop", "name": "Workshop", "page": "workshop.html"}]
    return out


def businesses_page(context, today: Optional[date] = None) -> dict:
    """The subdashboard: {available, businesses: [{id, name, type, month, year, owes, properties, open_orders,
    open_quotes, apps, page}], totals (this month's net across them, open orders), unsorted: orders and quotes with no
    business yet, as_of}; not available without Money."""
    budget = getattr(context, "budget", None)
    if budget is None:
        return {"available": False}
    today = today or date.today()
    month = (today.replace(day=1).isoformat(), today.isoformat())
    year = (today.replace(month=1, day=1).isoformat(), today.isoformat())
    book = getattr(context, "business", None)
    out = []
    for e in budget.all_business_entities():
        props = _properties(context, e.entity_id)
        orders = [o for o in (book.orders if book is not None else []) if o.entity_id == e.entity_id]
        quotes = [q for q in (book.quotes if book is not None else []) if q.entity_id == e.entity_id]
        out.append({
            "id": e.entity_id, "name": e.name, "type": e.entity_type, "page": f"biz.html?id={e.entity_id}",
            "month": _figures(budget, e.entity_id, *month), "year": _figures(budget, e.entity_id, *year),
            "owes": _money(budget.total_debt_balance(e.entity_id)), "owes_value": round(budget.total_debt_balance(e.entity_id), 2),
            "properties": len(props),
            "open_orders": sum(1 for o in orders if o.status not in ("Delivered", "Cancelled")),
            "open_quotes": sum(1 for q in quotes if q.status in ("Draft", "Sent")),
            "apps": _apps(bool(props), bool(orders or quotes), e.entity_id)})
    unsorted = sum(1 for r in (book.orders + book.quotes if book is not None else []) if not r.entity_id)
    month_net = sum(b["month"]["net_value"] for b in out)
    return {"available": True, "as_of": today.isoformat(), "businesses": out,
            "totals": {"month_net": _money(month_net), "month_net_value": round(month_net, 2),
                       "open_orders": sum(b["open_orders"] for b in out)},
            "unsorted": {"count": unsorted, "page": "business.html?business=none"} if unsorted else None}


def business_dashboard(context, entity_id: str, today: Optional[date] = None) -> Optional[dict]:
    """One business's own dashboard: {id, name, type, notes, month, year, spending: its biggest expense categories this
    year, income, expenses (the latest of each), properties, orders, quotes, debts, apps}; None for an unknown business
    or without Money."""
    budget = getattr(context, "budget", None)
    entity = budget.get_business_entity(entity_id) if budget is not None and entity_id else None
    if entity is None:
        return None
    today = today or date.today()
    start_year = today.replace(month=1, day=1).isoformat()
    by_cat = budget.total_expenses_by_category(start_year, today.isoformat(), entity_id=entity_id)
    line = lambda r: {"date": r.date, "what": r.description or r.category, "category": r.category,  # noqa: E731
                      "amount": _money(r.amount)}
    income = sorted((i for i in budget.all_income() if i.entity_id == entity_id), key=lambda r: r.date, reverse=True)
    spent = sorted((e for e in budget.all_expenses() if e.entity_id == entity_id), key=lambda r: r.date, reverse=True)
    props = _properties(context, entity_id)
    rows = _book_rows(context, entity_id, today)
    debts = budget.all_debts(entity_id)
    return {
        "id": entity.entity_id, "name": entity.name, "type": entity.entity_type, "notes": entity.notes,
        "month": _figures(budget, entity_id, today.replace(day=1).isoformat(), today.isoformat()),
        "year": _figures(budget, entity_id, start_year, today.isoformat()),
        "spending": [{"category": c, "amount": _money(v)} for c, v in sorted(by_cat.items(), key=lambda kv: -kv[1])[:5]],
        "income": [line(r) for r in income[:RECENT]], "expenses": [line(r) for r in spent[:RECENT]],
        "properties": [{"id": p.property_id, "name": p.name, "type": p.property_type, "status": p.status,
                        "rent": _money(p.monthly_rent) if p.monthly_rent else "", "page": "real-estate.html"}
                       for p in props],
        "orders": rows["orders"], "quotes": rows["quotes"],
        "debts": [{"name": d.name, "balance": _money(d.balance)} for d in debts],
        "apps": _apps(bool(props), bool(rows["orders"] or rows["quotes"]), entity_id),
        "orders_page": f"business.html?business={entity_id}",
    }
