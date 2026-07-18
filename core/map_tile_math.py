"""
core.map_tile_math
=====================

Pure Web Mercator "slippy map" tile-numbering math — the same
addressing scheme every standard XYZ/ArcGIS tile provider uses (OSM,
USGS National Map, etc.), documented publicly as the OSM wiki's
"Slippy map tilenames" formulas. Kept separate from
core/map_tile_cache.py (which adds real network I/O/disk caching on
top) so the coordinate math itself is trivially unit-testable.
"""

from __future__ import annotations

import math


def lat_lon_to_tile_xy(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """The tile (x, y) containing the given lat/lon at the given zoom level."""
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y


def tile_xy_to_lat_lon(x: int, y: int, zoom: int) -> tuple[float, float]:
    """The lat/lon of tile (x, y)'s north-west (top-left) corner — the
    inverse of lat_lon_to_tile_xy()."""
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def lat_lon_to_world_pixel(lat: float, lon: float, zoom: int, tile_size: int = 256) -> tuple[float, float]:
    """Continuous (non-tile-snapped) pixel coordinates in "world space"
    at the given zoom — gui/widgets/tile_map_view.py's pan/zoom math
    needs a smooth coordinate space, not one snapped to whole tiles the
    way lat_lon_to_tile_xy() is."""
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n * tile_size
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * tile_size
    return x, y


def world_pixel_to_lat_lon(x: float, y: float, zoom: int, tile_size: int = 256) -> tuple[float, float]:
    """Inverse of lat_lon_to_world_pixel()."""
    n = 2 ** zoom
    lon = x / (n * tile_size) * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / (n * tile_size))))
    lat = math.degrees(lat_rad)
    return lat, lon


def tiles_covering_bbox(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float, zoom: int
) -> list[tuple[int, int]]:
    """Every (x, y) tile coordinate whose area overlaps the given
    bounding box at the given zoom level."""
    x1, y1 = lat_lon_to_tile_xy(max_lat, min_lon, zoom)  # north-west corner
    x2, y2 = lat_lon_to_tile_xy(min_lat, max_lon, zoom)  # south-east corner
    x_min, x_max = min(x1, x2), max(x1, x2)
    y_min, y_max = min(y1, y2), max(y1, y2)
    return [(x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)]
