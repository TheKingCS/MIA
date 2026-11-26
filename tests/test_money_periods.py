"""
tests.test_money_periods
==========================

Money over a period in code (core/money_periods.py, the live sweep 2026-11-26): spending in a period with its top
categories, the biggest category, the shop's month; and plan answers never say "the fact sheet".
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, money_periods, question_plans

TODAY = date(2026, 11, 26)


def _budget(by):
    calls = []
    return SimpleNamespace(calls=calls, total_expenses_by_category=lambda s, e, entity_id=None: calls.append((s, e)) or by)


def test_the_periods_are_read():
    assert money_periods.period("last month", TODAY)[:2] == (date(2026, 10, 1), date(2026, 10, 31))
    assert money_periods.period("this year", TODAY)[:2] == (date(2026, 1, 1), TODAY)
    assert money_periods.period("last week", TODAY)[:2] == (date(2026, 11, 16), date(2026, 11, 22))
    assert money_periods.period("in december", TODAY)[:2] == (date(2025, 12, 1), date(2025, 12, 31))
    assert money_periods.period("lately", TODAY) is None
    assert money_periods.period("for march 2025", TODAY)[2] == "March 2025"
    assert money_periods.period("in december", TODAY)[2] == "December 2025"
    assert money_periods.only_period(" last month") and money_periods.only_period(" so far this year")
    for rest in (" at Costco last month", " last month on gas", " this month vs last month", " in the shop this month"):
        assert not money_periods.only_period(rest), rest


def test_spending_last_month_with_its_top_categories():
    budget = _budget({"Groceries": 400.0, "Utilities": 150.0, "Fuel": 90.0, "Other": 10.0})
    said = money_periods.spent(SimpleNamespace(budget=budget), "last month", TODAY)
    assert said == "You spent $650.00 last month (October). The most: Groceries $400.00, Utilities $150.00, Fuel $90.00."
    assert budget.calls == [("2026-10-01", "2026-10-31")]


def test_the_biggest_category_and_the_shop():
    said = money_periods.biggest(SimpleNamespace(budget=_budget({"Groceries": 300.0, "Fuel": 100.0})), "", TODAY)
    assert said == ("Your biggest category this year is Groceries: $300.00, 75% of the $400.00 you spent. Next: Fuel "
                    "($100.00).")
    ledger = SimpleNamespace(total_revenue=lambda s, e: 240.0, total_expenses=lambda s, e: 60.0)
    assert money_periods.shop_made(SimpleNamespace(ledger=ledger), "", TODAY) == \
        "The shop this month: $240.00 in sales, $60.00 in costs, $180.00 profit."


def test_the_words_reach_them(monkeypatch):
    monkeypatch.setattr(money_periods, "spent", lambda c, w, t=None: "spent")
    monkeypatch.setattr(money_periods, "biggest", lambda c, w, t=None: "biggest")
    monkeypatch.setattr(money_periods, "shop_made", lambda c, w, t=None: "shop")
    ask = lambda w: assistant_turn._own_tool_reply(SimpleNamespace(), w)  # noqa: E731
    assert ask("How much did I spend last month?") == "spent"
    assert ask("What's my biggest expense category this year?") == "biggest"
    assert ask("where does my money go") == "biggest"
    assert ask("What did I make from the shop this month?") == "shop"
    assert ask("How much did I spend on groceries this month?") != "spent", "a category is its own route"
    for words in ("how much did I spend at Costco last month", "what did I spend this month compared to last month",
                  "where is my money going to come from", "How's the shop doing on orders?",
                  "what's my top expense for the greenhouse build"):
        assert ask(words) not in ("spent", "biggest", "shop"), words


def test_a_plan_answer_never_says_the_fact_sheet():
    assert question_plans.without_sheet_words("The fact sheet says to put extra toward #1, the card.") == \
        "Put extra toward #1, the card."
    assert question_plans.without_sheet_words("The fact sheet doesn't mention customers.") == \
        "I don't have customers."
    for kept in ("The balance sheet doesn't show a loss.", "Bake on the sheet pan.", "It only shows up on Tuesdays.",
                 "Use a jig, e.g. it holds the board."):
        assert question_plans.without_sheet_words(kept) == kept, kept


def test_affording_a_purchase_from_this_months_records(monkeypatch):
    from core import money_ahead

    monkeypatch.setattr(money_ahead, "_records", lambda c: ([], [], []))
    monkeypatch.setattr(money_ahead, "flows", lambda *a, **k: [{"amount": -120.0, "what": "Electric", "day": TODAY,
                                                               "note": "overdue"}])
    broke = SimpleNamespace(budget=SimpleNamespace(total_income=lambda s, e: 0.0,
                                                   total_expenses_by_category=lambda s, e, entity_id=None: {}))
    said = money_periods.afford(broke, 500.0, TODAY)
    assert said.startswith("I can't tell from your records: no income is logged this month")
    assert "Not marked paid yet: Electric (each counted once)." in said, "an overdue bill named once"
    paid = SimpleNamespace(budget=SimpleNamespace(total_income=lambda s, e: 2000.0,
                                                  total_expenses_by_category=lambda s, e, entity_id=None: {"Food": 600.0}))
    assert money_periods.afford(paid, 500.0, TODAY).startswith("From what's logged, $500.00 fits: $1,280.00 is left")
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "Can I afford a $500 purchase this month?") is not None
