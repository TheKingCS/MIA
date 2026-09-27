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

import json

import core.budget_manager as budget_manager_module
import core.config_manager as config_manager_module
import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.budget_manager import (
    Bill,
    BudgetManager,
    BudgetTarget,
    Debt,
    IncomeSource,
    days_until_bill_due,
    days_until_income_due,
    days_until_promo_expires,
    effective_apr,
    is_bill_due,
    next_bill_due_date,
    next_income_due_date,
    rank_debts,
)
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager
from core.skill_manager import SkillManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(budget_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(budget_manager_module, "_BILLS_FILE", data_dir / "bills.json")
    monkeypatch.setattr(budget_manager_module, "_INCOME_FILE", data_dir / "income.json")
    monkeypatch.setattr(budget_manager_module, "_EXPENSES_FILE", data_dir / "budget_expenses.json")
    monkeypatch.setattr(budget_manager_module, "_INCOME_SOURCES_FILE", data_dir / "income_sources.json")
    monkeypatch.setattr(budget_manager_module, "_BUDGET_TARGETS_FILE", data_dir / "budget_targets.json")
    monkeypatch.setattr(budget_manager_module, "_BUSINESS_ENTITIES_FILE", data_dir / "business_entities.json")
    monkeypatch.setattr(budget_manager_module, "_DEBTS_FILE", data_dir / "debts.json")
    # Real once a test constructs a real ProfileManager too (2026-09-11
    # gamification hook tests below) — see test_workout_manager.py's
    # own isolated_paths for the identical reasoning.
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    # "My Hero's Path" (2026-09-11) — needed once a test constructs a
    # real SkillManager too, same reasoning as config_manager above.
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
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


def test_add_bill_rejects_negative_amount(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.add_bill(name="X", amount=-10.0, due_date="2026-09-01")


def test_add_bill_accepts_zero_amount(isolated_paths):
    manager = _make_manager()
    bill = manager.add_bill(name="X", amount=0.0, due_date="2026-09-01")
    assert bill.amount == 0.0


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


def test_mark_bill_paid_grants_xp_to_the_active_profile(isolated_paths):
    """2026-09-11 gamification pass — same "recurring completion is a
    real, distinct event each time" reasoning as
    core.maintenance_manager.MaintenanceManager.mark_complete()."""
    manager = _make_manager()
    manager.context.profiles = ProfileManager(manager.context)
    manager.context.profiles.create_profile(name="Alex", make_active=True)
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01")

    manager.mark_bill_paid(bill.bill_id)

    assert manager.context.profiles.get_active_profile().total_xp == 5


def test_mark_bill_paid_grants_xp_with_no_active_profile_does_not_raise(isolated_paths):
    manager = _make_manager()
    manager.context.profiles = ProfileManager(manager.context)
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01")
    manager.mark_bill_paid(bill.bill_id)  # must not raise


def test_mark_bill_paid_grants_household_management_skill_xp(isolated_paths):
    """"My Hero's Path" (2026-09-11)."""
    isolated_paths.mkdir(parents=True, exist_ok=True)
    (isolated_paths / "skill_definitions.json").write_text(
        json.dumps(
            {"skills": [{"skill_id": "household_management", "name": "Household Management", "category": "Social"}]}
        )
    )
    manager = _make_manager()
    manager.context.profiles = ProfileManager(manager.context)
    manager.context.skills = SkillManager(manager.context)
    profile = manager.context.profiles.create_profile(name="Alex", make_active=True)
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01")

    manager.mark_bill_paid(bill.bill_id)

    assert manager.context.skills.get_progress(profile.profile_id, "household_management").total_xp == 5


def test_mark_bill_paid_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.mark_bill_paid("does-not-exist")


def test_add_bill_with_entity_id_persists(isolated_paths):
    manager = _make_manager()
    manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01", entity_id="ent1")

    reloaded = _make_manager()
    assert reloaded.all_bills()[0].entity_id == "ent1"


def test_bill_from_dict_backward_compatible_with_old_shape_defaults_entity_id():
    bill = Bill.from_dict({"bill_id": "b1", "name": "Electric", "amount": 120.0})
    assert bill.entity_id == ""


def test_mark_bill_paid_copies_entity_id_onto_the_expense(isolated_paths):
    manager = _make_manager()
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01", entity_id="ent1")
    entry = manager.mark_bill_paid(bill.bill_id)
    assert entry.entity_id == "ent1"


def test_mark_bill_paid_without_entity_leaves_expense_unassigned(isolated_paths):
    manager = _make_manager()
    bill = manager.add_bill(name="Electric", amount=120.0, due_date="2026-09-01")
    entry = manager.mark_bill_paid(bill.bill_id)
    assert entry.entity_id == ""


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


def test_add_income_rejects_negative_amount(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.add_income(amount=-100.0)


def test_add_income_accepts_zero_amount(isolated_paths):
    manager = _make_manager()
    entry = manager.add_income(amount=0.0)
    assert entry.amount == 0.0


def test_add_expense_rejects_negative_amount(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.add_expense(amount=-50.0)


def test_add_expense_accepts_zero_amount(isolated_paths):
    manager = _make_manager()
    entry = manager.add_expense(amount=0.0)
    assert entry.amount == 0.0


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


def test_total_expenses_by_category_groups_and_omits_untouched_categories(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=100.0, category="Groceries", date="2026-09-01")
    manager.add_expense(amount=50.0, category="Groceries", date="2026-09-05")
    manager.add_expense(amount=200.0, category="Utilities", date="2026-09-03")

    totals = manager.total_expenses_by_category()
    assert totals == {"Groceries": 150.0, "Utilities": 200.0}
    assert "Insurance" not in totals


def test_total_income_by_category_only_includes_categories_with_entries(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=3000.0, category="Salary", date="2026-09-01")
    manager.add_income(amount=500.0, category="Investment", date="2026-09-05")

    totals = manager.total_income_by_category()
    assert totals == {"Salary": 3000.0, "Investment": 500.0}
    assert "Rental Income" not in totals


def test_total_income_by_category_sums_multiple_entries_same_category(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=1500.0, category="Rental Income", date="2026-09-01")
    manager.add_income(amount=1500.0, category="Rental Income", date="2026-09-15")

    totals = manager.total_income_by_category()
    assert totals == {"Rental Income": 3000.0}


def test_total_income_by_category_respects_date_range(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=3000.0, category="Salary", date="2026-08-01")
    manager.add_income(amount=3000.0, category="Salary", date="2026-09-01")

    totals = manager.total_income_by_category(start_date="2026-09-01", end_date="2026-09-30")
    assert totals == {"Salary": 3000.0}


# ------------------------------------------------------------------
# plaid_transaction_id — the dedup key core.plaid_manager uses on
# repeat sync (2026-09-08, full Plaid transaction history)
# ------------------------------------------------------------------

def test_add_income_stores_plaid_transaction_id(isolated_paths):
    manager = _make_manager()
    entry = manager.add_income(amount=1200.0, category="Salary", date="2026-09-01", plaid_transaction_id="txn-abc")
    assert entry.plaid_transaction_id == "txn-abc"


def test_add_expense_stores_plaid_transaction_id(isolated_paths):
    manager = _make_manager()
    entry = manager.add_expense(amount=45.0, category="Groceries", date="2026-09-01", plaid_transaction_id="txn-def")
    assert entry.plaid_transaction_id == "txn-def"


def test_get_income_by_plaid_transaction_id_found_not_found_and_empty_input(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=1200.0, plaid_transaction_id="txn-abc")

    assert manager.get_income_by_plaid_transaction_id("txn-abc").amount == 1200.0
    assert manager.get_income_by_plaid_transaction_id("txn-nonexistent") is None
    assert manager.get_income_by_plaid_transaction_id("") is None


def test_get_expense_by_plaid_transaction_id_found_not_found_and_empty_input(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=45.0, plaid_transaction_id="txn-def")

    assert manager.get_expense_by_plaid_transaction_id("txn-def").amount == 45.0
    assert manager.get_expense_by_plaid_transaction_id("txn-nonexistent") is None
    assert manager.get_expense_by_plaid_transaction_id("") is None


def test_income_entry_from_dict_backward_compatible_without_plaid_field():
    old_shape = {"entry_id": "i1", "amount": 3000.0, "category": "Salary", "date": "2026-09-01"}
    entry = budget_manager_module.IncomeEntry.from_dict(old_shape)
    assert entry.plaid_transaction_id == ""


def test_expense_entry_from_dict_backward_compatible_without_plaid_field():
    old_shape = {"entry_id": "e1", "amount": 45.0, "category": "Groceries", "date": "2026-09-01"}
    entry = budget_manager_module.ExpenseEntry.from_dict(old_shape)
    assert entry.plaid_transaction_id == ""


# ------------------------------------------------------------------
# BusinessEntity — LLC/sole-prop tagging (2026-09-08)
# ------------------------------------------------------------------

def test_add_business_entity_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    entity = manager.add_business_entity(name="Sunrise Rentals LLC", entity_type="LLC", notes="123 Main St")

    reloaded = _make_manager()
    found = reloaded.get_business_entity(entity.entity_id)
    assert found is not None
    assert found.name == "Sunrise Rentals LLC"
    assert found.entity_type == "LLC"
    assert found.notes == "123 Main St"


def test_add_business_entity_coerces_unknown_entity_type_to_other(isolated_paths):
    manager = _make_manager()
    entity = manager.add_business_entity(name="Side Gig", entity_type="Not A Real Type")
    assert entity.entity_type == "Other"


def test_update_business_entity_rejects_unknown_field(isolated_paths):
    manager = _make_manager()
    entity = manager.add_business_entity(name="Sunrise Rentals LLC")
    with pytest.raises(ValueError):
        manager.update_business_entity(entity.entity_id, not_a_real_field="x")


def test_update_business_entity_coerces_unknown_entity_type_to_other(isolated_paths):
    manager = _make_manager()
    entity = manager.add_business_entity(name="Sunrise Rentals LLC")
    updated = manager.update_business_entity(entity.entity_id, entity_type="Not A Real Type")
    assert updated.entity_type == "Other"


def test_delete_business_entity_removes_it(isolated_paths):
    manager = _make_manager()
    entity = manager.add_business_entity(name="Sunrise Rentals LLC")
    manager.delete_business_entity(entity.entity_id)
    assert manager.get_business_entity(entity.entity_id) is None


def test_get_business_entity_found_and_not_found(isolated_paths):
    manager = _make_manager()
    entity = manager.add_business_entity(name="Sunrise Rentals LLC")
    assert manager.get_business_entity(entity.entity_id) is not None
    assert manager.get_business_entity("no-such-id") is None


def test_all_business_entities_sorted_by_name(isolated_paths):
    manager = _make_manager()
    manager.add_business_entity(name="Zed Holdings LLC")
    manager.add_business_entity(name="Aquaponics R&D LLC")
    names = [e.name for e in manager.all_business_entities()]
    assert names == ["Aquaponics R&D LLC", "Zed Holdings LLC"]


def test_add_income_stores_entity_id(isolated_paths):
    manager = _make_manager()
    entry = manager.add_income(amount=1200.0, entity_id="ent-1")
    assert entry.entity_id == "ent-1"


def test_add_expense_stores_entity_id(isolated_paths):
    manager = _make_manager()
    entry = manager.add_expense(amount=45.0, entity_id="ent-1")
    assert entry.entity_id == "ent-1"


def test_income_entry_from_dict_backward_compatible_without_entity_field():
    old_shape = {"entry_id": "i1", "amount": 3000.0, "category": "Salary", "date": "2026-09-01"}
    entry = budget_manager_module.IncomeEntry.from_dict(old_shape)
    assert entry.entity_id == ""


def test_expense_entry_from_dict_backward_compatible_without_entity_field():
    old_shape = {"entry_id": "e1", "amount": 45.0, "category": "Groceries", "date": "2026-09-01"}
    entry = budget_manager_module.ExpenseEntry.from_dict(old_shape)
    assert entry.entity_id == ""


def test_expense_entry_from_dict_backward_compatible_defaults_payee_empty():
    old_shape = {"entry_id": "e1", "amount": 45.0, "category": "Groceries", "date": "2026-09-01"}
    entry = budget_manager_module.ExpenseEntry.from_dict(old_shape)
    assert entry.payee == ""


def test_add_expense_stores_payee(isolated_paths):
    manager = _make_manager()
    entry = manager.add_expense(amount=800.0, payee="Ace Plumbing LLC")
    assert entry.payee == "Ace Plumbing LLC"


# ------------------------------------------------------------------
# payees_over_1099_threshold — real IRS threshold check, business-tagged only
# ------------------------------------------------------------------

def test_payees_over_1099_threshold_excludes_below_threshold(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=500.0, payee="Ace Plumbing", property_id="p1")
    assert manager.payees_over_1099_threshold() == {}


def test_payees_over_1099_threshold_includes_at_or_over_threshold(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=600.0, payee="Ace Plumbing", property_id="p1")
    assert manager.payees_over_1099_threshold() == {"Ace Plumbing": 600.0}


def test_payees_over_1099_threshold_sums_multiple_payments_to_same_payee(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=300.0, payee="Ace Plumbing", property_id="p1", date="2026-01-01")
    manager.add_expense(amount=350.0, payee="Ace Plumbing", property_id="p1", date="2026-06-01")
    assert manager.payees_over_1099_threshold() == {"Ace Plumbing": 650.0}


def test_payees_over_1099_threshold_excludes_purely_personal_payments(isolated_paths):
    manager = _make_manager()
    # No property_id or entity_id — a personal household payment, not business-tagged.
    manager.add_expense(amount=1000.0, payee="Ace Plumbing")
    assert manager.payees_over_1099_threshold() == {}


def test_payees_over_1099_threshold_entity_tagged_counts(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=700.0, payee="Ace Plumbing", entity_id="ent-1")
    assert manager.payees_over_1099_threshold() == {"Ace Plumbing": 700.0}


def test_payees_over_1099_threshold_ignores_blank_payee(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=1000.0, property_id="p1")  # no payee set
    assert manager.payees_over_1099_threshold() == {}


def test_payees_over_1099_threshold_groups_case_insensitively_keeps_first_seen_casing(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=400.0, payee="Ace Plumbing", property_id="p1", date="2026-01-01")
    manager.add_expense(amount=300.0, payee="ACE PLUMBING", property_id="p1", date="2026-06-01")
    result = manager.payees_over_1099_threshold()
    assert result == {"Ace Plumbing": 700.0}  # first-seen casing preserved


def test_payees_over_1099_threshold_filters_by_entity_id(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=700.0, payee="Ace Plumbing", entity_id="ent-1")
    manager.add_expense(amount=800.0, payee="Bob's Landscaping", entity_id="ent-2")
    assert manager.payees_over_1099_threshold(entity_id="ent-1") == {"Ace Plumbing": 700.0}


def test_payees_over_1099_threshold_respects_date_range(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=700.0, payee="Ace Plumbing", property_id="p1", date="2025-01-01")
    assert manager.payees_over_1099_threshold(start_date="2026-01-01") == {}


def test_payees_over_1099_threshold_custom_threshold(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=200.0, payee="Ace Plumbing", property_id="p1")
    assert manager.payees_over_1099_threshold(threshold=100.0) == {"Ace Plumbing": 200.0}
    assert manager.payees_over_1099_threshold(threshold=500.0) == {}


def test_total_income_entity_filter_matches_only_that_entity(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=3000.0, entity_id="ent-1", date="2026-09-01")
    manager.add_income(amount=1500.0, entity_id="ent-2", date="2026-09-01")
    assert manager.total_income(entity_id="ent-1") == 3000.0
    assert manager.total_income(entity_id="ent-2") == 1500.0
    assert manager.total_income() == 4500.0


def test_total_expenses_entity_filter_matches_only_that_entity(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=100.0, entity_id="ent-1", date="2026-09-01")
    manager.add_expense(amount=50.0, entity_id="ent-2", date="2026-09-01")
    assert manager.total_expenses(entity_id="ent-1") == 100.0
    assert manager.total_expenses(entity_id="ent-2") == 50.0


def test_total_income_entity_filter_with_no_matches_returns_zero(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=3000.0, entity_id="ent-1", date="2026-09-01")
    assert manager.total_income(entity_id="ent-nonexistent") == 0.0


def test_total_income_by_category_entity_filter_only_includes_matching_entries(isolated_paths):
    manager = _make_manager()
    manager.add_income(amount=3000.0, category="Salary", entity_id="ent-1", date="2026-09-01")
    manager.add_income(amount=1500.0, category="Rental Income", entity_id="ent-2", date="2026-09-01")
    totals = manager.total_income_by_category(entity_id="ent-1")
    assert totals == {"Salary": 3000.0}


def test_total_expenses_by_category_entity_filter_only_includes_matching_entries(isolated_paths):
    manager = _make_manager()
    manager.add_expense(amount=100.0, category="Groceries", entity_id="ent-1", date="2026-09-01")
    manager.add_expense(amount=50.0, category="Utilities", entity_id="ent-2", date="2026-09-01")
    totals = manager.total_expenses_by_category(entity_id="ent-1")
    assert totals == {"Groceries": 100.0}


# ------------------------------------------------------------------
# IncomeSource — next_income_due_date / days_until_income_due
# ------------------------------------------------------------------

def _income_source(next_date="2026-09-01", recurrence=None, last_received_date=None, expected_amount=2400.0):
    return budget_manager_module.IncomeSource(
        source_id="s1", name="Paycheck", expected_amount=expected_amount,
        category="Salary", next_date=next_date, recurrence=recurrence, last_received_date=last_received_date,
    )


def test_next_income_due_date_never_received_is_the_anchor():
    assert next_income_due_date(_income_source(next_date="2026-09-01")) == date(2026, 9, 1)


def test_next_income_due_date_one_time_received_is_none():
    source = _income_source(next_date="2026-09-01", recurrence=None, last_received_date="2026-09-01")
    assert next_income_due_date(source) is None


def test_next_income_due_date_biweekly_steps_14_days_after_received():
    source = _income_source(next_date="2026-06-15", recurrence="biweekly", last_received_date="2026-08-24")
    assert next_income_due_date(source) == date(2026, 9, 7)


def test_days_until_income_due_negative_when_overdue():
    source = _income_source(next_date="2026-08-01")
    assert days_until_income_due(source, date(2026, 9, 7)) == -37


# ------------------------------------------------------------------
# IncomeSource CRUD + mark_income_received
# ------------------------------------------------------------------

def test_add_income_source_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-05", recurrence="biweekly")

    reloaded = _make_manager()
    sources = reloaded.all_income_sources()
    assert len(sources) == 1
    assert sources[0].name == "Paycheck"
    assert sources[0].recurrence == "biweekly"


def test_add_income_source_rejects_unknown_category_and_recurrence(isolated_paths):
    manager = _make_manager()
    source = manager.add_income_source(name="X", expected_amount=100.0, next_date="2026-09-01", category="Nonsense", recurrence="daily")
    assert source.category == "Other"
    assert source.recurrence is None


def test_add_income_source_rejects_negative_expected_amount(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.add_income_source(name="X", expected_amount=-100.0, next_date="2026-09-01")


def test_mark_income_received_creates_real_income_and_updates_last_received(isolated_paths):
    manager = _make_manager()
    source = manager.add_income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-05", category="Salary", recurrence="biweekly")

    entry = manager.mark_income_received(source.source_id, received_date="2026-09-05")

    assert entry.amount == 2400.0
    assert entry.category == "Salary"
    assert manager.get_income_source(source.source_id).last_received_date == "2026-09-05"
    assert len(manager.all_income()) == 1


def test_mark_income_received_amount_override_for_a_variable_paycheck(isolated_paths):
    manager = _make_manager()
    source = manager.add_income_source(name="Freelance", expected_amount=1000.0, next_date="2026-09-01")
    entry = manager.mark_income_received(source.source_id, amount=1250.0)
    assert entry.amount == 1250.0


def test_mark_income_received_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.mark_income_received("does-not-exist")


def test_add_income_source_with_entity_id_persists(isolated_paths):
    manager = _make_manager()
    manager.add_income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-05", entity_id="ent1")

    reloaded = _make_manager()
    assert reloaded.all_income_sources()[0].entity_id == "ent1"


def test_income_source_from_dict_backward_compatible_with_old_shape_defaults_entity_id():
    source = IncomeSource.from_dict({"source_id": "s1", "name": "Paycheck", "expected_amount": 2400.0})
    assert source.entity_id == ""


def test_mark_income_received_copies_entity_id_onto_the_income(isolated_paths):
    manager = _make_manager()
    source = manager.add_income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-05", entity_id="ent1")
    entry = manager.mark_income_received(source.source_id)
    assert entry.entity_id == "ent1"


def test_mark_income_received_without_entity_leaves_income_unassigned(isolated_paths):
    manager = _make_manager()
    source = manager.add_income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-05")
    entry = manager.mark_income_received(source.source_id)
    assert entry.entity_id == ""


def test_delete_income_source_removes_it(isolated_paths):
    manager = _make_manager()
    source = manager.add_income_source(name="Paycheck", expected_amount=2400.0, next_date="2026-09-05")
    manager.delete_income_source(source.source_id)
    assert manager.get_income_source(source.source_id) is None


# ------------------------------------------------------------------
# BudgetTarget CRUD
# ------------------------------------------------------------------

def test_set_budget_target_creates_then_upserts(isolated_paths):
    manager = _make_manager()
    manager.set_budget_target("Groceries", 400.0)
    manager.set_budget_target("Groceries", 450.0)

    targets = manager.all_budget_targets()
    assert len(targets) == 1
    assert targets[0].monthly_amount == 450.0


def test_set_budget_target_rejects_unknown_category(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.set_budget_target("Nonsense Category", 100.0)


def test_set_budget_target_rejects_negative_monthly_amount(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.set_budget_target("Groceries", -100.0)


def test_set_budget_target_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.set_budget_target("Groceries", 400.0)

    reloaded = _make_manager()
    assert reloaded.get_budget_target("Groceries").monthly_amount == 400.0


def test_delete_budget_target_removes_it(isolated_paths):
    manager = _make_manager()
    manager.set_budget_target("Groceries", 400.0)
    manager.delete_budget_target("Groceries")
    assert manager.get_budget_target("Groceries") is None


def test_budget_target_from_dict_backward_compatible_defaults_entity_id_empty():
    target = BudgetTarget.from_dict({"category": "Groceries", "monthly_amount": 400.0})
    assert target.entity_id == ""


def test_set_budget_target_same_category_different_entities_are_independent(isolated_paths):
    manager = _make_manager()
    manager.set_budget_target("Groceries", 400.0)  # household/unassigned
    manager.set_budget_target("Groceries", 150.0, entity_id="ent1")

    assert manager.get_budget_target("Groceries").monthly_amount == 400.0
    assert manager.get_budget_target("Groceries", entity_id="ent1").monthly_amount == 150.0


def test_delete_budget_target_only_removes_the_matching_entity(isolated_paths):
    manager = _make_manager()
    manager.set_budget_target("Groceries", 400.0)
    manager.set_budget_target("Groceries", 150.0, entity_id="ent1")

    manager.delete_budget_target("Groceries", entity_id="ent1")

    assert manager.get_budget_target("Groceries") is not None
    assert manager.get_budget_target("Groceries", entity_id="ent1") is None


def test_all_budget_targets_no_filter_returns_everything(isolated_paths):
    manager = _make_manager()
    manager.set_budget_target("Groceries", 400.0)
    manager.set_budget_target("Groceries", 150.0, entity_id="ent1")
    manager.set_budget_target("Utilities", 100.0, entity_id="ent2")

    assert len(manager.all_budget_targets()) == 3


def test_all_budget_targets_filters_to_one_entity(isolated_paths):
    manager = _make_manager()
    manager.set_budget_target("Groceries", 400.0)
    manager.set_budget_target("Groceries", 150.0, entity_id="ent1")

    household_only = manager.all_budget_targets(entity_id="")
    assert len(household_only) == 1
    assert household_only[0].monthly_amount == 400.0

    ent1_only = manager.all_budget_targets(entity_id="ent1")
    assert len(ent1_only) == 1
    assert ent1_only[0].monthly_amount == 150.0


# ----------------------------------------------------------------------
# Debt — payoff-tracked liabilities, effective_apr()/rank_debts()
# ----------------------------------------------------------------------

def _debt(balance=5000.0, interest_rate=24.99, promo_apr=None, promo_expires_date=None):
    return Debt(
        debt_id="d1", name="Chase Freedom", balance=balance, interest_rate=interest_rate,
        minimum_payment=100.0, debt_type="Credit Card", promo_apr=promo_apr, promo_expires_date=promo_expires_date,
    )


def test_effective_apr_no_promo_returns_standard_rate():
    debt = _debt(interest_rate=19.99)
    assert effective_apr(debt, date(2026, 9, 27)) == 19.99


def test_effective_apr_active_promo_returns_promo_rate():
    debt = _debt(interest_rate=24.99, promo_apr=0.0, promo_expires_date="2026-12-01")
    assert effective_apr(debt, date(2026, 9, 27)) == 0.0


def test_effective_apr_expired_promo_returns_standard_rate():
    debt = _debt(interest_rate=24.99, promo_apr=0.0, promo_expires_date="2026-01-01")
    assert effective_apr(debt, date(2026, 9, 27)) == 24.99


def test_effective_apr_promo_expires_today_still_active():
    debt = _debt(interest_rate=24.99, promo_apr=0.0, promo_expires_date="2026-09-27")
    assert effective_apr(debt, date(2026, 9, 27)) == 0.0


def test_effective_apr_promo_with_no_expiration_date_treated_as_expired():
    debt = _debt(interest_rate=24.99, promo_apr=0.0, promo_expires_date=None)
    assert effective_apr(debt, date(2026, 9, 27)) == 24.99


def test_days_until_promo_expires_none_when_no_promo():
    assert days_until_promo_expires(_debt(), date(2026, 9, 27)) is None


def test_days_until_promo_expires_real_count():
    debt = _debt(promo_apr=0.0, promo_expires_date="2026-10-07")
    assert days_until_promo_expires(debt, date(2026, 9, 27)) == 10


def test_rank_debts_avalanche_orders_by_highest_apr_first():
    low = Debt(debt_id="low", name="Low APR", balance=1000.0, interest_rate=5.0)
    high = Debt(debt_id="high", name="High APR", balance=1000.0, interest_rate=25.0)
    ranked = rank_debts([low, high], date(2026, 9, 27), strategy="avalanche")
    assert [p.debt.debt_id for p in ranked] == ["high", "low"]
    assert ranked[0].rank == 1


def test_rank_debts_snowball_orders_by_smallest_balance_first():
    small = Debt(debt_id="small", name="Small Balance", balance=500.0, interest_rate=25.0)
    large = Debt(debt_id="large", name="Large Balance", balance=5000.0, interest_rate=5.0)
    ranked = rank_debts([small, large], date(2026, 9, 27), strategy="snowball")
    assert [p.debt.debt_id for p in ranked] == ["small", "large"]


def test_rank_debts_hybrid_bumps_soon_expiring_promo_ahead_of_higher_apr():
    high_apr = Debt(debt_id="high", name="High APR", balance=1000.0, interest_rate=25.0)
    expiring_promo = Debt(
        debt_id="promo", name="Expiring Promo", balance=1000.0, interest_rate=25.0,
        promo_apr=0.0, promo_expires_date="2026-10-10",  # 13 days out, inside the urgency window
    )
    ranked = rank_debts([high_apr, expiring_promo], date(2026, 9, 27), strategy="hybrid")
    assert [p.debt.debt_id for p in ranked] == ["promo", "high"]
    assert "ends in 13d" in ranked[0].reason


def test_rank_debts_hybrid_ignores_promo_outside_urgency_window():
    high_apr = Debt(debt_id="high", name="High APR", balance=1000.0, interest_rate=25.0)
    far_promo = Debt(
        debt_id="promo", name="Far Promo", balance=1000.0, interest_rate=10.0,
        promo_apr=0.0, promo_expires_date="2027-06-01",  # well outside the urgency window
    )
    ranked = rank_debts([high_apr, far_promo], date(2026, 9, 27), strategy="hybrid")
    # Not urgent yet, so it's ranked by its own low effective (promo) APR — last, not first.
    assert [p.debt.debt_id for p in ranked] == ["high", "promo"]


def test_rank_debts_excludes_paid_off_debts():
    paid_off = Debt(debt_id="paid", name="Paid Off", balance=0.0, interest_rate=20.0)
    open_debt = Debt(debt_id="open", name="Open", balance=100.0, interest_rate=10.0)
    ranked = rank_debts([paid_off, open_debt], date(2026, 9, 27))
    assert [p.debt.debt_id for p in ranked] == ["open"]


def test_rank_debts_unknown_strategy_falls_back_to_hybrid():
    a = Debt(debt_id="a", name="A", balance=100.0, interest_rate=10.0)
    assert [p.debt.debt_id for p in rank_debts([a], date(2026, 9, 27), strategy="bogus")] == ["a"]


def test_add_debt_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_debt(name="Chase Freedom", balance=5000.0, interest_rate=24.99, minimum_payment=100.0)

    reloaded = _make_manager()
    assert len(reloaded.all_debts()) == 1
    assert reloaded.all_debts()[0].name == "Chase Freedom"


def test_add_debt_rejects_negative_balance(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.add_debt(name="Bad", balance=-1.0, interest_rate=10.0)


def test_add_debt_rejects_unknown_debt_type_falls_back_to_other(isolated_paths):
    manager = _make_manager()
    debt = manager.add_debt(name="Weird", balance=100.0, interest_rate=10.0, debt_type="Not A Real Type")
    assert debt.debt_type == "Other"


def test_add_debt_promo_apr_without_expiration_date_is_dropped(isolated_paths):
    manager = _make_manager()
    debt = manager.add_debt(name="X", balance=100.0, interest_rate=10.0, promo_apr=0.0, promo_expires_date=None)
    assert debt.promo_apr == 0.0
    assert debt.promo_expires_date is None


def test_update_debt_clears_promo_expires_date_when_promo_apr_cleared(isolated_paths):
    manager = _make_manager()
    debt = manager.add_debt(name="X", balance=100.0, interest_rate=10.0, promo_apr=0.0, promo_expires_date="2026-12-01")
    manager.update_debt(debt.debt_id, promo_apr=None)
    assert manager.get_debt(debt.debt_id).promo_expires_date is None


def test_delete_debt_removes_it(isolated_paths):
    manager = _make_manager()
    debt = manager.add_debt(name="X", balance=100.0, interest_rate=10.0)
    manager.delete_debt(debt.debt_id)
    assert manager.get_debt(debt.debt_id) is None


def test_record_debt_payment_creates_expense_and_reduces_balance(isolated_paths):
    manager = _make_manager()
    debt = manager.add_debt(name="Chase Freedom", balance=1000.0, interest_rate=24.99, minimum_payment=50.0)

    entry = manager.record_debt_payment(debt.debt_id, 200.0, date="2026-09-27")

    assert entry.amount == 200.0
    assert entry.category == "Debt Payment"
    assert entry.description == "Chase Freedom"
    updated = manager.get_debt(debt.debt_id)
    assert updated.balance == 800.0
    assert updated.last_payment_date == "2026-09-27"


def test_record_debt_payment_clamps_balance_at_zero_on_overpayment(isolated_paths):
    manager = _make_manager()
    debt = manager.add_debt(name="X", balance=100.0, interest_rate=10.0)
    manager.record_debt_payment(debt.debt_id, 500.0)
    assert manager.get_debt(debt.debt_id).balance == 0.0


def test_record_debt_payment_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.record_debt_payment("nonexistent", 100.0)


def test_debt_payoff_priority_reflects_manager_state(isolated_paths):
    manager = _make_manager()
    manager.add_debt(name="Low", balance=100.0, interest_rate=5.0)
    manager.add_debt(name="High", balance=100.0, interest_rate=25.0)

    ranked = manager.debt_payoff_priority(strategy="avalanche", today=date(2026, 9, 27))
    assert ranked[0].debt.name == "High"


def test_total_debt_balance_sums_open_debts(isolated_paths):
    manager = _make_manager()
    manager.add_debt(name="A", balance=100.0, interest_rate=10.0)
    manager.add_debt(name="B", balance=250.0, interest_rate=10.0)
    assert manager.total_debt_balance() == 350.0


def test_total_debt_balance_filters_by_entity(isolated_paths):
    manager = _make_manager()
    manager.add_debt(name="A", balance=100.0, interest_rate=10.0, entity_id="ent1")
    manager.add_debt(name="B", balance=250.0, interest_rate=10.0)
    assert manager.total_debt_balance(entity_id="ent1") == 100.0


def test_total_minimum_debt_payments_ignores_paid_off_debts(isolated_paths):
    manager = _make_manager()
    d1 = manager.add_debt(name="A", balance=100.0, interest_rate=10.0, minimum_payment=25.0)
    manager.add_debt(name="B", balance=50.0, interest_rate=10.0, minimum_payment=10.0)
    manager.record_debt_payment(d1.debt_id, 100.0)  # pays it off
    assert manager.total_minimum_debt_payments() == 10.0


def test_weighted_average_debt_apr_weights_by_balance(isolated_paths):
    manager = _make_manager()
    manager.add_debt(name="Small", balance=100.0, interest_rate=10.0)
    manager.add_debt(name="Large", balance=900.0, interest_rate=20.0)
    # (100*10 + 900*20) / 1000 = 19.0
    assert manager.weighted_average_debt_apr(today=date(2026, 9, 27)) == pytest.approx(19.0)


def test_weighted_average_debt_apr_zero_when_no_open_debt(isolated_paths):
    manager = _make_manager()
    assert manager.weighted_average_debt_apr() == 0.0
