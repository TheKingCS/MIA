"""
gui.widgets.waypoint_map_canvas
==================================

A schematic 2D plot of core.waypoint_manager.Waypoint points — built for
modules/maps/module.py, replacing that module's placeholder screen.

**Deliberately not a real map** (no tile data/basemap imagery, no real
map projection): modules/navigation/module.py's own docstring already
scoped "offline maps, trails, elevation" as waiting on real GPS/mapping
hardware/data this dev sandbox doesn't have, same reasoning
docs/ROADMAP.md's v0.16 called its own zero-hardware slice out
explicitly. This widget is the honest zero-hardware slice of "Maps":
a schematic layout of waypoints already entered by hand (same
compass-and-map-user framing core/waypoint_manager.py's own docstring
gives for distance_and_bearing() being useful without GPS hardware at
all) — good for "where is B relative to A," not literal cartography.

project_waypoints() is a free function (not a method) — pure math,
testable without Qt, see tests/test_waypoint_map_canvas.py. It uses a
simple equirectangular-style scaling (longitude -> x, latitude -> y,
flipped since screen y grows downward), fit-to-box with one shared
scale factor (not stretched per-axis) so relative shape isn't
distorted — this does *not* correct for latitude-dependent longitude
compression the way a real map projection would, which would visibly
matter at continental scale but is a fine approximation at the
trip-log scale this widget is for.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

_PADDING = 28.0
_DOT_RADIUS = 6.0
_HIGHLIGHT_DOT_RADIUS = 8.0
_HIT_TEST_RADIUS = 14.0  # generous click target, bigger than the dot itself

_DOT_COLOR = QColor("#4fd1c5")
_FROM_COLOR = QColor("#e0af68")
_TO_COLOR = QColor("#e06666")
_ROUTE_COLOR = QColor("#38d9c9")
_LABEL_COLOR = QColor("#c3ccd9")
_BACKGROUND_COLOR = QColor("#0d1116")
_BORDER_COLOR = QColor("#232b34")


def project_waypoints(
    points: list[tuple[str, float, float]], width: float, height: float, padding: float = _PADDING
) -> dict[str, tuple[float, float]]:
    """
    Projects (waypoint_id, latitude, longitude) points onto a
    width x height canvas. See this module's docstring for why this is
    a schematic layout, not a real map projection.

    Edge cases: no points -> empty dict; a single point (or every point
    sharing the same coordinates) -> centered rather than dividing by a
    zero span.
    """
    if not points:
        return {}

    usable_width = max(width - 2 * padding, 1.0)
    usable_height = max(height - 2 * padding, 1.0)

    if len(points) == 1:
        return {points[0][0]: (width / 2.0, height / 2.0)}

    lats = [p[1] for p in points]
    lons = [p[2] for p in points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    lat_span = max_lat - min_lat
    lon_span = max_lon - min_lon

    if lat_span == 0 and lon_span == 0:
        return {point_id: (width / 2.0, height / 2.0) for point_id, _, _ in points}

    scale_x = usable_width / lon_span if lon_span > 0 else float("inf")
    scale_y = usable_height / lat_span if lat_span > 0 else float("inf")
    scale = min(scale_x, scale_y)

    projected_width = lon_span * scale
    projected_height = lat_span * scale
    offset_x = padding + (usable_width - projected_width) / 2.0
    offset_y = padding + (usable_height - projected_height) / 2.0

    positions = {}
    for point_id, lat, lon in points:
        x = offset_x + (lon - min_lon) * scale
        y = offset_y + (max_lat - lat) * scale  # flip: north is up on screen
        positions[point_id] = (x, y)
    return positions


class WaypointMapCanvas(QWidget):
    """Plots waypoints, an optional Trip route overlay, and up to two
    "from"/"to" highlighted points for distance/bearing lookups."""

    waypoint_clicked = Signal(str)  # emits waypoint_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(280)
        self._points: list[tuple[str, str, float, float]] = []  # (id, name, lat, lon)
        self._route_ids: list[str] = []
        self._from_id: Optional[str] = None
        self._to_id: Optional[str] = None
        self._positions: dict[str, tuple[float, float]] = {}

    def set_waypoints(self, waypoints) -> None:
        self._points = [(w.waypoint_id, w.name, w.latitude, w.longitude) for w in waypoints]
        self._recompute_positions()
        self.update()

    def set_route(self, waypoint_ids: list[str]) -> None:
        self._route_ids = list(waypoint_ids)
        self.update()

    def set_highlighted(self, from_id: Optional[str], to_id: Optional[str]) -> None:
        self._from_id = from_id
        self._to_id = to_id
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._recompute_positions()

    def _recompute_positions(self) -> None:
        triples = [(point_id, lat, lon) for point_id, _, lat, lon in self._points]
        self._positions = project_waypoints(triples, float(self.width()), float(self.height()))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), _BACKGROUND_COLOR)
        painter.setPen(QPen(_BORDER_COLOR, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if not self._points:
            painter.setPen(_LABEL_COLOR)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No waypoints yet.")
            painter.end()
            return

        self._paint_route(painter)
        self._paint_waypoints(painter)
        painter.end()

    def _paint_route(self, painter: QPainter) -> None:
        route_points = [self._positions[wid] for wid in self._route_ids if wid in self._positions]
        if len(route_points) < 2:
            return
        painter.setPen(QPen(_ROUTE_COLOR, 2, Qt.PenStyle.DashLine))
        for start, end in zip(route_points, route_points[1:]):
            painter.drawLine(QPointF(*start), QPointF(*end))

    def _paint_waypoints(self, painter: QPainter) -> None:
        font = QFont(painter.font())
        font.setPointSize(max(font.pointSize() - 1, 7))
        painter.setFont(font)

        if self._from_id is not None and self._to_id is not None:
            from_pos = self._positions.get(self._from_id)
            to_pos = self._positions.get(self._to_id)
            if from_pos is not None and to_pos is not None:
                painter.setPen(QPen(QColor("#e7ecf3"), 2))
                painter.drawLine(QPointF(*from_pos), QPointF(*to_pos))

        for point_id, name, _, _ in self._points:
            pos = self._positions.get(point_id)
            if pos is None:
                continue
            x, y = pos
            if point_id == self._from_id:
                color, radius = _FROM_COLOR, _HIGHLIGHT_DOT_RADIUS
            elif point_id == self._to_id:
                color, radius = _TO_COLOR, _HIGHLIGHT_DOT_RADIUS
            else:
                color, radius = _DOT_COLOR, _DOT_RADIUS

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), radius, radius)

            painter.setPen(_LABEL_COLOR)
            painter.drawText(QPointF(x + radius + 4, y + 4), name)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        click_pos = event.position()
        for point_id, _, _, _ in self._points:
            pos = self._positions.get(point_id)
            if pos is None:
                continue
            dx = click_pos.x() - pos[0]
            dy = click_pos.y() - pos[1]
            if (dx * dx + dy * dy) ** 0.5 <= _HIT_TEST_RADIUS:
                self.waypoint_clicked.emit(point_id)
                return
        super().mousePressEvent(event)
