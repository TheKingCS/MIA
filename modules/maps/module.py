"""
modules.maps.module
=====================

Maps — a schematic waypoint plot (the original zero-hardware slice),
plus two real additions the user explicitly asked for next: a real
pannable/zoomable basemap ("offline maps") and a catalog of official
state park / trail map PDFs ("state park maps and trail maps").
Three tabs:

- **Waypoints** — the original schematic plot
  (gui/widgets/waypoint_map_canvas.py): click-to-select distance/
  bearing lookups between any two waypoints (finally surfacing
  core.waypoint_manager.WaypointManager.distance_and_bearing(), which
  existed but had no caller anywhere in the app) and an optional Trip
  route overlay (Trip.waypoint_ids). Deliberately not real cartography
  — see that widget's own docstring for the full reasoning.
- **Basemap** — a real tile-based map (gui/widgets/tile_map_view.py)
  with a source switcher between two providers, each scoped to a
  specific job (see core.map_tile_cache's own docstring for the full
  reasoning): **USGS National Map** topo tiles (US only, shows real
  trails) for high-detail region caching, and **OpenStreetMap** for a
  small worldwide low-zoom overview only (~5MB for the whole planet —
  OSM's tile usage policy prohibits the kind of bulk/deep caching USGS
  is fine with, so OSM is never used for that). One-click "Download
  Kentucky"/"Download Tennessee" buttons (the user's original starting
  scope) plus "Download Current View" (pan/zoom anywhere, then cache
  that exact area — not limited to the two preset states) and
  "Download Worldwide Overview" all bulk-prefetch via a background
  worker so the area works fully offline afterward; live panning/
  zooming fetches individual tiles beyond whatever's cached on demand.
- **Trail Maps** — a catalog of official per-park trail map PDFs
  (core.trail_map_library.TrailMapLibrary). Deliberately not
  pre-seeded with scraped URLs — see that module's own docstring for
  why (state park sites block automated scraping) — the user adds each
  one by URL or local file; the PDF opens embedded in-app via QtPdf
  (confirmed importable, unlike QtWebEngineWidgets).

format_distance_bearing_line() and format_tile_count_estimate() are
free functions (not methods) — testable without Qt, see
tests/test_maps_module.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.map_tile_cache import (
    DEFAULT_PREFETCH_SOURCE,
    DEFAULT_PREFETCH_ZOOM_LEVELS,
    WORLDWIDE_BOUNDS,
    WORLDWIDE_OVERVIEW_SOURCE,
    WORLDWIDE_OVERVIEW_ZOOM_LEVELS,
)
from core.map_tile_math import tiles_covering_bbox
from core.trail_map_library import NotAPdfError, TrailMap
from core.trip_manager import Trip
from core.waypoint_manager import Waypoint
from gui.add_trail_map_dialog import AddTrailMapDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from gui.trail_map_viewer_dialog import TrailMapViewerDialog
from gui.widgets.tile_map_view import TileMapView
from gui.widgets.waypoint_map_canvas import WaypointMapCanvas
from modules.maps.tile_prefetch_worker import TilePrefetchWorker
from modules.maps.trail_map_fetch_worker import TrailMapFetchWorker
from modules.module_base import ModuleBase

_NO_ROUTE_LABEL = "No route overlay"

#: Rough rectangular bounding boxes (public geographic fact, not
#: scraped/guessed) — used only to bulk-prefetch state-scale tile
#: coverage, so a little over-fetch past the exact state border is
#: harmless (nearby tiles are useful context anyway).
_STATE_BOUNDING_BOXES: dict[str, tuple[float, float, float, float]] = {
    "Kentucky": (36.497, -89.571, 39.147, -81.965),
    "Tennessee": (34.983, -90.310, 36.678, -81.647),
}

#: Deeper than DEFAULT_PREFETCH_ZOOM_LEVELS — "download the current
#: view" targets a much smaller area than a whole state (the visible
#: viewport), so it can afford more detail per tile-count budget.
_CURRENT_VIEW_PREFETCH_ZOOM_LEVELS: tuple[int, ...] = (8, 9, 10, 11, 12)

#: Dropdown label -> internal core.map_tile_cache.TILE_SOURCES key.
_SOURCE_DISPLAY_NAMES: dict[str, str] = {
    "USGS Topo (US detail, real trails)": "usgs_topo",
    "OpenStreetMap (worldwide, low-zoom overview only)": "osm",
}


def format_trail_map_row(park_name: str, state: str, notes: str) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_maps_module.py). Includes `notes` when present so
    multiple catalog entries for the same park (e.g. several distinct
    trail maps for one large recreation area) read as distinguishable
    list rows, not identical-looking duplicates."""
    suffix = f"  —  {notes}" if notes else ""
    return f"{park_name}  ({state}){suffix}"


