"""
tests.test_waypoint_map_canvas
==================================

Unit tests for gui.widgets.waypoint_map_canvas's project_waypoints() —
pure math, no Qt/QWidget instantiation needed. See that module's own
docstring for why this is a schematic layout, not a real map projection.
"""

from __future__ import annotations

from gui.widgets.waypoint_map_canvas import project_waypoints


def test_empty_points_returns_empty_dict():
    assert project_waypoints([], width=400, height=300) == {}


def test_single_point_is_centered():
    positions = project_waypoints([("a", 10.0, 20.0)], width=400, height=300)
    assert positions == {"a": (200.0, 150.0)}


def test_two_points_with_identical_coordinates_are_both_centered():
    positions = project_waypoints([("a", 5.0, 5.0), ("b", 5.0, 5.0)], width=400, height=300)
    assert positions["a"] == (200.0, 150.0)
    assert positions["b"] == (200.0, 150.0)


def test_north_point_is_above_south_point_on_screen():
    """Screen y grows downward, but north should still read as "up" —
    a higher latitude must produce a smaller y."""
    positions = project_waypoints([("north", 10.0, 0.0), ("south", 0.0, 0.0)], width=400, height=300)
    assert positions["north"][1] < positions["south"][1]


def test_east_point_is_right_of_west_point_on_screen():
    positions = project_waypoints([("east", 0.0, 10.0), ("west", 0.0, 0.0)], width=400, height=300)
    assert positions["east"][0] > positions["west"][0]


def test_all_points_fit_within_padded_bounds():
    points = [("a", 0.0, 0.0), ("b", 45.0, 90.0), ("c", -30.0, -60.0)]
    positions = project_waypoints(points, width=400, height=300, padding=20.0)
    for x, y in positions.values():
        assert 20.0 - 1e-6 <= x <= 380.0 + 1e-6
        assert 20.0 - 1e-6 <= y <= 280.0 + 1e-6


def test_relative_shape_is_not_stretched_per_axis():
    """A square lat/lon span in a non-square canvas should scale
    uniformly (same scale factor for both axes), not stretch to fill
    the whole box — otherwise relative distances would visibly distort."""
    points = [("a", 0.0, 0.0), ("b", 10.0, 0.0), ("c", 0.0, 10.0)]
    positions = project_waypoints(points, width=800, height=200, padding=0.0)
    # a->b is a pure latitude (vertical) span of 10 degrees; a->c is a
    # pure longitude (horizontal) span of 10 degrees. Equal degree spans
    # must map to equal pixel spans under a single shared scale factor.
    vertical_span = abs(positions["b"][1] - positions["a"][1])
    horizontal_span = abs(positions["c"][0] - positions["a"][0])
    assert vertical_span == horizontal_span
