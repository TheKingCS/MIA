"""
tests.test_ledger_manager
============================

Unit tests for core.ledger_manager. Isolates _DATA_DIR/_REVENUE_FILE/
_EXPENSES_FILE into a tmp_path scratch area, same monkeypatch pattern
as test_component_manager.py's isolated_paths. record_sale() also
needs core.product_manager isolated in the same tmp_path, same
"combined-manager fixture" pattern as test_job_manager.py's
consume_material()/produce_product() tests.
"""

from __future__ import annotations

import pytest

import core.ledger_manager as ledger_manager_module
import core.product_manager as product_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.ledger_manager import LedgerManager, _in_range
from core.product_manager import ProductManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(ledger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(ledger_manager_module, "_REVENUE_FILE", data_dir / "revenue.json")
    monkeypatch.setattr(ledger_manager_module, "_EXPENSES_FILE", data_dir / "expenses.json")
    monkeypatch.setattr(product_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(product_manager_module, "_PRODUCTS_FILE", data_dir / "products.json")
    return data_dir


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.products = ProductManager(context)
    context.ledger = LedgerManager(context)
    return context


# ----------------------------------------------------------------------
# _in_range (pure)
# ----------------------------------------------------------------------

def test_in_range_no_bounds_always_true():
    assert _in_range("2026-07-16", None, None) is True


def test_in_range_before_start_is_false():
    assert _in_range("2026-01-01", "2026-06-01", None) is False


def test_in_range_after_end_is_false():
    assert _in_range("2026-12-01", None, "2026-06-01") is False


def test_in_range_within_bounds_is_true():
    assert _in_range("2026-06-15", "2026-06-01", "2026-06-30") is True


def test_in_range_on_boundary_dates_is_true():
    assert _in_range("2026-06-01", "2026-06-01", "2026-06-30") is True
    assert _in_range("2026-06-30", "2026-06-01", "2026-06-30") is True


# ----------------------------------------------------------------------
# Revenue CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_files_exist(isolated_paths):
    context = _make_context()
    assert context.ledger.all_revenue() == []
    assert context.ledger.all_expenses() == []


def test_add_revenue_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    added = context.ledger.add_revenue(amount=25.0, description="Coaster sale", date="2026-07-16")

    reloaded = LedgerManager(context)
    entries = reloaded.all_revenue()
    assert len(entries) == 1
    assert entries[0].entry_id == added.entry_id
    assert entries[0].amount == 25.0
    assert entries[0].description == "Coaster sale"
    assert entries[0].date == "2026-07-16"
    assert entries[0].created_at


def test_add_revenue_defaults_date_to_today(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_revenue(amount=10.0)
    assert entry.date  # non-empty, some ISO date


def test_add_revenue_clamps_negative_amount_to_zero(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_revenue(amount=-50.0)
    assert entry.amount == 0


def test_update_revenue_changes_fields(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_revenue(amount=10.0)
    context.ledger.update_revenue(entry.entry_id, amount=20.0, description="Updated")
    assert entry.amount == 20.0
    assert entry.description == "Updated"


def test_update_revenue_rejects_created_at(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_revenue(amount=10.0)
    with pytest.raises(ValueError):
        context.ledger.update_revenue(entry.entry_id, created_at="hacked")


def test_update_revenue_unknown_id_raises(isolated_paths):
    context = _make_context()
    with pytest.raises(ValueError):
        context.ledger.update_revenue("does-not-exist", amount=5.0)


def test_delete_revenue_removes_it_and_is_idempotent(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_revenue(amount=10.0)
    context.ledger.delete_revenue(entry.entry_id)
    assert context.ledger.get_revenue(entry.entry_id) is None
    context.ledger.delete_revenue(entry.entry_id)  # already gone — must not raise


def test_all_revenue_sorted_most_recent_date_first(isolated_paths):
    context = _make_context()
    context.ledger.add_revenue(amount=10.0, date="2026-01-01")
    context.ledger.add_revenue(amount=20.0, date="2026-06-01")

    ordered = [r.amount for r in context.ledger.all_revenue()]
    assert ordered == [20.0, 10.0]


# ----------------------------------------------------------------------
# Expense CRUD
# ----------------------------------------------------------------------

def test_add_expense_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    added = context.ledger.add_expense(amount=45.0, category="Materials", description="Plywood restock", date="2026-07-16")

    reloaded = LedgerManager(context)
    entries = reloaded.all_expenses()
    assert len(entries) == 1
    assert entries[0].entry_id == added.entry_id
    assert entries[0].amount == 45.0
    assert entries[0].category == "Materials"
    assert entries[0].description == "Plywood restock"


def test_add_expense_rejects_invalid_category_falls_back_to_other(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_expense(amount=10.0, category="Not A Real Category")
    assert entry.category == "Other"


def test_add_expense_clamps_negative_amount_to_zero(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_expense(amount=-10.0)
    assert entry.amount == 0


def test_update_expense_changes_fields(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_expense(amount=10.0, category="Tools")
    context.ledger.update_expense(entry.entry_id, amount=15.0, category="Shipping")
    assert entry.amount == 15.0
    assert entry.category == "Shipping"


def test_update_expense_rejects_created_at(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_expense(amount=10.0)
    with pytest.raises(ValueError):
        context.ledger.update_expense(entry.entry_id, created_at="hacked")


def test_update_expense_unknown_id_raises(isolated_paths):
    context = _make_context()
    with pytest.raises(ValueError):
        context.ledger.update_expense("does-not-exist", amount=5.0)


def test_delete_expense_removes_it_and_is_idempotent(isolated_paths):
    context = _make_context()
    entry = context.ledger.add_expense(amount=10.0)
    context.ledger.delete_expense(entry.entry_id)
    assert context.ledger.get_expense(entry.entry_id) is None
    context.ledger.delete_expense(entry.entry_id)  # already gone — must not raise


def test_all_expenses_sorted_most_recent_date_first(isolated_paths):
    context = _make_context()
    context.ledger.add_expense(amount=10.0, date="2026-01-01")
    context.ledger.add_expense(amount=20.0, date="2026-06-01")

    ordered = [e.amount for e in context.ledger.all_expenses()]
    assert ordered == [20.0, 10.0]


def test_load_handles_corrupt_json_gracefully(isolated_paths, tmp_path):
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "revenue.json").write_text("{not valid json", encoding="utf-8")
    (tmp_path / "data" / "expenses.json").write_text("{not valid json", encoding="utf-8")

    context = _make_context()
    assert context.ledger.all_revenue() == []
    assert context.ledger.all_expenses() == []


# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------

def test_total_revenue_sums_all_entries(isolated_paths):
    context = _make_context()
    context.ledger.add_revenue(amount=10.0)
    context.ledger.add_revenue(amount=25.0)
    assert context.ledger.total_revenue() == 35.0


def test_total_expenses_sums_all_entries(isolated_paths):
    context = _make_context()
    context.ledger.add_expense(amount=10.0)
    context.ledger.add_expense(amount=5.0)
    assert context.ledger.total_expenses() == 15.0


def test_total_revenue_respects_date_range(isolated_paths):
    context = _make_context()
    context.ledger.add_revenue(amount=10.0, date="2026-01-01")
    context.ledger.add_revenue(amount=25.0, date="2026-07-01")
    assert context.ledger.total_revenue(start_date="2026-06-01") == 25.0


def test_net_profit_combines_revenue_and_expenses(isolated_paths):
    context = _make_context()
    context.ledger.add_revenue(amount=100.0)
    context.ledger.add_expense(amount=40.0)
    assert context.ledger.net_profit() == 60.0


def test_net_profit_empty_ledger_is_zero(isolated_paths):
    context = _make_context()
    assert context.ledger.net_profit() == 0.0


# ----------------------------------------------------------------------
# record_sale — the real cross-manager integration
# ----------------------------------------------------------------------

def test_record_sale_records_revenue_and_deducts_stock(isolated_paths):
    context = _make_context()
    product = context.products.add_product(name="Coasters", quantity_in_stock=20)

    entry = context.ledger.record_sale(product.product_id, quantity_sold=3, amount=45.0, description="Etsy order")

    assert entry.amount == 45.0
    assert entry.product_id == product.product_id
    assert entry.quantity_sold == 3
    assert context.products.get_product(product.product_id).quantity_in_stock == 17


def test_record_sale_clamps_stock_at_zero_rather_than_going_negative(isolated_paths):
    context = _make_context()
    product = context.products.add_product(name="Coasters", quantity_in_stock=2)

    context.ledger.record_sale(product.product_id, quantity_sold=10, amount=100.0)

    assert context.products.get_product(product.product_id).quantity_in_stock == 0


def test_record_sale_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    product = context.products.add_product(name="Coasters", quantity_in_stock=20)
    context.ledger.record_sale(product.product_id, quantity_sold=3, amount=45.0)

    reloaded = LedgerManager(context)
    entries = reloaded.all_revenue()
    assert len(entries) == 1
    assert entries[0].quantity_sold == 3
