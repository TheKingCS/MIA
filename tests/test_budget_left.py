"""
tests.test_budget_left
========================

"How much is left in my grocery budget?" by voice (budget_left): the Money page's own budget targets, spent and left
for the one he named or all, over a target said plainly, an unknown one named with the ones he has, and none set yet
said with how to set one.
"""

import core.finance_summary as fs
from core.assistant_domain_actions import _action_budget_left as left

SUMMARY = {"available": True, "month": {"label": "November 2026"}, "budget_targets": [
    {"category": "Gas", "budget": 200.0, "spent": 230.0}, {"category": "Groceries", "budget": 400.0, "spent": 250.0}]}


def test_the_named_budget_says_whats_left(monkeypatch):
    monkeypatch.setattr(fs, "build_finance_summary", lambda context: SUMMARY)
    assert left(None, {"category": "groceries"}) == "November 2026: Groceries: $250.00 of $400.00, $150.00 left."


def test_all_of_them_with_one_over(monkeypatch):
    monkeypatch.setattr(fs, "build_finance_summary", lambda context: SUMMARY)
    said = left(None, {})
    assert "Gas: $230.00 of $200.00, $30.00 over" in said and "Groceries" in said


def test_an_unknown_or_none_set_says_so(monkeypatch):
    monkeypatch.setattr(fs, "build_finance_summary", lambda context: SUMMARY)
    assert left(None, {"category": "boats"}).startswith("I don't have a budget for boats. Your budgets are: Gas")
    monkeypatch.setattr(fs, "build_finance_summary", lambda context: {"available": True, "budget_targets": []})
    assert left(None, {}).startswith("You haven't set any monthly budgets yet.")
