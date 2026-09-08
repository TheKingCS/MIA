"""
tests.test_real_estate_manager
=================================

Unit tests for core.real_estate_manager. Isolates _DATA_DIR/
_PROPERTIES_FILE (and core.budget_manager's own data files, since
rental income/expenses are real Budget entries this manager filters)
into a tmp_path scratch area, same monkeypatch pattern as
test_budget_manager.py's isolated_paths.
"""

from __future__ import annotations

import pytest

import core.budget_manager as budget_manager_module
import core.real_estate_manager as real_estate_manager_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.real_estate_manager import RealEstateManager, equity


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(real_estate_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(real_estate_manager_module, "_PROPERTIES_FILE", data_dir / "properties.json")
    monkeypatch.setattr(budget_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(budget_manager_module, "_BILLS_FILE", data_dir / "bills.json")
    monkeypatch.setattr(budget_manager_module, "_INCOME_FILE", data_dir / "income.json")
    monkeypatch.setattr(budget_manager_module, "_EXPENSES_FILE", data_dir / "budget_expenses.json")
    return data_dir


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.budget = BudgetManager(context)
    return context


def _make_manager(context: AppContext) -> RealEstateManager:
    manager = RealEstateManager(context)
    context.real_estate = manager
    return manager


# ------------------------------------------------------------------
# equity
# ------------------------------------------------------------------

def test_equity_is_value_minus_mortgage():
    from core.real_estate_manager import Property
    prop = Property(property_id="p1", name="123 Main St", current_value=300000.0, mortgage_balance=180000.0)
    assert equity(prop) == 120000.0


# ------------------------------------------------------------------
# Property CRUD
# ------------------------------------------------------------------

def test_add_property_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_property(name="123 Main St", property_type="Rental", current_value=300000.0, mortgage_balance=180000.0)

    reloaded = RealEstateManager(context)
    properties = reloaded.all_properties()
    assert len(properties) == 1
    assert properties[0].name == "123 Main St"
    assert properties[0].mortgage_balance == 180000.0


def test_add_property_rejects_unknown_type(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="X", property_type="Nonsense")
    assert prop.property_type == "Other"


def test_delete_property_removes_the_record_only(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St", current_value=300000.0)
    manager.record_rental_income(prop.property_id, amount=1500.0, date_str="2026-09-01")

    manager.delete_property(prop.property_id)

    assert manager.get_property(prop.property_id) is None
    # Real financial history isn't deleted along with the Property record.
    assert len(context.budget.all_income()) == 1


# ------------------------------------------------------------------
# record_rental_income / record_property_expense — thin wrappers over Budget
# ------------------------------------------------------------------

def test_record_rental_income_sets_property_id_and_category(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St")

    entry = manager.record_rental_income(prop.property_id, amount=1500.0, date_str="2026-09-01")

    assert entry.property_id == prop.property_id
    assert entry.category == "Rental Income"
    assert entry.amount == 1500.0


def test_record_rental_income_unknown_property_raises(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.record_rental_income("does-not-exist", amount=1500.0)


def test_record_property_expense_sets_property_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St")

    entry = manager.record_property_expense(prop.property_id, amount=200.0, category="Maintenance", date_str="2026-09-05")

    assert entry.property_id == prop.property_id
    assert entry.category == "Maintenance"


def test_income_for_property_only_returns_that_propertys_entries(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop_a = manager.add_property(name="123 Main St")
    prop_b = manager.add_property(name="456 Oak Ave")
    manager.record_rental_income(prop_a.property_id, amount=1500.0, date_str="2026-09-01")
    manager.record_rental_income(prop_b.property_id, amount=1800.0, date_str="2026-09-01")
    context.budget.add_income(amount=3000.0, category="Salary", date="2026-09-01")  # unrelated, no property_id

    entries = manager.income_for_property(prop_a.property_id)
    assert len(entries) == 1
    assert entries[0].amount == 1500.0


def test_income_for_property_respects_date_range(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St")
    manager.record_rental_income(prop.property_id, amount=1500.0, date_str="2026-08-01")
    manager.record_rental_income(prop.property_id, amount=1500.0, date_str="2026-09-01")

    entries = manager.income_for_property(prop.property_id, start_date="2026-09-01")
    assert len(entries) == 1


# ------------------------------------------------------------------
# net_operating_income / cap_rate
# ------------------------------------------------------------------

def test_net_operating_income_is_income_minus_operating_expenses(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St")
    manager.record_rental_income(prop.property_id, amount=1500.0, date_str="2026-09-01")
    manager.record_property_expense(prop.property_id, amount=200.0, category="Maintenance", date_str="2026-09-05")

    assert manager.net_operating_income(prop.property_id) == 1300.0


def test_net_operating_income_excludes_mortgage_payments(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St")
    manager.record_rental_income(prop.property_id, amount=1500.0, date_str="2026-09-01")
    manager.record_property_expense(prop.property_id, amount=1000.0, category="Mortgage/Rent", date_str="2026-09-05")

    # Mortgage payment is debt service, not an operating expense — NOI stays 1500, not 500.
    assert manager.net_operating_income(prop.property_id) == 1500.0


def test_cap_rate_computes_noi_over_current_value(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St", current_value=200000.0)
    manager.record_rental_income(prop.property_id, amount=20000.0, date_str="2026-01-01")

    assert manager.cap_rate(prop.property_id) == pytest.approx(0.1)


def test_cap_rate_none_when_current_value_is_zero(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="Undervalued Lot", current_value=0.0)
    assert manager.cap_rate(prop.property_id) is None


def test_cap_rate_none_for_unknown_property(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.cap_rate("does-not-exist") is None
