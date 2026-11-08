"""
tests.test_ohms_law
======================

Unit tests for Ohm's law solve() (core/toolbox_calcs.py; modules.toolbox.calculators.ohms_law re-exports it).
"""

from __future__ import annotations

import pytest

from core.toolbox_calcs import solve  # the math moved to core (the Qt calculator re-exports it)


def test_solve_voltage():
    """Voltage from current and resistance."""
    assert solve("voltage", None, current=2.0, resistance=5.0) == pytest.approx(10.0)


def test_solve_current():
    """Current from voltage and resistance."""
    assert solve("current", voltage=10.0, current=None, resistance=5.0) == pytest.approx(2.0)


def test_solve_resistance():
    """Resistance from voltage and current."""
    assert solve("resistance", voltage=10.0, current=2.0, resistance=None) == pytest.approx(5.0)


def test_solve_unknown_target_raises():
    with pytest.raises(ValueError):
        solve("power", voltage=10.0, current=2.0, resistance=None)


def test_solve_current_division_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        solve("current", voltage=10.0, current=None, resistance=0.0)


def test_solve_resistance_division_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        solve("resistance", voltage=10.0, current=0.0, resistance=None)
