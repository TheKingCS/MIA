"""
tests.test_utility_bills
==========================

"Why was power so high this month?" (core/utility_bills.py): energy bills found by their words (never the truck's
gas), totalled by month, said against the same month last year and the recent average, and the kWh meter when there
is one.
"""

from types import SimpleNamespace

from core import utility_bills as ub


def _e(amount, description, day, category="Utilities"):
    """An expense like the budget's."""
    return SimpleNamespace(amount=amount, description=description, date=day, category=category, payee="", notes="")


def test_bills_are_found_by_their_words_and_the_trucks_gas_never_is():
    """Electric co-op and power bill are electric; a propane fill is propane; gas for the truck is none of them."""
    assert ub.kind_of("Electric Co-op") == "electric" and ub.kind_of("power bill") == "electric"
    assert ub.kind_of("propane fill") == "propane" and ub.kind_of("gas bill") == "natural gas"
    assert ub.kind_of("gas for the truck") is None and ub.kind_of("Groceries") is None


def test_this_month_against_last_year_and_the_recent_average():
    """$182 in November against $136 last November and a $144 average; no meter is said as such."""
    expenses = [_e(182, "Electric Co-op", "2026-11-05"), _e(136, "Electric Co-op", "2025-11-04"),
                _e(140, "Electric Co-op", "2026-10-05"), _e(150, "Electric Co-op", "2026-09-05"),
                _e(142, "Electric Co-op", "2026-08-05"), _e(60, "gas for the truck", "2026-11-02", "Transportation")]
    context = SimpleNamespace(budget=SimpleNamespace(all_expenses=lambda: expenses), energy=None, config=None)
    said = ub.say(context, "electric")
    assert said.startswith("Your electric bill was $182.00 for November 2026.")
    assert "$46.00 more than November 2025 ($136.00)" in said
    assert "3-month average before it was $144.00, so it ran $38.00 over" in said
    assert "Without a kWh meter" in said


def test_no_bill_says_how_to_start():
    """Nothing logged: how to log it."""
    context = SimpleNamespace(budget=SimpleNamespace(all_expenses=lambda: []), energy=None, config=None)
    assert ub.say(context, "propane").startswith("I don't see a propane bill")
