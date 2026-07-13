"""
gui.trip_map_view
====================

A schematic (non-tiled) plot of a trip's planned route — docs/ROADMAP.md
milestone 12.6, Expedition Mode. Deliberately not a real basemap: there's no
bundled offline map imagery in this project (same "offline maps, trails"
gap already flagged in modules/navigation/module.py's own docstring), so
waypoints are placed by a plain equirectangular projection (x from
longitude, y from -latitude so north is up) scaled to fit a
QGraphicsView, not against any real terrain/street imagery. This is a
read-only visualization — adding/editing a point still goes through
gui/add_edit_waypoint_dialog.py's coordinate entry; a click on blank
schematic space has no real-world meaning without underlying map imagery
to anchor it.

`project_to_scene_xy()` is a free function (not a method) — testable
without Qt, see tests/test_trip_map_view.py.
"""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QVBoxLayout, QWidget

from core.app_context import AppContext
from core.waypoint_manager import Waypoint

_SCENE_SIZE = 400.0
_SCENE_MARGIN = 40.0
_MARKER_RADIUS = 6.0

#: Marker color per Waypoint.category (docs/ROADMAP.md milestone 12.2) —
#: an unrecognized/blank category falls back to _DEFAULT_MARKER_COLOR.
_CATEGORY_COLORS = {
    "Campsite": "#4CAF50",
    "Trailhead": "#2196F3",
    "Water Source": "#00BCD4",
    "Viewpoint": "#FF9800",
    "Other": "#9C27B0",
}
_DEFAULT_MARKER_COLOR = "#CCCCCC"
_LINE_COLOR = "#888888"
_LABEL_COLOR = "#EEEEEE"


def compute_bounds(waypoints: list[Waypoint]) -> tuple[float, float, float, float]:
    """(min_lat, max_lat, min_lon, max_lon) over a list of waypoints."""
    lats = [w.latitude for w in waypoints]
    lons = [w.longitude for w in waypoints]
    return (min(lats), max(lats), min(lons), max(lons))


def project_to_scene_xy(
    latitude: float,
    longitude: float,
    bounds: tuple[float, float, float, float],
    scale: float = _SCENE_SIZE,
) -> tuple[float, float]:
    """
    Plain equirectangular scaling into a `scale`x`scale` square, not a
    real map projection — adequate for the small local extents a single
    hike covers. `bounds` = (min_lat, max_lat, min_lon, max_lon). If every
    point shares the same latitude and/or longitude (bounds has zero
    height/width), that axis maps to the center of the square instead of
    dividing by zero.
    """
    min_lat, max_lat, min_lon, max_lon = bounds
    lon_span = max_lon - min_lon
    lat_span = max_lat - min_lat

    x = (scale / 2) if lon_span == 0 else (longitude - min_lon) / lon_span * scale
    # y is inverted (max_lat at the top) so north is up on screen.
    y = (scale / 2) if lat_span == 0 else (max_lat - latitude) / lat_span * scale
    return x, y


class _ZoomableGraphicsView(QGraphicsView):
    """Wheel-to-zoom on top of QGraphicsView's built-in ScrollHandDrag panning."""

    _ZOOM_FACTOR = 1.15

    def wheelEvent(self, event) -> None:
        factor = self._ZOOM_FACTOR if event.angleDelta().y() > 0 else 1 / self._ZOOM_FACTOR
        self.scale(factor, factor)


class TripMapView(QWidget):
    def __init__(self, context: AppContext, trip_id: str, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.trip_id = trip_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scene = QGraphicsScene()
        self._view = _ZoomableGraphicsView(self._scene)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setFixedHeight(260)
        layout.addWidget(self._view)

        self.refresh()

    def refresh(self) -> None:
        self._scene.clear()

        trip = self.context.trips.get_trip(self.trip_id)
        if trip is None:
            return

        waypoints = [self.context.waypoints.get_waypoint(wid) for wid in trip.waypoint_ids]
        waypoints = [w for w in waypoints if w is not None]
        if not waypoints:
            self._scene.addText("Add waypoints to the route to see them here.")
            return

        bounds = compute_bounds(waypoints)
        points: list[tuple[float, float, Waypoint]] = []
        for waypoint in waypoints:
            x, y = project_to_scene_xy(waypoint.latitude, waypoint.longitude, bounds)
            points.append((x + _SCENE_MARGIN, y + _SCENE_MARGIN, waypoint))

        line_pen = QPen(QColor(_LINE_COLOR))
        for (x1, y1, _), (x2, y2, _) in zip(points, points[1:]):
            self._scene.addLine(x1, y1, x2, y2, line_pen)

        for x, y, waypoint in points:
            color = QColor(_CATEGORY_COLORS.get(waypoint.category, _DEFAULT_MARKER_COLOR))
            self._scene.addEllipse(
                x - _MARKER_RADIUS,
                y - _MARKER_RADIUS,
                _MARKER_RADIUS * 2,
                _MARKER_RADIUS * 2,
                QPen(color),
                QBrush(color),
            )
            label = self._scene.addText(waypoint.name)
            label.setDefaultTextColor(QColor(_LABEL_COLOR))
            label.setPos(x + _MARKER_RADIUS + 2, y - _MARKER_RADIUS - 2)

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-20, -20, 20, 20))
