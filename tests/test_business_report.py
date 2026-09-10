"""
tests.test_business_report
=============================

Unit tests for core.business_report — no Qt, no manager instances, same
shape as tests/test_budget_nudges.py. Asserts on the literal returned
HTML string's real content rather than just "it doesn't crash."
"""

from __future__ import annotations

from core.budget_manager import BudgetTarget
from core.business_report import build_business_report_html, category_to_schedule_e_line


def _property(
    name="123 Main St", current_value=280000.0, mortgage_balance=150000.0, noi=12000.0, cap_rate=0.0429,
    annual_depreciation=8000.0,
):
    return {
        "name": name,
        "type": "Rental",
        "current_value": current_value,
        "mortgage_balance": mortgage_balance,
        "equity": current_value - mortgage_balance,
        "noi": noi,
        "cap_rate": cap_rate,
        "annual_depreciation": annual_depreciation,
    }


def _build(**overrides):
    args = dict(
        range_label="This Month",
        start_date="2026-09-01",
        end_date="2026-09-30",
        income_total=5000.0,
        expenses_total=3200.0,
        tax_income_total=5000.0,
        tax_expenses_total=1000.0,
        income_by_category={"Salary": 5000.0},
        expenses_by_category={"Groceries": 450.0, "Utilities": 120.0},
        budget_targets=[],
        actual_by_category={"Groceries": 450.0},
        properties=[],
        generated_at="2026-09-08 06:00",
    )
    args.update(overrides)
    return build_business_report_html(**args)


def test_includes_range_label_and_generated_at():
    html = _build(range_label="This Year", generated_at="2026-09-08 06:00")
    assert "This Year" in html
    assert "2026-09-08 06:00" in html


def test_includes_entity_label_when_given():
    html = _build(entity_label="Sunrise Rentals LLC")
    assert "Entity:" in html
    assert "Sunrise Rentals LLC" in html


def test_omits_entity_line_when_entity_label_is_none():
    html = _build(entity_label=None)
    assert "Entity:" not in html


def test_includes_household_summary_figures():
    html = _build(income_total=5000.0, expenses_total=3200.0)
    assert "$5,000.00" in html
    assert "$3,200.00" in html
    assert "$1,800.00" in html  # net cash flow


def test_income_by_category_table_lists_each_category_and_total():
    html = _build(income_by_category={"Salary": 3000.0, "Rental Income": 1500.0})
    assert "Salary" in html
    assert "Rental Income" in html
    assert "$4,500.00" in html  # total row


def test_expenses_by_category_table_lists_each_category_and_total():
    html = _build(expenses_by_category={"Groceries": 450.0, "Utilities": 100.0})
    assert "Groceries" in html
    assert "Utilities" in html
    assert "$550.00" in html  # total row


def test_empty_income_category_dict_shows_empty_state_not_dropped():
    html = _build(income_by_category={})
    assert "No income recorded for this range." in html


def test_empty_expenses_category_dict_shows_empty_state_not_dropped():
    html = _build(expenses_by_category={})
    assert "No expenses recorded for this range." in html


def test_property_row_includes_equity_noi_cap_rate():
    prop = _property(name="123 Main St", current_value=280000.0, mortgage_balance=150000.0, noi=12000.0, cap_rate=0.0429)
    html = _build(properties=[prop])
    assert "123 Main St" in html
    assert "$130,000" in html  # equity — whole-dollar in this table, see _money_whole()
    assert "$12,000" in html  # noi — also whole-dollar, see _portfolio_table()'s own comment on why
    assert "4.3%" in html  # cap rate


def test_property_row_includes_annual_depreciation():
    prop = _property(name="123 Main St", annual_depreciation=8181.82)
    html = _build(properties=[prop])
    assert "Annual" in html and "Depreciation" in html  # header renders as "Annual<br>Depreciation"
    assert "$8,181.82" in html


def test_portfolio_totals_row_sums_annual_depreciation():
    props = [
        _property(name="A", annual_depreciation=5000.0),
        _property(name="B", annual_depreciation=3000.0),
    ]
    html = _build(properties=props)
    assert "$8,000.00" in html  # total annual depreciation


def test_property_row_shows_dash_for_none_cap_rate():
    prop = _property(name="Vacant Lot", current_value=0.0, mortgage_balance=0.0, noi=0.0, cap_rate=None)
    html = _build(properties=[prop])
    assert "Vacant Lot" in html
    assert "—" in html


