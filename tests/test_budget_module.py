"""
tests.test_budget_module
===========================

Unit tests for modules.budget.module's pure row formatters — no Qt
event loop needed, same shape as tests/test_maintenance_module.py.
"""

from __future__ import annotations

from datetime import date

from core.budget_manager import Bill, ExpenseEntry, IncomeEntry, IncomeSource
from modules.budget.module import (
    format_bill_row,
    format_expense_row,
    format_income_row,
    format_income_source_row,
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
