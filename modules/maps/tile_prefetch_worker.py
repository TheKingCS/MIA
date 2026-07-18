"""
modules.maps.tile_prefetch_worker
====================================

Runs core.map_tile_cache.MapTileCache.ensure_region_cached() off the
GUI thread — the explicit, user-initiated "download this region for
offline use" action can fetch hundreds of tiles and take real time, so
this is the same one-shot QThread-per-run pattern as
modules/field_kit/script_worker.py's ScriptWorker, distinct from this
package's own TileFetchWorker (a persistent queue-processor for
individual on-demand tiles during live panning, not a single bulk job
with a progress bar).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core.map_tile_cache import DEFAULT_PREFETCH_ZOOM_LEVELS, MapTileCache


class TilePrefetchWorker(QThread):
    progress = Signal(int, int)  # done, total
    finished_prefetch = Signal(int)  # count of newly fetched tiles

    def __init__(
        self,
        tile_cache: MapTileCache,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        zoom_levels: tuple[int, ...] = DEFAULT_PREFETCH_ZOOM_LEVELS,
    ) -> None:
        super().__init__()
        self._tile_cache = tile_cache
        self._min_lat = min_lat
        self._min_lon = min_lon
        self._max_lat = max_lat
        self._max_lon = max_lon
        self._zoom_levels = zoom_levels

    def run(self) -> None:
        count = self._tile_cache.ensure_region_cached(
            self._min_lat,
            self._min_lon,
            self._max_lat,
            self._max_lon,
            self._zoom_levels,
            on_progress=lambda done, total: self.progress.emit(done, total),
        )
        self.finished_prefetch.emit(count)
