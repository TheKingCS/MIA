"""
tests.test_inventory_tool
============================

Unit test for modules.toolbox.tools.inventory_tool.format_item_row —
pure formatting logic, no Qt event loop needed.
"""

from __future__ import annotations

from core.inventory_manager import InventoryItem
from modules.toolbox.tools.inventory_tool import format_item_row


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
