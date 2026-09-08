"""
tests.test_real_estate_module
================================

Unit tests for modules.real_estate.module's pure formatters — no Qt
event loop needed, same shape as tests/test_property_module.py.
"""

from __future__ import annotations

from datetime import date

from core.budget_manager import ExpenseEntry, IncomeEntry
from core.maintenance_manager import MaintenanceTask
from core.real_estate_manager import Property
from modules.real_estate.module import (
    format_expense_row,
    format_income_row,
    format_linked_task_line,
    format_property_glance_line,
)


def test_format_property_glance_line():
    prop = Property(property_id="p1", name="123 Main St", property_type="Rental")
    assert format_property_glance_line(prop, 120000.0) == "123 Main St   [Rental]   Equity: $120,000.00"


def test_format_linked_task_line_calendar_overdue():
    task = MaintenanceTask(
        task_id="t1", asset_id="a1", title="Roof inspection", trigger_type="calendar",
        interval_days=365, last_completed="2025-01-01",
    )
    assert format_linked_task_line(task, date(2026, 9, 8)) == "Roof inspection — overdue 250d"


def test_format_income_row_with_description():
    entry = IncomeEntry(entry_id="i1", amount=1500.0, category="Rental Income", description="September rent", date="2026-09-01")
    assert format_income_row(entry) == "2026-09-01   $1500.00  September rent"


def test_format_expense_row_with_category():
    entry = ExpenseEntry(entry_id="e1", amount=200.0, category="Maintenance", description="Plumbing repair", date="2026-09-05")
    assert format_expense_row(entry) == "2026-09-05   $200.00  [Maintenance]  Plumbing repair"
