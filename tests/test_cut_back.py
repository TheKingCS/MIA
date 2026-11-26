"""
tests.test_cut_back
=====================

"Where can I cut back?" from his own records (core/money_periods.cut_back, the money-stress conversation check
2026-11-26): what he chooses this month against his usual, then his recurring bills, never a fixed cost.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, money_periods


def test_chosen_spending_and_recurring_bills():
    def by(a, b, entity_id=None):
        """Groceries and rent each month."""
        return {"Groceries": 300.0, "Mortgage/Rent": 900.0, "Entertainment": 60.0}
    bills = [SimpleNamespace(name="Netflix", amount=15.5, recurrence="monthly", category="Entertainment", entity_id=""),
             SimpleNamespace(name="Rent", amount=900, recurrence="monthly", category="Mortgage/Rent", entity_id="")]
    context = SimpleNamespace(budget=SimpleNamespace(total_expenses_by_category=by, all_bills=lambda: bills))
    said = money_periods.cut_back(context, date(2026, 11, 26))
    assert said.startswith("Where your money goes that you choose, this month: Groceries $300.00 (usually $300.00")
    assert "Netflix $15.50 monthly" in said and "Rent $" not in said and "Mortgage" not in said


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(money_periods, "cut_back", lambda c, t=None: "cuts")
    for words in ("where can I cut back?", "what can I cut?", "help me spend less", "where could we save money?"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "cuts", words
