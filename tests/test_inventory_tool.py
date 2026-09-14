"""
tests.test_inventory_tool
============================

Unit test for modules.toolbox.tools.inventory_tool.format_item_row —
pure formatting logic, no Qt event loop needed.
"""

from __future__ import annotations

from core.inventory_manager import InventoryItem
from modules.toolbox.tools.inventory_tool import format_item_detail_line, format_item_row


def test_formats_name_and_quantity_only():
    item = InventoryItem(item_id="i1", name="Duct Tape", quantity=3)
    assert format_item_row(item) == "Duct Tape  —  qty 3"


def test_includes_category_when_present():
    item = InventoryItem(item_id="i1", name="Widget", quantity=2, category="Electronics")
    assert format_item_row(item) == "Widget  —  qty 2  [Electronics]"


def test_includes_location_when_present():
    item = InventoryItem(item_id="i1", name="Widget", quantity=2, location="Shelf A")
    assert format_item_row(item) == "Widget  —  qty 2  @ Shelf A"


def test_includes_category_and_location_together():
    item = InventoryItem(item_id="i1", name="Widget", quantity=2, category="Electronics", location="Shelf A")
    assert format_item_row(item) == "Widget  —  qty 2  [Electronics]  @ Shelf A"


# ------------------------------------------------------------------
# format_item_detail_line (multi-user pass, 2026-09-14)
# ------------------------------------------------------------------

def test_detail_line_unknown_attribution_and_never_used():
    assert format_item_detail_line(None, 0, None, None) == "Added by: unknown  ·  Never used yet"


def test_detail_line_with_attribution_and_never_used():
    assert format_item_detail_line("Alex", 0, None, None) == "Added by Alex  ·  Never used yet"


def test_detail_line_with_usage_and_who_last_used_it():
    result = format_item_detail_line("Alex", 3, "Faith", "2026-09-14")
    assert result == "Added by Alex  ·  Used 3x (last: Faith on 2026-09-14)"


def test_detail_line_with_usage_but_unknown_last_user():
    """last_used_by_name can be None (e.g. an unattributed usage event)
    while a real date is still known — the date alone is still real,
    useful information, so it isn't dropped just because the name is."""
    result = format_item_detail_line("Alex", 1, None, "2026-09-14")
    assert result == "Added by Alex  ·  Used 1x (last: 2026-09-14)"
