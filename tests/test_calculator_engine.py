"""
tests.test_calculator_engine
===============================

Unit tests for core.calculator_engine.CalculatorEngine.
"""

from __future__ import annotations

import pytest

from core.calculator_engine import CalculatorEngine, CalculatorPlugin


class _FakeCalculator(CalculatorPlugin):
    def __init__(self, calculator_id: str, display_name: str, category: str = "General"):
        self.calculator_id = calculator_id
        self.display_name = display_name
        self.category = category
        self.description = f"{display_name} description"

    def build_widget(self):
        return None


def test_register_and_get():
    engine = CalculatorEngine()
    calc = _FakeCalculator("ohms_law", "Ohm's Law")
    engine.register(calc)

    assert engine.get("ohms_law") is calc


def test_get_unknown_returns_none():
    engine = CalculatorEngine()
    assert engine.get("does_not_exist") is None


def test_duplicate_calculator_id_raises():
    engine = CalculatorEngine()
    engine.register(_FakeCalculator("dup", "First"))
    with pytest.raises(ValueError):
        engine.register(_FakeCalculator("dup", "Second"))


def test_all_returns_sorted_by_display_name():
    engine = CalculatorEngine()
    engine.register(_FakeCalculator("b", "Zebra Calc"))
    engine.register(_FakeCalculator("a", "Alpha Calc"))

    names = [c.display_name for c in engine.all()]
    assert names == ["Alpha Calc", "Zebra Calc"]


def test_by_category_groups_correctly():
    engine = CalculatorEngine()
    engine.register(_FakeCalculator("unit_converter", "Unit Converter", category="General"))
    engine.register(_FakeCalculator("ohms_law", "Ohm's Law", category="Electronics"))
    engine.register(_FakeCalculator("wire_gauge", "Wire Gauge", category="Electronics"))

    grouped = engine.by_category()

    assert set(grouped.keys()) == {"General", "Electronics"}
    assert [c.display_name for c in grouped["Electronics"]] == ["Ohm's Law", "Wire Gauge"]
    assert [c.display_name for c in grouped["General"]] == ["Unit Converter"]


def test_by_category_empty_engine_returns_empty_dict():
    engine = CalculatorEngine()
    assert engine.by_category() == {}
