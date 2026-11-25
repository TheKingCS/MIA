"""
tests.test_make_next
======================

"What should I make next?" (core/make_next.py): products that sold in the last 90 days, the ones under a month of
stock first, best per hour first among them; nothing that hasn't sold is suggested.
"""

from datetime import date
from types import SimpleNamespace

from core import make_next


def _product(pid, name, stock, price):
    """A product like the workshop's."""
    return SimpleNamespace(product_id=pid, name=name, quantity_in_stock=stock, base_price=price)


def _sale(pid, qty, day):
    """A sale of a product."""
    return SimpleNamespace(product_id=pid, quantity_sold=qty, date=day, amount=10.0)


def test_the_low_and_well_paid_come_first_and_the_unsold_never(monkeypatch):
    """Boards (2 left, 12 sold in 90 days, $30 an hour) before coasters (0 left, $10 an hour); signs (plenty) aren't
    low; a stool that never sold isn't listed."""
    from core import product_pricing

    products = [_product("b", "Cutting board", 2, 45), _product("c", "Coaster set", 0, 20),
                _product("s", "Sign", 30, 60), _product("t", "Stool", 0, 90)]
    sales = [_sale("b", 4, "2026-11-01"), _sale("b", 8, "2026-10-01"), _sale("c", 6, "2026-11-10"),
             _sale("s", 3, "2026-10-20")]
    monkeypatch.setattr(product_pricing, "per_piece", lambda context: {
        "b": {"materials": 15.0, "hours": 1.0, "timed": True}, "c": {"materials": 10.0, "hours": 1.0, "timed": True}})
    context = SimpleNamespace(products=SimpleNamespace(all_products=lambda: products),
                              ledger=SimpleNamespace(all_revenue=lambda: sales), config=None)
    rows = make_next.ranked(context, date(2026, 11, 24))
    assert [r["name"] for r in rows] == ["Cutting board", "Coaster set", "Sign"]
    assert rows[0]["low"] and rows[0]["per_month"] == 4.0 and rows[0]["per_hour"] == 30.0
    assert not rows[2]["low"]
    said = make_next.say(context, date(2026, 11, 24))
    assert said.startswith("Make these next: Cutting board: you sell about 4 a month, 2 left")
    assert "Coaster set" in said and "none left" in said and "Sign" not in said and "Stool" not in said


def test_no_sales_says_how_to_start():
    """No sales in the window: how to log them."""
    context = SimpleNamespace(products=SimpleNamespace(all_products=lambda: []),
                              ledger=SimpleNamespace(all_revenue=lambda: []), config=None)
    assert make_next.say(context).startswith("I don't see sales of your products")
