"""
core.maps_web
===============

Maps' web screen (web/maps.html): the basemap tiles the desktop keeps
offline (core/map_tile_cache.py), with the waypoints on top. A tile is
served from the cache; one that isn't cached is fetched once and kept, by
the cache's own rules (the same as viewing the map on the desktop):

- **USGS topo** for detail, zoom 0 to MAX_ZOOM (a federal service meant for
  this; US coverage);
- **OpenStreetMap** only for the world overview, zoom 0 to 4 (its tile
  policy forbids bulk use beyond what a normal browse fetches).

Offline, a tile that was never cached is simply missing. Nothing about the
person goes out: a tile's address is all a server sees.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

MAX_ZOOM = 16
OSM_MAX_ZOOM = 4
CENTER = (39.5, -98.35)  # the middle of the contiguous US, when there are no waypoints


def allowed(source: str, z: int, x: int, y: int) -> bool:
    """Pure logic. A tile address the map may ask for."""
    from core.map_tile_cache import TILE_SOURCES

    if source not in TILE_SOURCES or not 0 <= z <= (OSM_MAX_ZOOM if source == "osm" else MAX_ZOOM):
        return False
    return 0 <= x < 2 ** z and 0 <= y < 2 ** z


def tile(context, source: str, z: int, x: int, y: int) -> Optional[Path]:
    """The tile's file, from the cache or fetched once and kept; None when it isn't allowed or can't be had."""
    cache = getattr(context, "map_tiles", None)
    if cache is None or not allowed(source, z, x, y):
        return None
    path = cache.tile_path(source, z, x, y)
    if path.exists():
        return path
    try:
        return cache.fetch_tile(source, z, x, y)
    except Exception:  # offline, or the service didn't answer: no tile, never an error page
        return None


def screen(context) -> dict:
    book = getattr(context, "waypoints", None)
    points = book.all_waypoints() if book is not None else []
    shown = [{"id": w.waypoint_id, "name": w.name, "category": w.category, "lat": w.latitude, "lon": w.longitude}
             for w in points]
    if shown:
        center = (sum(p["lat"] for p in shown) / len(shown), sum(p["lon"] for p in shown) / len(shown))
    else:
        center = CENTER
    return {"waypoints": shown, "center": {"lat": round(center[0], 5), "lon": round(center[1], 5)},
            "zoom": 12 if shown else 4, "max_zoom": MAX_ZOOM, "osm_max_zoom": OSM_MAX_ZOOM}
