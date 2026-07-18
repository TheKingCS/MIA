"""
tests.test_maps_module
==========================

Unit tests for modules.maps.module's pure functions, same style as
tests/test_navigation_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from modules.maps.module import format_distance_bearing_line, format_tile_count_estimate


def test_format_distance_bearing_line():
    assert format_distance_bearing_line(12.34, 47.0) == "12.3 km  —  bearing 047°"


def test_format_distance_bearing_line_rounds_bearing_to_three_digits():
    assert format_distance_bearing_line(0.5, 359.6) == "0.5 km  —  bearing 360°"


def test_format_distance_bearing_line_zero_distance():
    assert format_distance_bearing_line(0.0, 0.0) == "0.0 km  —  bearing 000°"


def test_format_tile_count_estimate_reports_tile_count_and_size():
    estimate = format_tile_count_estimate(34.98, -90.35, 39.15, -81.6, zoom_levels=(6, 7))
    assert "tiles" in estimate
    assert "MB" in estimate


def test_format_tile_count_estimate_grows_with_more_zoom_levels():
    small = format_tile_count_estimate(34.98, -90.35, 39.15, -81.6, zoom_levels=(6,))
    large = format_tile_count_estimate(34.98, -90.35, 39.15, -81.6, zoom_levels=(6, 7, 8, 9, 10))

    def _extract_tile_count(estimate: str) -> int:
        return int(estimate.split(" tiles")[0].lstrip("~"))

    assert _extract_tile_count(large) > _extract_tile_count(small)
