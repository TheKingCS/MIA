"""
gui.widgets.tile_map_view
============================

A real pannable/zoomable basemap widget — the actual "offline maps"
imagery, unlike gui/widgets/waypoint_map_canvas.py's schematic
waypoint plot (which deliberately has no basemap imagery at all; see
that module's docstring for why). Renders tiles from
core.map_tile_cache.MapTileCache, fetching whatever's missing for the
current view through core.tile_fetch_worker.TileFetchWorker rather
than blocking the paint/input thread on network I/O.

**No QtWebEngine/Leaflet.js here** — confirmed directly that
`PySide6.QtWebEngineWidgets` fails to import in this dev sandbox
(missing `libnspr4.so`, no sudo to install it, same class of blocked
system dependency as `libportaudio2`/`libpulse` before it) — so this is
a hand-built `QPainter` tile renderer instead, same general technique
as `gui/presence_widget.py`.

Coordinate math (continuous "world pixel" projection, not snapped to
whole tiles — needed for smooth pan/zoom) lives in core.map_tile_math,
pure and unit-tested there; this widget only does Qt painting/input
handling on top of it.

**Must call stop() before this widget is destroyed** — it owns a
`TileFetchWorker` background thread with no Qt-parent-driven cleanup,
same explicit-teardown requirement as
`gui/widgets/avatar_camera_widget.py`'s `QCamera`.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget

from core.map_tile_cache import MapTileCache
from core.map_tile_math import lat_lon_to_world_pixel, world_pixel_to_lat_lon
from core.tile_fetch_worker import TileFetchWorker

_TILE_SIZE = 256
_MIN_ZOOM = 0
_MAX_ZOOM = 15
_BACKGROUND_COLOR = QColor("#0d1116")
_PLACEHOLDER_COLOR = QColor("#161b22")
_GRID_COLOR = QColor("#232b34")
_ATTRIBUTION_COLOR = QColor("#7c8798")

#: source name -> attribution text. OSM's own attribution requirement
#: ("© OpenStreetMap contributors") is different wording from USGS's —
#: shown based on whichever source is actually on screen, not hardcoded.
_ATTRIBUTIONS: dict[str, str] = {
    "usgs_topo": "USGS National Map",
    "osm": "© OpenStreetMap contributors",
}


class TileMapView(QWidget):
    """A real basemap: mouse-drag to pan, scroll wheel to zoom.
    set_source() switches which tile provider is displayed — see
    core.map_tile_cache's own docstring for why there are two
    (USGS for US high-detail, OSM for a worldwide low-zoom overview
    only) and why they're never blended per-tile (each renders its own
    consistent visual style; switching is an explicit user choice, same
    reasoning real map apps offer a basemap-source switcher rather than
    silently mixing providers)."""

    def __init__(
        self, tile_cache: MapTileCache, source: str = "usgs_topo", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(320)
        self.setMouseTracking(True)

        self._tile_cache = tile_cache
        self._source = source
        self._center_lat = 37.0  # roughly the KY/TN border — a reasonable default center
        self._center_lon = -85.5
        self._zoom = 7

        self._pixmap_cache: dict[tuple[str, int, int, int], QPixmap] = {}
        self._drag_last_pos: Optional[QPointF] = None

        self._fetch_worker = TileFetchWorker(tile_cache)
        self._fetch_worker.tile_ready.connect(self._on_tile_ready)
        self._fetch_worker.start()

    def stop(self) -> None:
        self._fetch_worker.tile_ready.disconnect(self._on_tile_ready)
        self._fetch_worker.stop()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_center(self, lat: float, lon: float, zoom: Optional[int] = None) -> None:
        self._center_lat = lat
        self._center_lon = lon
        if zoom is not None:
            self._zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, zoom))
        self.update()

    def set_source(self, source: str) -> None:
        self._source = source
        self.update()

    def source(self) -> str:
        return self._source

    def visible_bounds(self) -> tuple[float, float, float, float]:
        """(min_lat, min_lon, max_lat, max_lon) currently on screen —
        used by the module's "download this view" action."""
        center_x, center_y = lat_lon_to_world_pixel(self._center_lat, self._center_lon, self._zoom, _TILE_SIZE)
        half_width, half_height = self.width() / 2.0, self.height() / 2.0
        north_lat, west_lon = world_pixel_to_lat_lon(center_x - half_width, center_y - half_height, self._zoom, _TILE_SIZE)
        south_lat, east_lon = world_pixel_to_lat_lon(center_x + half_width, center_y + half_height, self._zoom, _TILE_SIZE)
        return south_lat, west_lon, north_lat, east_lon

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), _BACKGROUND_COLOR)

        center_x, center_y = lat_lon_to_world_pixel(self._center_lat, self._center_lon, self._zoom, _TILE_SIZE)
        half_width, half_height = self.width() / 2.0, self.height() / 2.0
        top_left_x, top_left_y = center_x - half_width, center_y - half_height

        first_tile_x = int(top_left_x // _TILE_SIZE) - 1
        first_tile_y = int(top_left_y // _TILE_SIZE) - 1
        last_tile_x = int((top_left_x + self.width()) // _TILE_SIZE) + 1
        last_tile_y = int((top_left_y + self.height()) // _TILE_SIZE) + 1

        n = 2 ** self._zoom
        for tile_x in range(first_tile_x, last_tile_x + 1):
            if tile_x < 0 or tile_x >= n:
                continue
            for tile_y in range(first_tile_y, last_tile_y + 1):
                if tile_y < 0 or tile_y >= n:
                    continue
                screen_x = tile_x * _TILE_SIZE - top_left_x
                screen_y = tile_y * _TILE_SIZE - top_left_y
                self._paint_tile(painter, tile_x, tile_y, screen_x, screen_y)

        painter.setPen(_ATTRIBUTION_COLOR)
        attribution = _ATTRIBUTIONS.get(self._source, self._source)
        painter.drawText(self.rect().adjusted(6, 0, -6, -6), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, attribution)
        painter.end()

    def _paint_tile(self, painter: QPainter, tile_x: int, tile_y: int, screen_x: float, screen_y: float) -> None:
        key = (self._source, self._zoom, tile_x, tile_y)
        pixmap = self._pixmap_cache.get(key)
        if pixmap is None:
            path = self._tile_cache.tile_path(self._source, self._zoom, tile_x, tile_y)
            if path.exists():
                pixmap = QPixmap(str(path))
                self._pixmap_cache[key] = pixmap
            else:
                painter.fillRect(int(screen_x), int(screen_y), _TILE_SIZE, _TILE_SIZE, _PLACEHOLDER_COLOR)
                painter.setPen(QPen(_GRID_COLOR, 1))
                painter.drawRect(int(screen_x), int(screen_y), _TILE_SIZE, _TILE_SIZE)
                self._fetch_worker.request(self._source, self._zoom, tile_x, tile_y)
                return

        painter.drawPixmap(int(screen_x), int(screen_y), pixmap)

    def _on_tile_ready(self, source: str, zoom: int, x: int, y: int, path: str) -> None:
        if source == self._source and zoom == self._zoom:
            self.update()

    # ------------------------------------------------------------------
    # Pan / zoom input
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_last_pos = event.position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_last_pos is None:
            return
        current_pos = event.position()
        delta_x = current_pos.x() - self._drag_last_pos.x()
        delta_y = current_pos.y() - self._drag_last_pos.y()
        self._drag_last_pos = current_pos

        center_x, center_y = lat_lon_to_world_pixel(self._center_lat, self._center_lon, self._zoom, _TILE_SIZE)
        center_x -= delta_x
        center_y -= delta_y
        self._center_lat, self._center_lon = world_pixel_to_lat_lon(center_x, center_y, self._zoom, _TILE_SIZE)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_last_pos = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = 1 if event.angleDelta().y() > 0 else -1
        new_zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, self._zoom + delta))
        if new_zoom != self._zoom:
            self._zoom = new_zoom
            self.update()
