"""
modules.maps.tile_fetch_worker
=================================

Fetches individual missing basemap tiles off the GUI thread for
gui/widgets/tile_map_view.py's live pan/zoom — same "network I/O never
blocks a paint/input handler" reasoning as
modules/field_kit/port_scan_worker.py's PortScanWorker, but shaped as a
long-lived queue-processing thread rather than a one-shot run(), since
tile requests arrive continuously while panning/zooming rather than
from a single button click.

**stop() must be called before this widget/thread is torn down** — a
QThread has no Qt-parent-driven automatic cleanup, same explicit-
teardown requirement gui/widgets/avatar_camera_widget.py's QCamera
already has.
"""

from __future__ import annotations

import queue
import urllib.error

from PySide6.QtCore import QThread, Signal

from core.logger import get_logger
from core.map_tile_cache import MapTileCache

log = get_logger(__name__)


class TileFetchWorker(QThread):
    tile_ready = Signal(str, int, int, int, str)  # source, zoom, x, y, local file path

    def __init__(self, tile_cache: MapTileCache) -> None:
        super().__init__()
        self._tile_cache = tile_cache
        self._queue: "queue.Queue[tuple[str, int, int, int] | None]" = queue.Queue()
        self._pending: set[tuple[str, int, int, int]] = set()
        self._running = True

    def request(self, source: str, zoom: int, x: int, y: int) -> None:
        """Enqueues a tile fetch if it isn't already queued/in-flight —
        called from the GUI thread every time paintEvent() finds a
        missing tile; safe to call repeatedly for the same tile while
        panning without piling up duplicate work."""
        key = (source, zoom, x, y)
        if key in self._pending:
            return
        self._pending.add(key)
        self._queue.put(key)

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)  # wake the blocking get() so run() can exit
        self.wait(2000)

    def run(self) -> None:
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            source, zoom, x, y = item
            try:
                path = self._tile_cache.fetch_tile(source, zoom, x, y)
                self.tile_ready.emit(source, zoom, x, y, str(path))
            except (urllib.error.URLError, OSError):
                log.warning("Failed to fetch map tile source=%s z=%s x=%s y=%s.", source, zoom, x, y, exc_info=True)
            finally:
                self._pending.discard(item)
