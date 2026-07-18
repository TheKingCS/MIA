"""
core.map_tile_cache
======================

Disk-backed cache for real basemap tiles — the actual "offline maps"
imagery gui/widgets/tile_map_view.py renders, unlike
gui/widgets/waypoint_map_canvas.py's schematic waypoint plot (which has
no basemap imagery at all, by design — see that module's docstring).

**Tile source: USGS National Map "USGSTopo"**
(`basemap.nationalmap.gov`) rather than OpenStreetMap's own tile
server — confirmed reachable directly (`curl`) before writing any code
against it. Two concrete reasons, not just a coin flip: (1) USGSTopo is
a real topographic map that shows trails, not just roads — directly
matches "trail maps," where a plain roads-only basemap wouldn't. (2)
OpenStreetMap's tile usage policy explicitly prohibits bulk/automated
downloading for offline caching — exactly what `ensure_region_cached()`
below does — while USGS's National Map REST tile service is a public
federal government service meant for this kind of programmatic use, no
API key required, tiles are public domain.

Uses stdlib `urllib.request`, not the `requests` package — matches
`requirements.txt`'s own "keep this list minimal" stance; nothing here
needs more than a GET and a file write.

**Tile addressing wrinkle, confirmed directly against the live
service, not assumed from docs**: USGSTopo's ArcGIS REST tile endpoint
takes path segments in `{z}/{y}/{x}` order — the reverse of the more
common `{z}/{x}/{y}` XYZ convention `core.map_tile_math`'s own
functions use and this module's local cache path/most other tile
providers use. `_tile_url()` is the one place that reordering happens.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.map_tile_math import tiles_covering_bbox

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TILE_CACHE_DIR = _DATA_DIR / "map_tiles"

_TILE_URL_TEMPLATE = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}"
_REQUEST_TIMEOUT_SECONDS = 10
# A small pause between requests during a bulk region prefetch — being
# a reasonable citizen of a public government service, even though it
# has no documented rate limit the way OSM's policy explicitly does.
_BULK_FETCH_DELAY_SECONDS = 0.05

#: A default, deliberately modest bulk-prefetch zoom range — state/
#: regional overview down to roughly county-visible detail (~557 tiles,
#: ~19MB combined for a Kentucky+Tennessee-sized bounding box, measured
#: directly before picking this range). Live panning/zooming can fetch
#: individual tiles beyond this range on demand — normal browsing use,
#: not the kind of bulk automated caching USGS's range is scoped to
#: avoid overusing.
DEFAULT_PREFETCH_ZOOM_LEVELS: tuple[int, ...] = (6, 7, 8, 9, 10)


class MapTileCache:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    # ------------------------------------------------------------------
    # Single-tile fetch/cache
    # ------------------------------------------------------------------

    def tile_path(self, zoom: int, x: int, y: int) -> Path:
        return _TILE_CACHE_DIR / str(zoom) / str(x) / f"{y}.jpg"

    def is_cached(self, zoom: int, x: int, y: int) -> bool:
        return self.tile_path(zoom, x, y).exists()

    def _tile_url(self, zoom: int, x: int, y: int) -> str:
        return _TILE_URL_TEMPLATE.format(z=zoom, y=y, x=x)

    def fetch_tile(self, zoom: int, x: int, y: int) -> Path:
        """Returns the cached tile's path, downloading it first if not
        already cached. Raises urllib.error.URLError/HTTPError on a
        real network failure — callers decide how to handle that (a
        single missing tile shouldn't usually abort a whole region
        prefetch, see ensure_region_cached() below)."""
        path = self.tile_path(zoom, x, y)
        if path.exists():
            return path

        request = urllib.request.Request(self._tile_url(zoom, x, y), headers={"User-Agent": "MIA-Home/0.2"})
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            data = response.read()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    # ------------------------------------------------------------------
    # Bulk region prefetch — the explicit, user-initiated "download this
    # area for offline use" action (never run automatically/silently).
    # ------------------------------------------------------------------

    def ensure_region_cached(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        zoom_levels: tuple[int, ...] = DEFAULT_PREFETCH_ZOOM_LEVELS,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """Fetches every not-yet-cached tile covering the given
        bounding box across zoom_levels. A single tile's fetch failure
        is logged and skipped, not fatal to the whole batch — same
        graceful-degradation stance as this app's other network/
        hardware-dependent features. Returns how many tiles were newly
        fetched (already-cached ones don't count). on_progress(done,
        total), if given, is called after every tile (cached-already or
        freshly-fetched alike) so a caller can drive a progress bar."""
        all_tiles = [
            (zoom, x, y)
            for zoom in zoom_levels
            for x, y in tiles_covering_bbox(min_lat, min_lon, max_lat, max_lon, zoom)
        ]
        total = len(all_tiles)
        fetched_count = 0

        for index, (zoom, x, y) in enumerate(all_tiles, start=1):
            already_cached = self.is_cached(zoom, x, y)
            if not already_cached:
                try:
                    self.fetch_tile(zoom, x, y)
                    fetched_count += 1
                    time.sleep(_BULK_FETCH_DELAY_SECONDS)
                except (urllib.error.URLError, OSError):
                    log.warning("Failed to fetch map tile z=%s x=%s y=%s — skipping.", zoom, x, y, exc_info=True)
            if on_progress is not None:
                on_progress(index, total)

        return fetched_count
