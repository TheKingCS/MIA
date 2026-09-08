"""
tests.test_budget_nudges
===========================

Unit tests for core.budget_nudges — no Qt, no manager instances, same
shape as tests/test_daily_occasions.py.
"""

from __future__ import annotations

from datetime import date

from core.budget_manager import Bill, BudgetTarget, IncomeSource
from core.budget_nudges import (
    budget_overage_summary,
    build_nudge_message,
    overdue_bills_summary,
    upcoming_bills_summary,
    upcoming_income_summary,
)


def _bill(name="Electric", amount=120.0, due_date="2026-09-07", last_paid_date=None):
    return Bill(bill_id="b1", name=name, amount=amount, due_date=due_date, last_paid_date=last_paid_date)


def _income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-07"):
    return IncomeSource(source_id="s1", name=name, expected_amount=expected_amount, next_date=next_date)


# ------------------------------------------------------------------
# overdue_bills_summary
# ------------------------------------------------------------------

def test_overdue_bills_summary_none_when_nothing_overdue():
    bills = [_bill(due_date="2026-09-10")]
    assert overdue_bills_summary(bills, date(2026, 9, 7)) is None


def test_overdue_bills_summary_single_bill():
    bills = [_bill(name="Electric", due_date="2026-08-01")]
    assert overdue_bills_summary(bills, date(2026, 9, 7)) == "'Electric' is overdue."


def test_overdue_bills_summary_multiple_bills():
    bills = [_bill(name="Electric", due_date="2026-08-01"), Bill(bill_id="b2", name="Water", amount=50.0, due_date="2026-08-15")]
    result = overdue_bills_summary(bills, date(2026, 9, 7))
    assert result == "2 bills are overdue: Electric, Water."


# ------------------------------------------------------------------
# upcoming_bills_summary
# ------------------------------------------------------------------

def test_upcoming_bills_summary_excludes_overdue():
    bills = [_bill(due_date="2026-08-01")]  # overdue, not upcoming
    assert upcoming_bills_summary(bills, date(2026, 9, 7)) is None


def test_upcoming_bills_summary_includes_due_today_and_soon():
    bills = [_bill(name="Electric", amount=120.0, due_date="2026-09-07")]
    result = upcoming_bills_summary(bills, date(2026, 9, 7))
    assert result == "Due within 7 days: Electric ($120.00)."


def test_upcoming_bills_summary_none_outside_window():
    bills = [_bill(due_date="2026-09-20")]
    assert upcoming_bills_summary(bills, date(2026, 9, 7)) is None


# ------------------------------------------------------------------
# upcoming_income_summary
# ------------------------------------------------------------------

def test_upcoming_income_summary_names_the_soonest_source():
    sources = [
        _income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-10"),
        _income_source(name="Rental Income", expected_amount=1500.0, next_date="2026-09-08"),
    ]
    result = upcoming_income_summary(sources, date(2026, 9, 7))
    assert result == "Next expected income: Rental Income, $1500.00 in 1 days."


def test_upcoming_income_summary_due_today_says_today():
    sources = [_income_source(next_date="2026-09-07")]
    assert upcoming_income_summary(sources, date(2026, 9, 7)) == "Next expected income: Paycheck, $2400.00 today."


def test_upcoming_income_summary_none_outside_window():
    sources = [_income_source(next_date="2026-09-20")]
    assert upcoming_income_summary(sources, date(2026, 9, 7)) is None


# ------------------------------------------------------------------
# budget_overage_summary
# ------------------------------------------------------------------

def test_budget_overage_summary_none_when_under_target():
    targets = [BudgetTarget(category="Groceries", monthly_amount=400.0)]
    assert budget_overage_summary(targets, {"Groceries": 350.0}) is None


def test_budget_overage_summary_reports_only_over_categories():
    targets = [
        BudgetTarget(category="Groceries", monthly_amount=400.0),
        BudgetTarget(category="Utilities", monthly_amount=150.0),
    ]
    actual = {"Groceries": 450.0, "Utilities": 100.0}
    result = budget_overage_summary(targets, actual)
    assert result == "Over budget this month: Groceries ($450.00 of $400.00 planned)."


def test_budget_overage_summary_none_when_category_untouched():
    targets = [BudgetTarget(category="Groceries", monthly_amount=400.0)]
    assert budget_overage_summary(targets, {}) is None


# ------------------------------------------------------------------
# build_nudge_message
# ------------------------------------------------------------------

def test_build_nudge_message_none_when_everything_is_quiet():
    result = build_nudge_message([], [], [], {}, date(2026, 9, 7))
    assert result is None


def test_build_nudge_message_joins_multiple_real_findings():
    bills = [_bill(name="Electric", due_date="2026-08-01")]  # overdue
    sources = [_income_source(next_date="2026-09-07")]  # due today
    result = build_nudge_message(bills, sources, [], {}, date(2026, 9, 7))
    assert "'Electric' is overdue." in result
    assert "Next expected income: Paycheck, $2400.00 today." in result
