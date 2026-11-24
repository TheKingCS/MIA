"""
core.best_customers
=====================

Who his best customers are, and who's gone quiet (Jarvis brainstorm round 7, 2026-11-24; his businesses): "who are
my best customers?", "which customers haven't ordered in a while?". The customers, their orders and the ledger read
together.

**How.** Each customer's orders (not cancelled): how many, what's been paid on them (the order page's count: its
payments, and sales on its builds; each ledger entry credited to one order only, the oldest), and the newest order's
date. Ranked by what they've paid, then by orders, all time. A customer who has ordered at least twice, whose newest
order is older than `QUIET_DAYS` and who has nothing still open, building or ready is named as gone quiet, a regular
worth a word. Shares are of what's been paid on orders (market-day sales aren't orders). Never guesses: a customer
with no orders isn't ranked. Read-only.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

QUIET_DAYS = 180  # a regular not heard from in half a year
SHOW = 5


def ranked(context, today: Optional[date] = None) -> list[dict]:
    """Every customer with orders: {name, orders, paid (each ledger entry once), last (YYYY-MM-DD), quiet (none open)},
    best first; [] without the book."""
    book = getattr(context, "business", None)
    if book is None:
        return []
    today = today or date.today()
    ledger = getattr(context, "ledger", None)
    entries = ledger.all_revenue() if ledger is not None else []
    credited: dict = {}  # each ledger entry: the one order it counts for (the oldest that names it)
    for order in sorted(book.orders, key=lambda o: o.created_at or ""):
        if order.status == "Cancelled":
            continue
        jobs = set(order.job_ids or [])
        for r in entries:
            if r.entry_id in (order.payment_ids or []) or (jobs and r.job_id in jobs):
                credited.setdefault(r.entry_id, (order.order_id, float(r.amount or 0)))
    paid_on: dict = {}
    for order_id, amount in credited.values():
        paid_on[order_id] = paid_on.get(order_id, 0.0) + amount
    out = []
    for customer in book.customers:
        orders = [o for o in book.orders if o.customer_id == customer.customer_id and o.status != "Cancelled"]
        if not orders:
            continue
        last = max((o.created_at or "")[:10] for o in orders)
        paid = round(sum(paid_on.get(o.order_id, 0.0) for o in orders), 2)
        still_open = any(o.status in ("Open", "Building", "Ready") for o in orders)
        quiet = (len(orders) >= 2 and bool(last) and not still_open
                 and last < (today - timedelta(days=QUIET_DAYS)).isoformat())
        out.append({"name": customer.name, "orders": len(orders), "paid": paid, "last": last, "quiet": quiet})
    return sorted(out, key=lambda c: (-c["paid"], -c["orders"], c["name"]))


def say(context, today: Optional[date] = None) -> str:
    """The best few (`SHOW`) by what they've paid on orders, all time, their share of that, and the regulars gone
    quiet."""
    from core.region import money

    if getattr(context, "business", None) is None:
        return "The business book isn't on this MIA, so I can't rank your customers."
    rows = ranked(context, today)
    if not rows:
        return "No customer has an order yet, so there's no one to rank. Orders made for a customer count here."
    total = sum(r["paid"] for r in rows)
    parts = [f"{r['name']}: {money(r['paid'])} paid on {r['orders']} order{'s' if r['orders'] != 1 else ''}"
             + (f" ({round(r['paid'] / total * 100)}%)" if total else "") for r in rows[:SHOW]]
    out = ("Your customers by what they've paid on orders, all time (the share is of what's been paid on orders; "
           "market-day sales aren't orders): " + "; ".join(parts) + ".")
    quiet = [r for r in rows if r["quiet"]]
    if quiet:
        out += (" Gone quiet (two or more orders, none in six months, nothing open): "
                + ", ".join(f"{r['name']} (last {r['last']})" for r in quiet[:SHOW]) + ". Maybe worth a word.")
    return out
