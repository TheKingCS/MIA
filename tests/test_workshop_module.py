"""
tests.test_workshop_module
=============================

Unit tests for modules.workshop.module's pure formatting logic — no Qt
event loop needed. Same shape as tests/test_notes_module.py's
format_entry_row test. format_component_row() covers Components (the
original tab); format_material_row()/format_job_row()/
format_product_row()/format_revenue_row()/format_expense_row() cover
the four MIA Home production-pipeline tabs added 2026-07-16.
"""

from __future__ import annotations

from core.component_manager import Component
from core.job_manager import Job
from core.ledger_manager import ExpenseEntry, RevenueEntry
from core.material_manager import Material
from core.product_manager import Product, ProductListing
from modules.workshop.module import (
    format_component_detail_line,
    format_component_row,
    format_expense_row,
    format_job_row,
    format_material_row,
    format_product_row,
    format_revenue_row,
)


def test_formats_full_details():
    component = Component(
        component_id="abc123",
        name="Resistor",
        category="Resistor",
        value="10k",
        package="THT",
        quantity=50,
        location="Bin A3",
    )
    assert format_component_row(component) == "Resistor  [Resistor, 10k, THT]  qty 50  (Bin A3)"


def test_omits_missing_detail_fields():
    component = Component(component_id="abc123", name="Mystery Part", quantity=3)
    assert format_component_row(component) == "Mystery Part  qty 3"


# ------------------------------------------------------------------
# format_component_detail_line (multi-user pass, 2026-09-14)
# ------------------------------------------------------------------

def test_detail_line_unknown_attribution_and_never_used():
    assert format_component_detail_line(None, 0, None, None) == "Added by: unknown  ·  Never used yet"


def test_detail_line_with_attribution_and_never_used():
    assert format_component_detail_line("Alex", 0, None, None) == "Added by Alex  ·  Never used yet"


def test_detail_line_with_usage_and_who_last_used_it():
    result = format_component_detail_line("Alex", 3, "Faith", "2026-09-14")
    assert result == "Added by Alex  ·  Used 3x (last: Faith on 2026-09-14)"


def test_detail_line_with_usage_but_unknown_last_user():
    result = format_component_detail_line("Alex", 1, None, "2026-09-14")
    assert result == "Added by Alex  ·  Used 1x (last: 2026-09-14)"


def test_omits_location_when_absent():
    component = Component(component_id="abc123", name="Cap", category="Capacitor", quantity=1)
    assert format_component_row(component) == "Cap  [Capacitor]  qty 1"


# ----------------------------------------------------------------------
# format_material_row
# ----------------------------------------------------------------------

def test_format_material_row_well_stocked():
    material = Material(
        material_id="m1", name="Plywood", unit="sheet", unit_cost=10.0,
        quantity_on_hand=12, reorder_threshold=3,
    )
    assert format_material_row(material) == "Plywood  —  12 sheet on hand  —  $10.00/sheet"


def test_format_material_row_flags_low_stock():
    material = Material(
        material_id="m1", name="Filament", unit="spool", unit_cost=25.0,
        quantity_on_hand=2, reorder_threshold=5,
    )
    assert format_material_row(material) == "Filament  —  2 spool on hand  —  $25.00/spool  ⚠ LOW STOCK"


def test_format_material_row_no_unit_falls_back_to_word_unit():
    material = Material(material_id="m1", name="Widget", unit_cost=1.0, quantity_on_hand=5, reorder_threshold=1)
    assert format_material_row(material) == "Widget  —  5 on hand  —  $1.00/unit"


# ----------------------------------------------------------------------
# format_job_row
# ----------------------------------------------------------------------

def test_format_job_row():
    job = Job(job_id="j1", name="Engrave 20 coasters", status="In Progress", labor_hours=2.5)
    assert format_job_row(job) == "Engrave 20 coasters  [In Progress]  —  2.5 labor hrs"


# ----------------------------------------------------------------------
# format_product_row
# ----------------------------------------------------------------------

def test_format_product_row_no_listings():
    product = Product(product_id="p1", name="Coaster Set", quantity_in_stock=10, base_price=25.0)
    assert format_product_row(product) == "Coaster Set  —  10 in stock  —  $25.00 base"


def test_format_product_row_with_listings():
    product = Product(
        product_id="p1", name="Coaster Set", quantity_in_stock=10, base_price=25.0,
        listings=[ProductListing(listing_id="l1", platform="Etsy"), ProductListing(listing_id="l2", platform="Web")],
    )
    assert format_product_row(product) == "Coaster Set  —  10 in stock  —  $25.00 base  —  2 listings"


def test_format_product_row_singular_listing():
    product = Product(
        product_id="p1", name="X", listings=[ProductListing(listing_id="l1", platform="Etsy")],
    )
    assert "1 listing" in format_product_row(product)
    assert "1 listings" not in format_product_row(product)


# ----------------------------------------------------------------------
# format_revenue_row / format_expense_row
# ----------------------------------------------------------------------

def test_format_revenue_row_with_description():
    entry = RevenueEntry(entry_id="r1", amount=45.0, description="Etsy order", date="2026-07-16")
    assert format_revenue_row(entry) == "2026-07-16  —  $45.00  —  Etsy order"


def test_format_revenue_row_without_description():
    entry = RevenueEntry(entry_id="r1", amount=45.0, date="2026-07-16")
    assert format_revenue_row(entry) == "2026-07-16  —  $45.00"


def test_format_expense_row():
    entry = ExpenseEntry(entry_id="e1", amount=45.0, category="Materials", description="Plywood restock", date="2026-07-16")
    assert format_expense_row(entry) == "2026-07-16  —  $45.00  [Materials]  —  Plywood restock"
