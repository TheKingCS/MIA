"""
tests.test_map_tile_math
============================

Unit tests for core.map_tile_math — pure coordinate math, no network/Qt.
"""

from __future__ import annotations

import pytest

from core.map_tile_math import (
    lat_lon_to_tile_xy,
    lat_lon_to_world_pixel,
    tile_xy_to_lat_lon,
    tiles_covering_bbox,
    world_pixel_to_lat_lon,
)


def test_null_island_at_zoom_0_is_tile_0_0():
    assert lat_lon_to_tile_xy(0.0, 0.0, zoom=0) == (0, 0)


def test_tile_count_doubles_per_axis_each_zoom_level():
    # A point comfortably inside the grid (not on a tile boundary)
    # should map to roughly double the tile index one zoom level up.
    x5, y5 = lat_lon_to_tile_xy(40.0, -85.0, zoom=5)
    x6, y6 = lat_lon_to_tile_xy(40.0, -85.0, zoom=6)
    assert x6 in (2 * x5, 2 * x5 + 1)
    assert y6 in (2 * y5, 2 * y5 + 1)


def test_coordinates_are_clamped_within_the_grid():
    x, y = lat_lon_to_tile_xy(89.9, 179.9, zoom=3)
    n = 2 ** 3
    assert 0 <= x < n
    assert 0 <= y < n


def test_tile_xy_to_lat_lon_is_the_approximate_inverse():
    zoom = 8
    original_lat, original_lon = 36.5, -85.0
    x, y = lat_lon_to_tile_xy(original_lat, original_lon, zoom)
    lat, lon = tile_xy_to_lat_lon(x, y, zoom)
    # The tile's own corner won't exactly equal the original point (a
    # tile covers an area), but must be within one tile-width of it.
    tile_degrees = 360.0 / (2 ** zoom)
    assert abs(lat - original_lat) <= tile_degrees
    assert abs(lon - original_lon) <= tile_degrees


def test_tiles_covering_bbox_returns_a_rectangular_grid():
    tiles = tiles_covering_bbox(min_lat=35.0, min_lon=-87.0, max_lat=37.0, max_lon=-84.0, zoom=8)
    xs = {x for x, _ in tiles}
    ys = {y for _, y in tiles}
    assert len(tiles) == len(xs) * len(ys)


def test_tiles_covering_bbox_includes_single_tile_for_a_tiny_area():
    tiles = tiles_covering_bbox(min_lat=36.5, min_lon=-85.5, max_lat=36.51, max_lon=-85.49, zoom=4)
    assert len(tiles) == 1


def test_tiles_covering_bbox_grows_with_zoom():
    low_zoom = tiles_covering_bbox(34.98, -90.35, 39.15, -81.6, zoom=6)
    high_zoom = tiles_covering_bbox(34.98, -90.35, 39.15, -81.6, zoom=9)
    assert len(high_zoom) > len(low_zoom)


# ----------------------------------------------------------------------
# Continuous world-pixel projection (pan/zoom math)
# ----------------------------------------------------------------------

def test_world_pixel_round_trips_through_its_inverse():
    original_lat, original_lon = 36.5, -85.0
    zoom = 10
    x, y = lat_lon_to_world_pixel(original_lat, original_lon, zoom)
    lat, lon = world_pixel_to_lat_lon(x, y, zoom)
    assert lat == pytest.approx(original_lat, abs=1e-6)
    assert lon == pytest.approx(original_lon, abs=1e-6)


def test_world_pixel_x_doubles_per_zoom_level_for_a_fixed_point():
    lon = -85.0
    x_at_9, _ = lat_lon_to_world_pixel(36.5, lon, zoom=9)
    x_at_10, _ = lat_lon_to_world_pixel(36.5, lon, zoom=10)
    assert x_at_10 == pytest.approx(2 * x_at_9)


def test_world_pixel_east_is_greater_x_than_west():
    x_east, _ = lat_lon_to_world_pixel(36.5, -80.0, zoom=8)
    x_west, _ = lat_lon_to_world_pixel(36.5, -90.0, zoom=8)
    assert x_east > x_west


def test_world_pixel_north_is_smaller_y_than_south():
    _, y_north = lat_lon_to_world_pixel(40.0, -85.0, zoom=8)
    _, y_south = lat_lon_to_world_pixel(30.0, -85.0, zoom=8)
    assert y_north < y_south
