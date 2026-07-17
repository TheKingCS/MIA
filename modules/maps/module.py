"""
modules.maps.module
=====================

Maps — replaces the placeholder screen with a real, honest
zero-hardware slice: a schematic waypoint plot
(gui/widgets/waypoint_map_canvas.py), click-to-select distance/bearing
lookups between any two waypoints (finally surfacing
core.waypoint_manager.WaypointManager.distance_and_bearing(), which
existed but had no caller anywhere in the app), and an optional Trip
route overlay (Trip.waypoint_ids, the "ordered planned route").

**Deliberately not real cartography** — see
gui/widgets/waypoint_map_canvas.py's docstring for the full reasoning;
same "offline maps, trails, elevation... wait for real GPS/mapping
hardware/data" scope modules/navigation/module.py's own docstring
already drew. Maps is the spatial-visualization companion to
Navigation's waypoint CRUD + Sun/Moon panel, not a duplicate of it —
Maps has no add/edit/delete of its own, it only visualizes whatever
waypoints/trips already exist.

**No live refresh from other modules**: gui/main_window.py caches each
module's get_widget() the first time it's opened (never rebuilds it),
and neither WaypointManager nor TripManager publishes a "changed" event
today — same reasoning several other read-only/aggregate-view modules
in this app just need an explicit "Refresh" button rather than new
event-bus wiring for one screen.

format_distance_bearing_line() is a free function (not a method) —
testable without Qt, see tests/test_maps_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.trip_manager import Trip
from core.waypoint_manager import Waypoint
from gui.widgets.waypoint_map_canvas import WaypointMapCanvas
from modules.module_base import ModuleBase

_NO_ROUTE_LABEL = "No route overlay"


def format_distance_bearing_line(distance_km: float, bearing_degrees: float) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_maps_module.py)."""
    return f"{distance_km:.1f} km  —  bearing {bearing_degrees:03.0f}°"


class MapsModule(ModuleBase):
    module_id = "maps"
    display_name = "Maps"
    description = "A schematic plot of your waypoints — distance/bearing lookups and trip routes."
    icon = "\U0001F5FA"  # world map

    def __init__(self, context) -> None:
        super().__init__(context)
        self._canvas: Optional[WaypointMapCanvas] = None
        self._route_combo: Optional[QComboBox] = None
        self._lookup_label: Optional[QLabel] = None
        self._from_id: Optional[str] = None
        self._to_id: Optional[str] = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        hint = QLabel("Click a waypoint to set the \"from\" point, then click another for \"to\".")
        hint.setObjectName("DashboardSectionBody")
        layout.addWidget(hint)

        self._canvas = WaypointMapCanvas()
        self._canvas.waypoint_clicked.connect(self._on_waypoint_clicked)
        layout.addWidget(self._canvas, stretch=1)

        self._lookup_label = QLabel("")
        self._lookup_label.setObjectName("DashboardSectionBody")
        layout.addWidget(self._lookup_label)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Route overlay:"))
        self._route_combo = QComboBox()
        self._route_combo.currentIndexChanged.connect(self._on_route_selected)
        controls.addWidget(self._route_combo, stretch=1)

        refresh_button = QPushButton("Refresh")
        refresh_button.setToolTip("Reload waypoints/trips (e.g. after adding one in the Navigation module)")
        refresh_button.clicked.connect(self._refresh)
        controls.addWidget(refresh_button)
        layout.addLayout(controls)

        self._refresh()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self._from_id = None
        self._to_id = None
        self._update_lookup_label()

        waypoints: list[Waypoint] = self.context.waypoints.all_waypoints() if self.context.waypoints else []
        self._canvas.set_waypoints(waypoints)
        self._canvas.set_highlighted(None, None)

        trips: list[Trip] = self.context.trips.all_trips() if self.context.trips else []
        self._route_combo.blockSignals(True)
        self._route_combo.clear()
        self._route_combo.addItem(_NO_ROUTE_LABEL, userData=None)
        for trip in trips:
            if len(trip.waypoint_ids) >= 2:
                self._route_combo.addItem(trip.name, userData=trip.trip_id)
        self._route_combo.blockSignals(False)
        self._canvas.set_route([])

    # ------------------------------------------------------------------
    # Distance/bearing lookup
    # ------------------------------------------------------------------

    def _on_waypoint_clicked(self, waypoint_id: str) -> None:
        if waypoint_id == self._from_id:
            self._from_id = None
        elif waypoint_id == self._to_id:
            self._to_id = None
        elif self._from_id is None:
            self._from_id = waypoint_id
        elif self._to_id is None:
            self._to_id = waypoint_id
        else:
            # Both already set — starting a fresh pair is more useful
            # than refusing the click.
            self._from_id = waypoint_id
            self._to_id = None

        self._canvas.set_highlighted(self._from_id, self._to_id)
        self._update_lookup_label()

    def _update_lookup_label(self) -> None:
        if self._from_id is None or self._to_id is None:
            self._lookup_label.setText("Select two waypoints to see the distance and bearing between them.")
            return

        result = self.context.waypoints.distance_and_bearing(self._from_id, self._to_id) if self.context.waypoints else None
        if result is None:
            self._lookup_label.setText("Couldn't compute distance/bearing for that pair.")
            return

        distance_km, bearing_degrees = result
        from_waypoint = self.context.waypoints.get_waypoint(self._from_id)
        to_waypoint = self.context.waypoints.get_waypoint(self._to_id)
        from_name = from_waypoint.name if from_waypoint else "?"
        to_name = to_waypoint.name if to_waypoint else "?"
        self._lookup_label.setText(f"{from_name} → {to_name}:  {format_distance_bearing_line(distance_km, bearing_degrees)}")

    # ------------------------------------------------------------------
    # Route overlay
    # ------------------------------------------------------------------

    def _on_route_selected(self, index: int) -> None:
        trip_id = self._route_combo.itemData(index)
        if trip_id is None or self.context.trips is None:
            self._canvas.set_route([])
            return
        trip = self.context.trips.get_trip(trip_id)
        self._canvas.set_route(trip.waypoint_ids if trip is not None else [])
