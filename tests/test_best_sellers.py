"""
tests.test_best_sellers
=========================

"What's my best-selling product?" by units sold from the ledger's product sales (core/money_periods.best_sellers,
the live sweep 2026-11-26: it had been judged by what's in stock).
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, money_periods


def test_by_units_sold_never_stock():
    sales = [SimpleNamespace(product_id="b", amount=50, quantity_sold=2, date="2026-10-02"),
             SimpleNamespace(product_id="c", amount=120, quantity_sold=3, date="2026-11-01"),
             SimpleNamespace(product_id="b", amount=25, quantity_sold=1, date="2026-11-20"),
             SimpleNamespace(product_id="", amount=500, quantity_sold=0, date="2026-11-20"),
             SimpleNamespace(product_id="c", amount=40, quantity_sold=1, date="2025-12-01"),
             SimpleNamespace(product_id="z", amount=80, quantity_sold=0, date="2026-11-21")]
    names = {"b": "Birdhouse", "c": "Cutting Board"}
    context = SimpleNamespace(ledger=SimpleNamespace(all_revenue=lambda: sales),
                              products=SimpleNamespace(get_product=lambda pid: SimpleNamespace(name=names[pid])))
    said = money_periods.best_sellers(context, "", date(2026, 11, 26))
    assert said == "Your best seller this year is Cutting Board: 3 sold, $120.00. Then Birdhouse: 3 sold, $75.00."
    none = money_periods.best_sellers(SimpleNamespace(ledger=SimpleNamespace(all_revenue=lambda: [])), "",
                                      date(2026, 11, 26))
    assert none.startswith("No sales tied to a product this year")
    october = money_periods.best_sellers(context, "in October", date(2026, 11, 26))
    assert october == "Your best seller in October is Birdhouse: 2 sold, $50.00."


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(money_periods, "best_sellers", lambda c, w="", t=None: f"best[{w.strip()}]")
    for words, when in (("What's my best-selling product?", ""), ("what sells best?", ""),
                        ("what are my top sellers this month?", "this month"), ("what sold best in March?", "in March")):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == f"best[{when}]", words
    for words in ("what is my best seller in 2025?", "what sells best in town?"):
        assert not str(assistant_turn._own_tool_reply(SimpleNamespace(), words) or "").startswith("best["), words
