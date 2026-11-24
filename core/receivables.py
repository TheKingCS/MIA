"""
core.receivables
==================

Who owes him money (Jarvis brainstorm, round 3: his businesses). "Who owes me?" (`say`) reads his orders
(core/business_book.py) for what's still unpaid: each order's price less the payments taken on it (the workshop
ledger's revenue entries, as `order.pay` records them), never a cancelled one, oldest due date first, the overdue ones
named: a delivered one still unpaid is the one to chase; one past its date but not delivered yet is his to finish,
never called money overdue (its balance is due on delivery, as the Business page reads a due date), and the total.
What's been paid is `business_actions._paid`, the same as the invoice and the Business page: its payments, and a
sale recorded on its build.

How: `owed(orders, paid_of, today)` is pure: it takes the orders and a function giving what's been paid on each, so
the arithmetic is code's and the model only phrases it. An order with no price set isn't counted (there's nothing to
owe yet) and is named so he can price it. A delivered order with money still on it is the one to chase first, so it
says so. Nothing here changes a record; the next step it offers is the invoice draft he already has (draft_invoice).
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Optional



def owed(orders: list, paid_of: Callable, today: date, customers: Optional[dict] = None) -> dict:
    """Pure logic. {"lines": [{title, customer, left, due, days_late, delivered}], "total", "unpriced": [titles]}:
    every order not cancelled with money still on it, oldest due date first (no due date last)."""
    customers = customers or {}
    lines, unpriced = [], []
    for order in orders:
        if getattr(order, "status", "") == "Cancelled":
            continue
        price = float(getattr(order, "price", 0) or 0)
        if price <= 0:
            if getattr(order, "status", "") != "Delivered":
                unpriced.append(order.title)
            continue
        left = round(price - float(paid_of(order) or 0), 2)
        if left <= 0.005:
            continue
        due = str(getattr(order, "due_date", "") or "")[:10]
        try:
            late = (today - date.fromisoformat(due)).days if due else None
        except ValueError:
            due, late = "", None
        lines.append({"title": order.title, "customer": customers.get(getattr(order, "customer_id", ""), ""),
                      "left": left, "due": due, "days_late": late, "delivered": order.status == "Delivered"})
    lines.sort(key=lambda l: (l["due"] == "", l["due"], l["title"]))
    return {"lines": lines, "total": round(sum(l["left"] for l in lines), 2), "unpriced": unpriced}


def _line(l: dict, money) -> str:
    """Pure logic. One order in words: who, what, how much, and where it stands: delivered and unpaid (with days past
    its due date), not delivered yet past its date, due today, or its due date."""
    who = f"{l['customer']}, " if l["customer"] else ""
    text = f"{who}{l['title']}: {money(l['left'])}"
    late = l["days_late"]
    if l["delivered"]:
        text += f", delivered and {late} day{'s' if late != 1 else ''} past its due date" if late and late > 0 else \
            ", delivered and still unpaid"
    elif late is not None and late > 0:
        text += f", not delivered yet (it was due {l['due']})"
    elif late == 0:
        text += ", due today"
    elif l["due"]:
        text += f", due {l['due']}"
    return text


def to_chase(lines: list) -> list:
    """Pure logic. The orders to ask payment for: delivered with money still on them, longest past due first (an
    undelivered order's balance isn't due until he delivers it)."""
    return sorted((l for l in lines if l["delivered"]), key=lambda l: -(l["days_late"] or 0))


def say(context, today: Optional[date] = None) -> str:
    """For "who owes me?": the total, then each unpaid order oldest due first (a delivered one said as delivered and
    unpaid; one past its date and not delivered yet said as that, never as money overdue), the delivered one longest
    past due named to chase (`to_chase`), and orders with no price yet ("and N more" past three)."""
    from core.business_actions import _paid
    from core.region import money

    today = today or date.today()
    book = getattr(context, "business", None)
    if book is None:
        return "There are no orders here yet."
    customers = {c.customer_id: c.name for c in getattr(book, "customers", [])}
    got = owed(list(book.orders), lambda o: _paid(context, o), today, customers)
    fmt = lambda a: money(a, ",.2f")  # noqa: E731
    if not got["lines"]:
        said = "Nobody owes you anything on your orders right now."
    else:
        n = len(got["lines"])
        said = (f"{fmt(got['total'])} is owed on {n} order{'s' if n != 1 else ''}: "
                + "; ".join(_line(l, fmt) for l in got["lines"]) + ".")
        chase = to_chase(got["lines"])
        if chase:
            said += f" Chase {chase[0]['title']} first; I can draft its invoice if you'd like."
    if got["unpriced"]:
        more = len(got["unpriced"]) - 3
        said += " No price set yet on " + ", ".join(got["unpriced"][:3]) + (f" and {more} more" if more > 0 else "") + "."
    return said