def format_distance_bearing_line(distance_km: float, bearing_degrees: float) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_maps_module.py)."""
    return f"{distance_km:.1f} km  —  bearing {bearing_degrees:03.0f}°"


def format_tile_count_estimate(min_lat: float, min_lon: float, max_lat: float, max_lon: float, zoom_levels) -> str:
    """Pure formatting logic — the confirmation prompt before a bulk
    prefetch, so the user knows roughly what they're about to download
    before committing to it."""
    total_tiles = sum(len(tiles_covering_bbox(min_lat, min_lon, max_lat, max_lon, zoom)) for zoom in zoom_levels)
    estimated_mb = total_tiles * 35 / 1024  # ~35KB/tile, measured directly against the real USGS service
    return f"~{total_tiles} tiles (~{estimated_mb:.0f} MB)"


class MapsModule(ModuleBase):
    module_id = "maps"
    display_name = "Maps"
    description = "Waypoints, a real offline basemap, and official trail maps."
    icon = "\U0001F5FA"  # world map

    def __init__(self, context) -> None:
        super().__init__(context)
        self._canvas: Optional[WaypointMapCanvas] = None
        self._route_combo: Optional[QComboBox] = None
        self._lookup_label: Optional[QLabel] = None
        self._from_id: Optional[str] = None
        self._to_id: Optional[str] = None

        self._tile_view: Optional[TileMapView] = None
        self._source_combo: Optional[QComboBox] = None
        self._prefetch_status_label: Optional[QLabel] = None
        self._prefetch_buttons: list[QPushButton] = []
        self._prefetch_worker: Optional[TilePrefetchWorker] = None

        self._trail_map_list: Optional[QListWidget] = None
        self._trail_map_status_label: Optional[QLabel] = None
        self._trail_map_fetch_worker: Optional[TrailMapFetchWorker] = None

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

        tabs = QTabWidget()
        tabs.addTab(self._build_waypoints_tab(), "Waypoints")
        tabs.addTab(self._build_basemap_tab(), "Basemap")
        tabs.addTab(self._build_trail_maps_tab(), "Trail Maps")
        layout.addWidget(tabs, stretch=1)

        self._refresh_waypoints_tab()
        self._refresh_trail_maps_tab()
        return widget

    def on_unload(self) -> None:
        super().on_unload()
        if self._tile_view is not None:
            self._tile_view.stop()

    # ------------------------------------------------------------------
    # Waypoints tab (the original schematic plot)
    # ------------------------------------------------------------------

    def _build_waypoints_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

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
        refresh_button.clicked.connect(self._refresh_waypoints_tab)
        controls.addWidget(refresh_button)
        layout.addLayout(controls)

        return tab

    def _refresh_waypoints_tab(self) -> None:
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

    def _on_route_selected(self, index: int) -> None:
        trip_id = self._route_combo.itemData(index)
        if trip_id is None or self.context.trips is None:
            self._canvas.set_route([])
            return
        trip = self.context.trips.get_trip(trip_id)
        self._canvas.set_route(trip.waypoint_ids if trip is not None else [])

    # ------------------------------------------------------------------
    # Basemap tab (real USGS topo tiles)
    # ------------------------------------------------------------------

    def _build_basemap_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        hint = QLabel("Drag to pan, scroll to zoom. Download a region below to make it fully available offline.")
        hint.setObjectName("DashboardSectionBody")
        layout.addWidget(hint)

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Basemap source:"))
        self._source_combo = QComboBox()
        for label, source_key in _SOURCE_DISPLAY_NAMES.items():
            self._source_combo.addItem(label, source_key)
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_row.addWidget(self._source_combo, stretch=1)
        layout.addLayout(source_row)

        self._tile_view = TileMapView(self.context.map_tiles, source=DEFAULT_PREFETCH_SOURCE)
        layout.addWidget(self._tile_view, stretch=1)

        self._prefetch_status_label = QLabel("")
        self._prefetch_status_label.setObjectName("DashboardSectionBody")
        layout.addWidget(self._prefetch_status_label)

        controls = QHBoxLayout()
        for state_name in _STATE_BOUNDING_BOXES:
            button = QPushButton(f"Download {state_name}")
            button.clicked.connect(lambda _checked=False, s=state_name: self._on_download_state_clicked(s))
            controls.addWidget(button)
            self._prefetch_buttons.append(button)
        layout.addLayout(controls)

        more_controls = QHBoxLayout()
        current_view_button = QPushButton("Download Current View")
        current_view_button.setToolTip("Pan/zoom to any area, then cache it here for offline use")
        current_view_button.clicked.connect(self._on_download_current_view_clicked)
        more_controls.addWidget(current_view_button)
        self._prefetch_buttons.append(current_view_button)

        worldwide_button = QPushButton("Download Worldwide Overview")
        worldwide_button.setToolTip("A small (~5MB) low-zoom overview of the entire planet")
        worldwide_button.clicked.connect(self._on_download_worldwide_clicked)
        more_controls.addWidget(worldwide_button)
        self._prefetch_buttons.append(worldwide_button)
        layout.addLayout(more_controls)

        return tab

    def _on_source_changed(self, index: int) -> None:
        source_key = self._source_combo.itemData(index)
        if source_key is not None:
            self._tile_view.set_source(source_key)

    def _run_prefetch(
        self,
        label: str,
        source: str,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        zoom_levels: tuple[int, ...],
    ) -> None:
        if self._prefetch_worker is not None:
            return  # a prefetch is already running

        estimate = format_tile_count_estimate(min_lat, min_lon, max_lat, max_lon, zoom_levels)
        confirm = QMessageBox.question(
            None,
            f"Download {label}?",
            f"This will download {estimate} of map tiles for offline use. Continue?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        for button in self._prefetch_buttons:
            button.setEnabled(False)
        self._prefetch_status_label.setText(f"Downloading {label}... 0/0")

        self._prefetch_worker = TilePrefetchWorker(
            self.context.map_tiles, min_lat, min_lon, max_lat, max_lon, zoom_levels, source=source
        )
        self._prefetch_worker.progress.connect(
            lambda done, total, s=label: self._prefetch_status_label.setText(f"Downloading {s}... {done}/{total}")
        )
        self._prefetch_worker.finished_prefetch.connect(lambda count, s=label: self._on_prefetch_finished(s, count))
        self._prefetch_worker.start()

    def _on_download_state_clicked(self, state_name: str) -> None:
        min_lat, min_lon, max_lat, max_lon = _STATE_BOUNDING_BOXES[state_name]
        self._tile_view.set_center((min_lat + max_lat) / 2, (min_lon + max_lon) / 2, zoom=7)
        self._run_prefetch(state_name, DEFAULT_PREFETCH_SOURCE, min_lat, min_lon, max_lat, max_lon, DEFAULT_PREFETCH_ZOOM_LEVELS)

    def _on_download_current_view_clicked(self) -> None:
        min_lat, min_lon, max_lat, max_lon = self._tile_view.visible_bounds()
        self._run_prefetch(
            "current view", DEFAULT_PREFETCH_SOURCE, min_lat, min_lon, max_lat, max_lon, _CURRENT_VIEW_PREFETCH_ZOOM_LEVELS
        )

    def _on_download_worldwide_clicked(self) -> None:
        min_lat, min_lon, max_lat, max_lon = WORLDWIDE_BOUNDS
        self._run_prefetch(
            "worldwide overview", WORLDWIDE_OVERVIEW_SOURCE, min_lat, min_lon, max_lat, max_lon, WORLDWIDE_OVERVIEW_ZOOM_LEVELS
        )

    def _on_prefetch_finished(self, label: str, count: int) -> None:
        self._prefetch_status_label.setText(f"{label}: {count} new tiles cached for offline use.")
        for button in self._prefetch_buttons:
            button.setEnabled(True)
        self._prefetch_worker = None

    # ------------------------------------------------------------------
    # Trail Maps tab (official PDF catalog)
    # ------------------------------------------------------------------

    def _build_trail_maps_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._trail_map_list = QListWidget()
        self._trail_map_list.itemDoubleClicked.connect(self._on_view_trail_map)
        layout.addWidget(self._trail_map_list, stretch=1)

        self._trail_map_status_label = QLabel("")
        self._trail_map_status_label.setObjectName("DashboardSectionBody")
        layout.addWidget(self._trail_map_status_label)

        controls = QHBoxLayout()
        add_button = QPushButton("Add Trail Map")
        add_button.clicked.connect(self._on_add_trail_map)
        controls.addWidget(add_button)

        view_button = QPushButton("View")
        view_button.clicked.connect(lambda: self._on_view_trail_map(self._trail_map_list.currentItem()))
        controls.addWidget(view_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._on_delete_trail_map)
        controls.addWidget(delete_button)
        layout.addLayout(controls)

        return tab

    def _refresh_trail_maps_tab(self) -> None:
        self._trail_map_list.clear()
        for trail_map in self.context.trail_maps.all_trail_maps():
            item = QListWidgetItem(format_trail_map_row(trail_map.park_name, trail_map.state, trail_map.notes))
            item.setData(1, trail_map.trail_map_id)
            self._trail_map_list.addItem(item)

    def _on_add_trail_map(self) -> None:
        dialog = AddTrailMapDialog()
        if dialog.exec() != AddTrailMapDialog.DialogCode.Accepted:
            return

        if dialog.entered_local_file_path:
            try:
                self.context.trail_maps.add_from_local_file(
                    dialog.entered_park_name, dialog.entered_state, Path(dialog.entered_local_file_path)
                )
            except NotAPdfError as exc:
                QMessageBox.warning(None, "Not a valid PDF", str(exc))
                return
            self._refresh_trail_maps_tab()
            return

        # A URL download is real network I/O — runs off the GUI thread.
        self._trail_map_status_label.setText(f"Downloading trail map for {dialog.entered_park_name}...")
        self._trail_map_fetch_worker = TrailMapFetchWorker(
            self.context.trail_maps, dialog.entered_park_name, dialog.entered_state, dialog.entered_url
        )
        self._trail_map_fetch_worker.finished_fetch.connect(self._on_trail_map_fetch_finished)
        self._trail_map_fetch_worker.start()

    def _on_trail_map_fetch_finished(self, trail_map: Optional[TrailMap], error_message: str) -> None:
        self._trail_map_fetch_worker = None
        if trail_map is None:
            self._trail_map_status_label.setText("")
            QMessageBox.warning(None, "Couldn't add trail map", error_message)
            return
        self._trail_map_status_label.setText(f"Added: {trail_map.park_name}")
        self._refresh_trail_maps_tab()

    def _on_view_trail_map(self, item: Optional[QListWidgetItem]) -> None:
        if item is None:
            return
        trail_map_id = item.data(1)
        trail_map = self.context.trail_maps.get_trail_map(trail_map_id)
        file_path = self.context.trail_maps.file_path(trail_map_id)
        if trail_map is None or file_path is None:
            QMessageBox.warning(None, "File missing", "That trail map's PDF file couldn't be found on disk.")
            return
        dialog = TrailMapViewerDialog(trail_map, file_path)
        dialog.exec()

    def _on_delete_trail_map(self) -> None:
        item = self._trail_map_list.currentItem()
        if item is None:
            return
        trail_map_id = item.data(1)
        trail_map = self.context.trail_maps.get_trail_map(trail_map_id)
        if trail_map is None:
            return

        dialog = DeleteConfirmDialog(trail_map.park_name, is_directory=False)
        if dialog.exec() != DeleteConfirmDialog.DialogCode.Accepted:
            return

        self.context.trail_maps.delete_trail_map(trail_map_id)
        self._refresh_trail_maps_tab()
