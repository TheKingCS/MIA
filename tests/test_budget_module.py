"""
tests.test_budget_module
===========================

Unit tests for modules.budget.module's pure row formatters — no Qt
event loop needed, same shape as tests/test_maintenance_module.py.
"""

from __future__ import annotations

from datetime import date

from core.budget_manager import Bill, Debt, DebtPriority, ExpenseEntry, IncomeEntry, IncomeSource
from modules.budget.module import (
    format_bill_row,
    format_debt_row,
    format_expense_row,
    format_holding_row,
    format_income_row,
    format_income_source_row,
    month_buckets,
)


def _bill(due_date="2026-09-07", recurrence=None, last_paid_date=None, amount=120.0):
    return Bill(bill_id="b1", name="Electric", amount=amount, category="Utilities", due_date=due_date, recurrence=recurrence, last_paid_date=last_paid_date)


def _income_source(next_date="2026-09-07", recurrence=None, last_received_date=None, expected_amount=2400.0):
    return IncomeSource(
        source_id="s1",
        name="Paycheck",
        expected_amount=expected_amount,
        category="Salary",
        next_date=next_date,
        recurrence=recurrence,
        last_received_date=last_received_date,
    )


def _debt(balance=5000.0, interest_rate=24.99, promo_apr=None, promo_expires_date=None):
    return Debt(
        debt_id="d1", name="Chase Freedom", balance=balance, interest_rate=interest_rate,
        minimum_payment=100.0, debt_type="Credit Card", promo_apr=promo_apr, promo_expires_date=promo_expires_date,
    )


def test_format_debt_row_no_priority():
    debt = _debt()
    assert format_debt_row(debt, date(2026, 9, 27)) == "Chase Freedom   $5,000.00 @ 24.99% APR  [Credit Card]"


def test_format_debt_row_with_priority_includes_rank_and_reason():
    debt = _debt()
    priority = DebtPriority(debt=debt, rank=2, effective_apr=24.99, reason="Highest current APR (24.99%)")
    assert format_debt_row(debt, date(2026, 9, 27), priority) == (
        "#2  Chase Freedom   $5,000.00 @ 24.99% APR  [Credit Card]  — Highest current APR (24.99%)"
    )


def test_format_debt_row_uses_effective_promo_apr():
    debt = _debt(interest_rate=24.99, promo_apr=0.0, promo_expires_date="2026-12-01")
    assert format_debt_row(debt, date(2026, 9, 27)) == "Chase Freedom   $5,000.00 @ 0.00% APR  [Credit Card]"


def test_format_bill_row_overdue():
    bill = _bill(due_date="2026-08-01")
    assert format_bill_row(bill, date(2026, 9, 7)) == "[OVERDUE 37d]  Electric   $120.00  [Utilities]"


def test_format_bill_row_due_today():
    bill = _bill(due_date="2026-09-07")
    assert format_bill_row(bill, date(2026, 9, 7)) == "[DUE TODAY]  Electric   $120.00  [Utilities]"


def test_format_bill_row_due_in_future():
    bill = _bill(due_date="2026-09-10")
    assert format_bill_row(bill, date(2026, 9, 7)) == "[DUE IN 3d]  Electric   $120.00  [Utilities]"


def test_format_bill_row_paid_one_time():
    bill = _bill(due_date="2026-09-01", last_paid_date="2026-09-01")
    assert format_bill_row(bill, date(2026, 9, 7)) == "[PAID]  Electric   $120.00  [Utilities]"


def test_format_income_row_with_description():
    entry = IncomeEntry(entry_id="i1", amount=3000.0, category="Salary", description="September paycheck", date="2026-09-01")
    assert format_income_row(entry) == "2026-09-01   $3000.00  [Salary]  September paycheck"


def test_format_income_row_without_description():
    entry = IncomeEntry(entry_id="i1", amount=1500.0, category="Rental Income", date="2026-09-01")
    assert format_income_row(entry) == "2026-09-01   $1500.00  [Rental Income]"


def test_format_expense_row_with_description():
    entry = ExpenseEntry(entry_id="e1", amount=85.5, category="Groceries", description="Weekly shop", date="2026-09-05")
    assert format_expense_row(entry) == "2026-09-05   $85.50  [Groceries]  Weekly shop"


def test_format_holding_row_with_ticker_and_quantity():
    holding = {"security_name": "Apple Inc.", "ticker_symbol": "AAPL", "quantity": 10.0, "institution_value": 1500.0}
    assert format_holding_row(holding) == "Apple Inc. (AAPL)   10 sh  —  $1,500.00"


def test_format_holding_row_without_ticker():
    holding = {"security_name": "Private Fund X", "quantity": 3.0, "institution_value": 900.0}
    row = format_holding_row(holding)
    assert row.startswith("Private Fund X   ")
    assert "(" not in row


def test_format_holding_row_without_quantity_or_value():
    holding = {"security_name": "Mystery Security"}
    assert format_holding_row(holding) == "Mystery Security   value unknown"


def test_format_income_source_row_overdue():
    source = _income_source(next_date="2026-08-01")
    assert format_income_source_row(source, date(2026, 9, 7)) == "[OVERDUE 37d]  Paycheck   $2400.00  [Salary]"


def test_format_income_source_row_due_today():
    source = _income_source(next_date="2026-09-07")
    assert format_income_source_row(source, date(2026, 9, 7)) == "[DUE TODAY]  Paycheck   $2400.00  [Salary]"


def test_format_income_source_row_due_in_future():
    source = _income_source(next_date="2026-09-10")
    assert format_income_source_row(source, date(2026, 9, 7)) == "[DUE IN 3d]  Paycheck   $2400.00  [Salary]"


def test_format_income_source_row_no_schedule_after_one_time_received():
    source = _income_source(next_date="2026-09-01", last_received_date="2026-09-01")
    assert format_income_source_row(source, date(2026, 9, 7)) == "[NO SCHEDULE]  Paycheck   $2400.00  [Salary]"


# ------------------------------------------------------------------
# month_buckets — pure trend-view helper
# ------------------------------------------------------------------

def test_month_buckets_returns_requested_count():
    buckets = month_buckets(date(2026, 9, 9), count=12)
    assert len(buckets) == 12


def test_month_buckets_oldest_first_ending_at_todays_month():
    buckets = month_buckets(date(2026, 9, 9), count=3)
    labels = [label for label, _, _ in buckets]
    assert labels == ["Jul 2026", "Aug 2026", "Sep 2026"]


def test_month_buckets_start_and_end_dates_for_a_known_month():
    buckets = month_buckets(date(2026, 9, 9), count=1)
    label, start, end = buckets[0]
    assert label == "Sep 2026"
    assert start == "2026-09-01"
    assert end == "2026-09-30"


def test_month_buckets_handles_december_to_january_year_boundary():
    buckets = month_buckets(date(2026, 1, 15), count=2)
    assert [label for label, _, _ in buckets] == ["Dec 2025", "Jan 2026"]
    dec_start, dec_end = buckets[0][1], buckets[0][2]
    assert dec_start == "2025-12-01"
    assert dec_end == "2025-12-31"


def test_month_buckets_handles_leap_year_february():
    buckets = month_buckets(date(2024, 2, 10), count=1)
    _, start, end = buckets[0]
    assert start == "2024-02-01"
    assert end == "2024-02-29"  # 2024 is a leap year


def test_month_buckets_handles_non_leap_year_february():
    buckets = month_buckets(date(2026, 2, 10), count=1)
    _, start, end = buckets[0]
    assert end == "2026-02-28"  # 2026 is not a leap year
