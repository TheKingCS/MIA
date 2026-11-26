"""
tests.test_month_vs
=====================

This month against last (core/money_periods.compare, brainstorm round 19): to the same day, last month's whole
beside it, the categories that moved most, or one category's own.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, money_periods


def _budget(rows):
    """A budget whose expenses are (day, category, amount) rows."""
    def by(a, b, entity_id=None):
        """Spending per category between two ISO days."""
        out = {}
        for day, cat, amount in rows:
            if a <= day <= b:
                out[cat] = out.get(cat, 0) + amount
        return out
    return SimpleNamespace(total_expenses_by_category=by)


ROWS = [("2026-10-05", "Groceries", 100), ("2026-10-20", "Groceries", 150), ("2026-10-10", "Transportation", 40),
        ("2026-11-03", "Groceries", 220), ("2026-11-12", "Transportation", 30)]


def test_to_the_same_day_with_what_moved():
    said = money_periods.compare(SimpleNamespace(budget=_budget(ROWS)), today=date(2026, 11, 15))
    assert said.startswith("$110.00 more: $250.00 this month so far, against $140.00 by October 15.")
    assert "All of October came to $290.00." in said and "Moved most: Groceries (up $120.00)" in said
    one = money_periods.compare(SimpleNamespace(budget=_budget(ROWS)), "Transportation", date(2026, 11, 15))
    assert one.startswith("$10.00 less: $30.00 on Transportation this month so far")


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(money_periods, "compare", lambda c, cat="", t=None: f"compare[{cat}]")
    for words in ("Did I spend more this month than last month?", "am I spending more than last month?",
                  "how does my spending this month compare to last month?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "compare[]", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "did I spend more on groceries this month than last "
                                                             "month?") == "compare[Groceries]"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "groceries this month vs last month?") == "compare[Groceries]"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "spending this month vs last month") == "compare[]"
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "the kids this month vs last month") is None
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "did I make more this month than last month?") != "compare[]"
