"""
core.map_tile_cache
======================

Disk-backed cache for real basemap tiles — the actual "offline maps"
imagery gui/widgets/tile_map_view.py renders, unlike
gui/widgets/waypoint_map_canvas.py's schematic waypoint plot (which has
no basemap imagery at all, by design — see that module's docstring).

**Two tile sources, each scoped to a specific, deliberately-limited use:**

- **`"usgs_topo"`** (`basemap.nationalmap.gov`) — real topographic
  detail (shows trails, not just roads), US coverage only, public
  domain, a federal REST service meant for exactly this kind of
  programmatic/bulk use. This is what `ensure_region_cached()` uses for
  any region-specific high-detail prefetch (`DEFAULT_PREFETCH_ZOOM_LEVELS`).
- **`"osm"`** (`tile.openstreetmap.org`) — used *only* for the
  worldwide low-zoom overview (`WORLDWIDE_OVERVIEW_ZOOM_LEVELS`, zoom
  0-4, ~341 tiles/~5MB for the *entire planet*, measured directly
  before picking this range). OpenStreetMap's own tile usage policy
  explicitly prohibits bulk/systematic downloading for offline
  caching — a one-time ~5MB worldwide overview is the same order of
  magnitude as a single normal browsing session generates, not the
  kind of heavy/automated scraping that policy targets, but this
  source is deliberately never used for `DEFAULT_PREFETCH_ZOOM_LEVELS`-
  style deep regional caching, which *would* cross that line. There is
  currently no non-US equivalent of USGS's bulk-friendly service wired
  up here — high-detail offline coverage outside the US is a known,
  documented gap (`docs/ROADMAP.md`), not silently worked around by
  quietly overusing OSM's tile server.

Uses stdlib `urllib.request`, not the `requests` package — matches
`requirements.txt`'s own "keep this list minimal" stance; nothing here
needs more than a GET and a file write.

**Tile addressing wrinkle, confirmed directly against the live
service, not assumed from docs**: USGSTopo's ArcGIS REST tile endpoint
takes path segments in `{z}/{y}/{x}` order — the reverse of the more
common `{z}/{x}/{y}` XYZ convention `core.map_tile_math`'s own
functions use, this module's local cache path, and OSM's own tile URLs
all use. `_tile_url()` is the one place that reordering happens.
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

#: source name -> (URL template, local file extension). URL templates
#: always use {z}/{x}/{y} placeholders regardless of a given provider's
#: own path *order* — _tile_url() handles USGS's reversed order itself
#: rather than baking provider-specific quirks into every template.
TILE_SOURCES: dict[str, tuple[str, str]] = {
    "usgs_topo": ("https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}", "jpg"),
    "osm": ("https://tile.openstreetmap.org/{z}/{x}/{y}.png", "png"),
}

_REQUEST_TIMEOUT_SECONDS = 10
# A small pause between requests during a bulk region prefetch — being
# a reasonable citizen of a public service, even for USGS (no
# documented rate limit, unlike OSM's explicit policy).
_BULK_FETCH_DELAY_SECONDS = 0.05

#: A default, deliberately modest bulk-prefetch zoom range — state/
#: regional overview down to roughly county-visible detail (~557 tiles,
#: ~19MB combined for a Kentucky+Tennessee-sized bounding box, measured
#: directly before picking this range). Live panning/zooming can fetch
#: individual tiles beyond this range on demand — normal browsing use,
#: not the kind of bulk automated caching this range is scoped to avoid
#: overusing.
DEFAULT_PREFETCH_SOURCE = "usgs_topo"
DEFAULT_PREFETCH_ZOOM_LEVELS: tuple[int, ...] = (6, 7, 8, 9, 10)

#: The whole-planet low-zoom overview — see this module's own docstring
#: for why OSM is acceptable here specifically (small one-time volume)
#: but not for DEFAULT_PREFETCH_ZOOM_LEVELS-style deep caching.
WORLDWIDE_OVERVIEW_SOURCE = "osm"
WORLDWIDE_OVERVIEW_ZOOM_LEVELS: tuple[int, ...] = (0, 1, 2, 3, 4)
#: Web Mercator's own valid latitude range (the projection breaks down
#: past this, same reason core.map_tile_math's formulas never see
#: latitudes beyond it in practice) — used as "the whole world" bbox.
WORLDWIDE_BOUNDS: tuple[float, float, float, float] = (-85.0, -180.0, 85.0, 180.0)


class MapTileCache:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    # ------------------------------------------------------------------
    # Single-tile fetch/cache
    # ------------------------------------------------------------------

    def tile_path(self, source: str, zoom: int, x: int, y: int) -> Path:
        _, extension = TILE_SOURCES[source]
        return _TILE_CACHE_DIR / source / str(zoom) / str(x) / f"{y}.{extension}"

    def is_cached(self, source: str, zoom: int, x: int, y: int) -> bool:
        return self.tile_path(source, zoom, x, y).exists()

    def _tile_url(self, source: str, zoom: int, x: int, y: int) -> str:
        template, _ = TILE_SOURCES[source]
        return template.format(z=zoom, y=y, x=x)

    def fetch_tile(self, source: str, zoom: int, x: int, y: int) -> Path:
        """Returns the cached tile's path, downloading it first if not
        already cached. Raises urllib.error.URLError/HTTPError on a
        real network failure — callers decide how to handle that (a
        single missing tile shouldn't usually abort a whole region
        prefetch, see ensure_region_cached() below)."""
        path = self.tile_path(source, zoom, x, y)
        if path.exists():
            return path

        request = urllib.request.Request(self._tile_url(source, zoom, x, y), headers={"User-Agent": "MIA-Home/0.2"})
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
        source: str,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        zoom_levels: tuple[int, ...] = DEFAULT_PREFETCH_ZOOM_LEVELS,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """Fetches every not-yet-cached tile covering the given
        bounding box across zoom_levels, from the given source. A
        single tile's fetch failure is logged and skipped, not fatal to
        the whole batch — same graceful-degradation stance as this
        app's other network/hardware-dependent features. Returns how
        many tiles were newly fetched (already-cached ones don't
        count). on_progress(done, total), if given, is called after
        every tile (cached-already or freshly-fetched alike) so a
        caller can drive a progress bar."""
        all_tiles = [
            (zoom, x, y)
            for zoom in zoom_levels
            for x, y in tiles_covering_bbox(min_lat, min_lon, max_lat, max_lon, zoom)
        ]
        total = len(all_tiles)
        fetched_count = 0

        for index, (zoom, x, y) in enumerate(all_tiles, start=1):
            already_cached = self.is_cached(source, zoom, x, y)
            if not already_cached:
                try:
                    self.fetch_tile(source, zoom, x, y)
                    fetched_count += 1
                    time.sleep(_BULK_FETCH_DELAY_SECONDS)
                except (urllib.error.URLError, OSError):
                    log.warning(
                        "Failed to fetch map tile source=%s z=%s x=%s y=%s — skipping.",
                        source, zoom, x, y, exc_info=True,
                    )
            if on_progress is not None:
                on_progress(index, total)

        return fetched_count
