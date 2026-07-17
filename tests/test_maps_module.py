"""
tests.test_maps_module
==========================

Unit tests for modules.maps.module's pure functions, same style as
tests/test_navigation_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from modules.maps.module import format_distance_bearing_line


def test_format_distance_bearing_line():
    assert format_distance_bearing_line(12.34, 47.0) == "12.3 km  —  bearing 047°"


def test_format_distance_bearing_line_rounds_bearing_to_three_digits():
    assert format_distance_bearing_line(0.5, 359.6) == "0.5 km  —  bearing 360°"


def test_format_distance_bearing_line_zero_distance():
    assert format_distance_bearing_line(0.0, 0.0) == "0.0 km  —  bearing 000°"
