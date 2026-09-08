"""
tests.test_budget_manager
============================

Unit tests for core.budget_manager. Isolates _DATA_DIR/_*_FILE into a
tmp_path scratch area, same monkeypatch pattern as
test_calendar_manager.py's isolated_paths, so these tests never touch
real data/*.json.
"""

from __future__ import annotations

from datetime import date

import pytest

import core.budget_manager as budget_manager_module
from core.app_context import AppContext
from core.budget_manager import (
    Bill,
    BudgetManager,
    days_until_bill_due,
    is_bill_due,
    next_bill_due_date,
)
from core.config_manager import ConfigManager
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(budget_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(budget_manager_module, "_BILLS_FILE", data_dir / "bills.json")
    monkeypatch.setattr(budget_manager_module, "_INCOME_FILE", data_dir / "income.json")
    monkeypatch.setattr(budget_manager_module, "_EXPENSES_FILE", data_dir / "budget_expenses.json")
    return data_dir


def _make_manager() -> BudgetManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return BudgetManager(context)


def _bill(due_date="2026-09-01", recurrence=None, last_paid_date=None):
    return Bill(bill_id="b1", name="Electric", amount=120.0, category="Utilities", due_date=due_date, recurrence=recurrence, last_paid_date=last_paid_date)


# ------------------------------------------------------------------
# next_bill_due_date / days_until_bill_due / is_bill_due
# ------------------------------------------------------------------

def test_next_bill_due_date_never_paid_is_the_anchor():
    assert next_bill_due_date(_bill(due_date="2026-09-01")) == date(2026, 9, 1)


def test_next_bill_due_date_one_time_paid_is_none():
    assert next_bill_due_date(_bill(due_date="2026-09-01", recurrence=None, last_paid_date="2026-09-01")) is None


def test_next_bill_due_date_monthly_steps_to_next_month_after_paid():
    bill = _bill(due_date="2026-01-05", recurrence="monthly", last_paid_date="2026-08-05")
    assert next_bill_due_date(bill) == date(2026, 9, 5)


def test_next_bill_due_date_monthly_skips_a_month_missing_the_anchor_day():
    # Anchor on the 31st — no next_bill_due_date lands on Feb, since it doesn't have a 31st.
    bill = _bill(due_date="2026-01-31", recurrence="monthly", last_paid_date="2026-01-31")
    assert next_bill_due_date(bill) == date(2026, 3, 31)


def test_next_bill_due_date_yearly_steps_a_full_year():
    bill = _bill(due_date="2020-06-15", recurrence="yearly", last_paid_date="2025-06-15")
    assert next_bill_due_date(bill) == date(2026, 6, 15)


def test_days_until_bill_due_negative_when_overdue():
    bill = _bill(due_date="2026-08-01")
    assert days_until_bill_due(bill, date(2026, 9, 7)) == -37


def test_days_until_bill_due_none_for_a_paid_one_time_bill():
    bill = _bill(due_date="2026-08-01", last_paid_date="2026-08-01")
    assert days_until_bill_due(bill, date(2026, 9, 7)) is None


def test_is_bill_due_true_on_and_after_the_due_date():
    bill = _bill(due_date="2026-09-07")
    assert is_bill_due(bill, date(2026, 9, 7)) is True
    assert is_bill_due(bill, date(2026, 9, 6)) is False


def test_is_bill_due_false_once_paid_for_a_one_time_bill():
    bill = _bill(due_date="2026-09-01", last_paid_date="2026-09-01")
    assert is_bill_due(bill, date(2026, 9, 7)) is False


def test_is_bill_due_recurring_bill_becomes_due_again_after_being_paid():
    bill = _bill(due_date="2026-01-05", recurrence="monthly", last_paid_date="2026-08-05")
    assert is_bill_due(bill, date(2026, 9, 4)) is False
    assert is_bill_due(bill, date(2026, 9, 5)) is True


# ------------------------------------------------------------------
# Bill CRUD
# ------------------------------------------------------------------

def test_add_bill_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01", category="Utilities", recurrence="monthly")

    reloaded = _make_manager()
    bills = reloaded.all_bills()
    assert len(bills) == 1
    assert bills[0].name == "Electric"
    assert bills[0].recurrence == "monthly"


def test_add_bill_rejects_unknown_category_and_recurrence(isolated_paths):
    manager = _make_manager()
    bill = manager.add_bill(name="X", amount=10.0, due_date="2026-09-01", category="Nonsense", recurrence="daily")
    assert bill.category == "Other"
    assert bill.recurrence is None


def test_delete_bill_removes_it(isolated_paths):
    manager = _make_manager()
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01")
    manager.delete_bill(bill.bill_id)
    assert manager.get_bill(bill.bill_id) is None


# ------------------------------------------------------------------
# mark_bill_paid — the real "one action, two effects" integration point
# ------------------------------------------------------------------

def test_mark_bill_paid_creates_a_real_expense_and_updates_last_paid_date(isolated_paths):
    manager = _make_manager()
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01", category="Utilities", recurrence="monthly", tax_relevant=False)

    entry = manager.mark_bill_paid(bill.bill_id, paid_date="2026-09-03")

    assert entry.amount == 120.0
    assert entry.category == "Utilities"
    assert entry.bill_id == bill.bill_id
    assert entry.tax_relevant is False
    assert manager.get_bill(bill.bill_id).last_paid_date == "2026-09-03"
    assert len(manager.all_expenses()) == 1


def test_mark_bill_paid_amount_override_for_a_variable_bill(isolated_paths):
    manager = _make_manager()
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01")
    entry = manager.mark_bill_paid(bill.bill_id, amount=145.50)
    assert entry.amount == 145.50


def test_mark_bill_paid_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.mark_bill_paid("does-not-exist")


# ------------------------------------------------------------------
# Income / Expense CRUD
# ------------------------------------------------------------------

def test_add_income_persists_and_sorts_newest_first(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=3000.0, category="Salary", date="2026-08-01")
    manager.add_income(amount=1500.0, category="Rental Income", date="2026-09-01")

    reloaded = _make_manager()
    entries = reloaded.all_income()
    assert [e.category for e in entries] == ["Rental Income", "Salary"]


def test_add_expense_defaults_tax_relevant_false_and_income_defaults_true(isolated_paths):
    manager = _make_manager()
    income = manager.add_income(amount=100.0)
    expense = manager.add_expense(amount=50.0)
    assert income.tax_relevant is True
    assert expense.tax_relevant is False


def test_update_income_rejects_unknown_field(isolated_paths):
    manager = _make_manager()
    entry = manager.add_income(amount=100.0)
    with pytest.raises(ValueError):
        manager.update_income(entry.entry_id, bogus_field="x")


# ------------------------------------------------------------------
# Reporting
# ------------------------------------------------------------------

def test_total_income_and_expenses_respect_date_range(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=1000.0, date="2026-08-01")
    manager.add_income(amount=2000.0, date="2026-09-01")
    manager.add_expense(amount=300.0, date="2026-08-15")

    assert manager.total_income(start_date="2026-09-01") == 2000.0
    assert manager.total_income() == 3000.0
    assert manager.total_expenses(end_date="2026-08-31") == 300.0


def test_total_income_tax_relevant_only_filters(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=1000.0, tax_relevant=True)
    manager.add_income(amount=500.0, tax_relevant=False)
    assert manager.total_income(tax_relevant_only=True) == 1000.0
    assert manager.total_income() == 1500.0


def test_net_cash_flow_is_income_minus_expenses(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=3000.0, date="2026-09-01")
    manager.add_expense(amount=1200.0, date="2026-09-02")
    assert manager.net_cash_flow() == 1800.0