def test_portfolio_totals_row_sums_value_mortgage_equity():
    props = [
        _property(name="A", current_value=200000.0, mortgage_balance=100000.0, noi=8000.0, cap_rate=0.04),
        _property(name="B", current_value=100000.0, mortgage_balance=50000.0, noi=4000.0, cap_rate=0.04),
    ]
    html = _build(properties=props)
    assert "$300,000" in html  # total current value — whole-dollar in this table
    assert "$150,000" in html  # total mortgage balance
    assert "$150,000" in html  # total equity (also 150,000 here, both present)
    assert "$12,000" in html  # total noi — also whole-dollar


def test_no_properties_shows_empty_state():
    html = _build(properties=[])
    assert "No properties tracked." in html


def test_budget_targets_section_included_when_targets_passed():
    targets = [BudgetTarget(category="Groceries", monthly_amount=400.0)]
    html = _build(budget_targets=targets, actual_by_category={"Groceries": 450.0})
    assert "Budget Targets vs. Actual" in html
    assert "$400.00" in html
    assert "$450.00" in html


def test_budget_targets_section_omitted_when_no_targets_passed():
    html = _build(budget_targets=[])
    assert "Budget Targets vs. Actual" not in html


def test_multiple_properties_all_present():
    props = [_property(name="123 Main St"), _property(name="Lake Cabin", current_value=180000.0, mortgage_balance=90000.0)]
    html = _build(properties=props)
    assert "123 Main St" in html
    assert "Lake Cabin" in html


# ------------------------------------------------------------------
# category_to_schedule_e_line — pure mapping
# ------------------------------------------------------------------

def test_category_to_schedule_e_line_real_mappings():
    assert category_to_schedule_e_line("Insurance") == "Insurance"
    assert category_to_schedule_e_line("Maintenance") == "Repairs"
    assert category_to_schedule_e_line("Taxes") == "Taxes"
    assert category_to_schedule_e_line("Utilities") == "Utilities"
    assert category_to_schedule_e_line("Mortgage/Rent") == "Mortgage Interest"


def test_category_to_schedule_e_line_unmapped_falls_to_other():
    for category in ("Groceries", "Transportation", "Medical", "Personal Care", "Shopping", "Bank Fees", "Entertainment", "Travel", "Other"):
        assert category_to_schedule_e_line(category) == "Other"


# ------------------------------------------------------------------
# Schedule E section
# ------------------------------------------------------------------

def _schedule_e_property(name="123 Main St", rents_received=24000.0, expenses_by_category=None, depreciation=8181.82):
    return {
        "name": name,
        "rents_received": rents_received,
        "expenses_by_category": expenses_by_category or {"Insurance": 1200.0, "Maintenance": 800.0, "Groceries": 50.0},
        "depreciation": depreciation,
    }


def test_schedule_e_section_omitted_when_no_properties_passed():
    html = _build(range_label="This Year", schedule_e_properties=[])
    assert "Schedule E Summary" not in html


def test_schedule_e_section_shows_mapped_lines_and_totals():
    html = _build(range_label="This Year", schedule_e_properties=[_schedule_e_property()])
    assert "Schedule E Summary" in html
    assert "Rents Received" in html
    assert "$24,000.00" in html
    assert "Insurance" in html and "$1,200.00" in html
    assert "Repairs" in html and "$800.00" in html  # Maintenance -> Repairs
    assert "Depreciation" in html and "$8,181.82" in html
    # Groceries (50.0) maps to "Other" — its amount should still show under that line
    assert "Other" in html and "$50.00" in html
    total_expenses = 1200.0 + 800.0 + 50.0 + 8181.82
    assert f"${total_expenses:,.2f}" in html  # Total Expenses row
    net = 24000.0 - total_expenses
    assert f"${net:,.2f}" in html  # Net Income (Loss) row


def test_schedule_e_section_skips_zero_amount_lines():
    prop = _schedule_e_property(expenses_by_category={"Insurance": 1200.0}, depreciation=0.0)
    html = _build(range_label="This Year", schedule_e_properties=[prop])
    assert "Repairs" not in html
    assert "Taxes" not in html
    assert "Depreciation" not in html


def test_schedule_e_section_mentions_not_tax_advice_and_mortgage_caveat():
    html = _build(range_label="This Year", schedule_e_properties=[_schedule_e_property()])
    assert "not a computed tax liability" in html
    assert "principal/interest split" in html


def test_schedule_e_section_shows_a_loss_in_accounting_parens_not_a_minus_sign():
    prop = _schedule_e_property(rents_received=1000.0, expenses_by_category={"Insurance": 2000.0}, depreciation=0.0)
    html = _build(range_label="This Year", schedule_e_properties=[prop])
    assert "($1,000.00)" in html
    assert "$-1,000.00" not in html


def test_schedule_e_section_includes_property_name_heading():
    html = _build(range_label="This Year", schedule_e_properties=[_schedule_e_property(name="Lake Cabin")])
    assert "<h3>Lake Cabin</h3>" in html
