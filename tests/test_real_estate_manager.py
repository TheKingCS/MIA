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
from core.real_estate_manager import (
    Property,
    RealEstateManager,
    accumulated_depreciation,
    annual_depreciation,
    depreciable_basis,
    equity,
)


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
    prop = Property(property_id="p1", name="123 Main St", current_value=300000.0, mortgage_balance=180000.0)
    assert equity(prop) == 120000.0


def test_property_from_dict_backward_compatible_defaults_depreciation_fields():
    prop = Property.from_dict({"property_id": "p1", "name": "123 Main St"})
    assert prop.land_value == 0.0
    assert prop.placed_in_service_date == ""


# ------------------------------------------------------------------
# depreciable_basis / annual_depreciation / accumulated_depreciation
# ------------------------------------------------------------------

def _rental(**overrides) -> Property:
    defaults = dict(
        property_id="p1", name="123 Main St", property_type="Rental",
        purchase_price=275000.0, land_value=0.0,
        purchase_date="2020-01-01", placed_in_service_date="",
    )
    defaults.update(overrides)
    return Property(**defaults)


def test_depreciable_basis_subtracts_land_value():
    prop = _rental(purchase_price=275000.0, land_value=50000.0)
    assert depreciable_basis(prop) == 225000.0


def test_depreciable_basis_zero_land_value_is_full_price():
    prop = _rental(purchase_price=275000.0, land_value=0.0)
    assert depreciable_basis(prop) == 275000.0


def test_depreciable_basis_land_value_exceeding_price_clamps_to_zero():
    prop = _rental(purchase_price=100000.0, land_value=150000.0)
    assert depreciable_basis(prop) == 0.0


def test_annual_depreciation_rental_computes_real_figure():
    prop = _rental(purchase_price=275000.0, land_value=0.0)
    assert annual_depreciation(prop) == pytest.approx(275000.0 / 27.5)


def test_annual_depreciation_investment_type_also_eligible():
    prop = _rental(property_type="Investment", purchase_price=275000.0, land_value=0.0)
    assert annual_depreciation(prop) == pytest.approx(275000.0 / 27.5)


def test_annual_depreciation_primary_residence_is_zero_even_with_real_basis():
    prop = _rental(property_type="Primary Residence", purchase_price=275000.0, land_value=0.0)
    assert annual_depreciation(prop) == 0.0


def test_annual_depreciation_land_type_is_zero():
    prop = _rental(property_type="Land", purchase_price=100000.0, land_value=0.0)
    assert annual_depreciation(prop) == 0.0


def test_annual_depreciation_custom_useful_life():
    prop = _rental(purchase_price=390000.0, land_value=0.0)
    assert annual_depreciation(prop, useful_life_years=39.0) == pytest.approx(10000.0)


def test_accumulated_depreciation_falls_back_to_purchase_date_when_unset():
    from datetime import date
    prop = _rental(purchase_price=275000.0, land_value=0.0, purchase_date="2020-01-01", placed_in_service_date="")
    # Exactly 2 years after purchase_date, no separate placed_in_service_date set.
    result = accumulated_depreciation(prop, date(2022, 1, 1))
    expected_annual = 275000.0 / 27.5
    assert result == pytest.approx(expected_annual * 2, rel=0.01)


def test_accumulated_depreciation_uses_placed_in_service_date_when_set():
    from datetime import date
    prop = _rental(
        purchase_price=275000.0, land_value=0.0,
        purchase_date="2018-01-01", placed_in_service_date="2020-01-01",
    )
    # 1 year after placed_in_service_date (not purchase_date, which was 2 years earlier).
    result = accumulated_depreciation(prop, date(2021, 1, 1))
    expected_annual = 275000.0 / 27.5
    assert result == pytest.approx(expected_annual, rel=0.01)


def test_accumulated_depreciation_zero_before_start_date():
    from datetime import date
    prop = _rental(purchase_price=275000.0, land_value=0.0, purchase_date="2025-01-01")
    assert accumulated_depreciation(prop, date(2024, 1, 1)) == 0.0


def test_accumulated_depreciation_clamps_at_full_basis_once_fully_depreciated():
    from datetime import date
    prop = _rental(purchase_price=275000.0, land_value=0.0, purchase_date="2000-01-01")
    # Well past 27.5 years — must clamp at the full depreciable basis, not overshoot.
    assert accumulated_depreciation(prop, date(2050, 1, 1)) == 275000.0


def test_accumulated_depreciation_zero_for_non_depreciable_property_type():
    from datetime import date
    prop = _rental(property_type="Primary Residence", purchase_price=275000.0, purchase_date="2000-01-01")
    assert accumulated_depreciation(prop, date(2024, 1, 1)) == 0.0


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


def test_add_property_stores_entity_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St", entity_id="ent-1")
    assert prop.entity_id == "ent-1"


def test_property_from_dict_backward_compatible_without_entity_field():
    from core.real_estate_manager import Property
    old_shape = {"property_id": "p1", "name": "123 Main St", "current_value": 300000.0}
    prop = Property.from_dict(old_shape)
    assert prop.entity_id == ""


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


def test_record_rental_income_inherits_property_entity_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St", entity_id="ent-1")

    entry = manager.record_rental_income(prop.property_id, amount=1500.0, date_str="2026-09-01")
    assert entry.entity_id == "ent-1"


def test_record_property_expense_inherits_property_entity_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    prop = manager.add_property(name="123 Main St", entity_id="ent-1")

    entry = manager.record_property_expense(prop.property_id, amount=200.0, date_str="2026-09-05")
    assert entry.entity_id == "ent-1"


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
