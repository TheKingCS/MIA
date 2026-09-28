"""
modules.navigation.module
============================

Navigation — docs/ROADMAP.md milestone 10.2: waypoints (name/lat/lon/
notes CRUD, same shape as Notes/Inventory/Components) plus a Sun/Moon
panel (sunrise/sunset + moon phase for a selected waypoint's
coordinates) via the `astral` package. `core/waypoint_manager.py`'s
`distance_and_bearing()` (haversine formula) is available on the
manager for a future "distance between two waypoints" UI addition;
not surfaced in this first cut to keep the widget simple.

format_waypoint_row()/format_moon_phase_name()/format_sun_moon_summary()
are free functions (not methods) — testable without Qt, see
tests/test_navigation_module.py.

"Offline maps, trails, elevation" from this section's full described
scope wait for real GPS/mapping hardware/data; this milestone is the
slice buildable with zero real hardware right now.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from astral import Observer
from astral import moon as astral_moon
from astral.sun import sun as astral_sun
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.waypoint_manager import Waypoint
from gui.add_edit_waypoint_dialog import AddEditWaypointDialog
from modules.module_base import ModuleBase


def format_waypoint_row(waypoint: Waypoint) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_navigation_module.py)."""
    category = f"[{waypoint.category}] " if waypoint.category else ""
    return f"{category}{waypoint.name}  ({waypoint.latitude:.4f}, {waypoint.longitude:.4f})"


def format_moon_phase_name(phase: float) -> str:
    """
    astral.moon.phase() returns 0-27.99 (days into the ~29.5-day
    synodic month), documented by astral itself as exactly these four
    buckets — matched here as-is rather than inventing a finer 8-phase
    scale the underlying calculation doesn't actually support:
    0-6.99 New moon, 7-13.99 First quarter, 14-20.99 Full moon,
    21-27.99 Last quarter.
    """
    if phase < 7:
        return "New Moon"
    if phase < 14:
        return "First Quarter"
    if phase < 21:
        return "Full Moon"
    return "Last Quarter"


def format_sun_moon_summary(latitude: float, longitude: float, for_date: date) -> str:
    """Pure formatting logic (astral calls only, no Qt) — testable, see tests/test_navigation_module.py."""
    observer = Observer(latitude=latitude, longitude=longitude)
    try:
        sun_times = astral_sun(observer, date=for_date)
    except ValueError as exc:
        # astral raises ValueError for latitudes with no sunrise/sunset
        # on a given date (inside the polar circles) — a real, not
        # hypothetical, edge case for a "survival/field device" tool.
        return f"Sun times unavailable for this location/date: {exc}"

    sunrise_local = sun_times["sunrise"].astimezone()
    sunset_local = sun_times["sunset"].astimezone()
    phase = astral_moon.phase(for_date)

    return "\n".join([
        f"Sunrise: {sunrise_local.strftime('%H:%M')}",
        f"Sunset: {sunset_local.strftime('%H:%M')}",
        f"Moon phase: {format_moon_phase_name(phase)}",
    ])


class NavigationModule(ModuleBase):
    module_id = "navigation"
    display_name = "Navigation"
    description = "Waypoints, distance/bearing, and sun/moon reference."
    icon = "\U0001F9ED"  # compass

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list: Optional[QListWidget] = None
        self._sun_moon_label: Optional[QLabel] = None
        self._waypoint_combo: Optional[QComboBox] = None

    def refresh(self) -> None:
        """Re-read every list (ModuleBase.refresh: records changed elsewhere, e.g. by voice)."""
        self._refresh_list()

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

        sun_moon_title = QLabel("Sun / Moon (selected waypoint, today)")
        sun_moon_title.setObjectName("SubtitleLabel")
        layout.addWidget(sun_moon_title)

        self._waypoint_combo = QComboBox()
        self._waypoint_combo.currentIndexChanged.connect(self._refresh_sun_moon)
        layout.addWidget(self._waypoint_combo)

        self._sun_moon_label = QLabel("")
        self._sun_moon_label.setObjectName("ReadoutLabel")
        layout.addWidget(self._sun_moon_label)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Waypoint")
        add_button.clicked.connect(self._on_add)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        waypoints = self.context.waypoints.all_waypoints()

        self._list.clear()
        for waypoint in waypoints:
            item = QListWidgetItem(format_waypoint_row(waypoint))
            item.setData(Qt.ItemDataRole.UserRole, waypoint.waypoint_id)
            self._list.addItem(item)

        previously_selected = self._waypoint_combo.currentData()
        self._waypoint_combo.blockSignals(True)
        self._waypoint_combo.clear()
        for waypoint in waypoints:
            self._waypoint_combo.addItem(waypoint.name, waypoint.waypoint_id)
        if previously_selected is not None:
            index = self._waypoint_combo.findData(previously_selected)
            if index != -1:
                self._waypoint_combo.setCurrentIndex(index)
        self._waypoint_combo.blockSignals(False)

        self._refresh_sun_moon()

    def _refresh_sun_moon(self) -> None:
        waypoint_id = self._waypoint_combo.currentData()
        waypoint = self.context.waypoints.get_waypoint(waypoint_id) if waypoint_id is not None else None
        if waypoint is None:
            self._sun_moon_label.setText("Add a waypoint to see sun/moon info.")
            return
        self._sun_moon_label.setText(format_sun_moon_summary(waypoint.latitude, waypoint.longitude, date.today()))

    def _selected_waypoint_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        dialog = AddEditWaypointDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.waypoints.add_waypoint(
            name=dialog.entered_name,
            latitude=dialog.entered_latitude,
            longitude=dialog.entered_longitude,
            notes=dialog.entered_notes,
            category=dialog.entered_category,
        )
        self._refresh_list()

    def _on_edit(self) -> None:
        waypoint_id = self._selected_waypoint_id()
        if waypoint_id is None:
            QMessageBox.information(None, "No Waypoint Selected", "Select a waypoint to edit.")
            return

        waypoint = self.context.waypoints.get_waypoint(waypoint_id)
        dialog = AddEditWaypointDialog(waypoint=waypoint)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.waypoints.update_waypoint(
            waypoint_id,
            name=dialog.entered_name,
            latitude=dialog.entered_latitude,
            longitude=dialog.entered_longitude,
            notes=dialog.entered_notes,
            category=dialog.entered_category,
        )
        self._refresh_list()

    def _on_delete(self) -> None:
        waypoint_id = self._selected_waypoint_id()
        if waypoint_id is None:
            QMessageBox.information(None, "No Waypoint Selected", "Select a waypoint to delete.")
            return

        waypoint = self.context.waypoints.get_waypoint(waypoint_id)
        confirm = QMessageBox.question(
            None,
            "Delete Waypoint",
            f"Delete '{waypoint.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.waypoints.delete_waypoint(waypoint_id)
        self._refresh_list()
