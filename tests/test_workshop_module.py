"""
tests.test_workshop_module
=============================

Unit test for modules.workshop.module.format_component_row — pure
formatting logic, no Qt event loop needed. Same shape as
tests/test_notes_module.py's format_entry_row test.
"""

from __future__ import annotations

from core.component_manager import Component
from modules.workshop.module import format_component_row


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


def test_omits_location_when_absent():
    component = Component(component_id="abc123", name="Cap", category="Capacitor", quantity=1)
    assert format_component_row(component) == "Cap  [Capacitor]  qty 1"
