"""
tests.test_receivables
========================

Who owes him money (core/receivables.py): each order's price less what's been paid, never a cancelled or paid-up
one, oldest due first with the overdue days, the delivered-but-unpaid named as the one to chase, orders with no
price said apart, and nothing owed said plainly.
"""

from datetime import date
from types import SimpleNamespace

from core import receivables as rv

TODAY = date(2026, 11, 24)


def _order(title, price, status="Open", due="", customer="", oid=None):
    """An order as the business book keeps one."""
    return SimpleNamespace(order_id=oid or title, title=title, price=price, status=status, due_date=due,
                           customer_id=customer)


def test_whats_left_on_each_order_oldest_due_first():
    orders = [_order("Cedar chest", 900, due="2026-12-10", customer="c1"),
              _order("Bench", 300, status="Delivered", due="2026-11-14", customer="c2"),
              _order("Shelf", 150, due="2026-11-20"), _order("Table", 1200, status="Cancelled"),
              _order("Sign", 80), _order("Stool", 0)]
    paid = {"Cedar chest": 300, "Shelf": 150}
    got = rv.owed(orders, lambda o: paid.get(o.order_id, 0), TODAY, {"c1": "Dana", "c2": "Lee"})
    assert [l["title"] for l in got["lines"]] == ["Bench", "Cedar chest", "Sign"]
    assert got["total"] == 980 and got["unpriced"] == ["Stool"]
    assert got["lines"][0]["days_late"] == 10 and got["lines"][0]["delivered"]


def test_the_answer_names_who_and_what_to_chase(monkeypatch):
    import core.business_actions as ba

    monkeypatch.setattr(ba, "_paid", lambda context, order: 0)
    book = SimpleNamespace(orders=[_order("Bench", 300, status="Delivered", due="2026-11-14", customer="c2")],
                           customers=[SimpleNamespace(customer_id="c2", name="Lee")])
    said = rv.say(SimpleNamespace(business=book), TODAY)
    assert "is owed on 1 order: Lee, Bench:" in said and "10 days overdue (delivered, still unpaid)" in said
    assert "Chase Bench first" in said


def test_nothing_owed_is_said_plainly(monkeypatch):
    import core.business_actions as ba

    monkeypatch.setattr(ba, "_paid", lambda context, order: order.price)
    book = SimpleNamespace(orders=[_order("Bench", 300)], customers=[])
    assert rv.say(SimpleNamespace(business=book), TODAY) == "Nobody owes you anything on your orders right now."
