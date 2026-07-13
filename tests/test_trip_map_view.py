"""
tests.test_trip_map_view
===========================

Unit tests for gui.trip_map_view's pure functions (project_to_scene_xy,
compute_bounds), same style as tests/test_navigation_module.py — no Qt
event loop, no QGraphicsScene/View instantiated.
"""

from __future__ import annotations

import pytest

from core.waypoint_manager import Waypoint
from gui.trip_map_view import compute_bounds, project_to_scene_xy


def test_compute_bounds_over_multiple_waypoints():
    waypoints = [
        Waypoint(waypoint_id="a", name="A", latitude=10.0, longitude=-5.0),
        Waypoint(waypoint_id="b", name="B", latitude=20.0, longitude=5.0),
    ]
    assert compute_bounds(waypoints) == (10.0, 20.0, -5.0, 5.0)


def test_project_min_lon_min_lat_maps_to_bottom_left():
    bounds = (0.0, 10.0, 0.0, 10.0)
    x, y = project_to_scene_xy(latitude=0.0, longitude=0.0, bounds=bounds, scale=100.0)
    assert x == pytest.approx(0.0)
    assert y == pytest.approx(100.0)  # min latitude is at the bottom (y inverted, north is up)


def test_project_max_lon_max_lat_maps_to_top_right():
    bounds = (0.0, 10.0, 0.0, 10.0)
    x, y = project_to_scene_xy(latitude=10.0, longitude=10.0, bounds=bounds, scale=100.0)
    assert x == pytest.approx(100.0)
    assert y == pytest.approx(0.0)  # max latitude is at the top


def test_project_midpoint_maps_to_center():
    bounds = (0.0, 10.0, 0.0, 10.0)
    x, y = project_to_scene_xy(latitude=5.0, longitude=5.0, bounds=bounds, scale=100.0)
    assert x == pytest.approx(50.0)
    assert y == pytest.approx(50.0)


def test_project_zero_width_bounds_maps_to_center_without_dividing_by_zero():
    # All points share the same longitude (and/or latitude) — a real
    # edge case for a route confined to a single north-south trail.
    bounds = (5.0, 5.0, 5.0, 5.0)
    x, y = project_to_scene_xy(latitude=5.0, longitude=5.0, bounds=bounds, scale=100.0)
    assert x == pytest.approx(50.0)
    assert y == pytest.approx(50.0)
