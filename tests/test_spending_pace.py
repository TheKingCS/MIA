"""
tests.test_spending_pace
==========================

"Am I spending more on groceries than usual?" (core/spending_pace.py): his words read to a category, this month at its
pace against his usual month, the early days said as too early, and the ones running over said when none is named.
"""

from datetime import date

from core import spending_pace as sp
from tests.engine_world import build_world

CATS = ["Groceries", "Transportation", "Entertainment", "Utilities"]


def test_his_words_name_a_category():
    """Food and groceries are Groceries, gas is Transportation, eating out is Entertainment; nothing named is None."""
    assert sp.category_of("am I spending more on food than usual", CATS) == "Groceries"
    assert sp.category_of("how's my gas spending", CATS) == "Transportation"
    assert sp.category_of("eating out this month", CATS) == "Entertainment"
    assert sp.category_of("am I spending more than usual", CATS) is None


def test_the_pace_is_the_whole_month_at_this_rate():
    """$100 by the 10th of a 30-day month is on pace for $300."""
    assert sp.pace(100.0, date(2026, 11, 10)) == 300.0


def test_groceries_against_his_usual_and_the_ones_over(tmp_path, monkeypatch):
    """Three months of $300 groceries; $200 by the 15th is on pace for $400, $100 over; asked in general, groceries is
    named and gas, on pace, isn't."""
    world = build_world(tmp_path, monkeypatch)
    for month in ("2026-08", "2026-09", "2026-10"):
        world.budget.add_expense(300.0, category="Groceries", description="Groceries", date=f"{month}-12")
        world.budget.add_expense(100.0, category="Transportation", description="Gas", date=f"{month}-12")
    world.budget.add_expense(200.0, category="Groceries", description="Groceries", date="2026-11-10")
    world.budget.add_expense(50.0, category="Transportation", description="Gas", date="2026-11-10")
    today = date(2026, 11, 15)
    said = sp.say(world, "groceries", today)
    assert said.startswith("Groceries: $200.00 so far, on pace for $400.00 this month, $100.00 over your usual")
    general = sp.say(world, "", today)
    assert general.startswith("Groceries:") and "Transportation" not in general
    assert "too early" in sp.say(world, "groceries", date(2026, 11, 3))
