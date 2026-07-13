"""
gui.trip_detail_dialog
=========================

The Trip detail screen for modules/expeditions/module.py —
docs/ROADMAP.md Expedition Mode milestones. Milestone 12.1 gives it
just the Route section
(pick an existing Waypoint, add it to the trip's ordered planned route,
remove one, see the planned-route distance). Milestone 12.3 adds the
Gear Checklist section (add from Inventory or as a freeform custom
item, checkbox toggles packed/unpacked). Milestone 12.4 adds the
Journal / Weather Log section (entries linked to this trip via
`JournalEntry.trip_id`, each with its own `conditions` field). Logged
speed/distance (12.5), the schematic map (12.6), and photos (12.7) each
add their own section to this same dialog in later milestones rather
than spawning separate screens — a Trip's full detail belongs in one
place. Milestone 12.5 adds the Speed & Distance section: "Log Arrival
Now" records a Split (TripManager.record_split()) against the currently
selected waypoint, and the summary readout is derived from
leg_summaries()/total_distance_km()/average_speed_kmh() — actual,
as-logged distance/speed, distinct from the Route section's upfront
planned-distance estimate. Milestone 12.6 embeds gui/trip_map_view.py's
schematic route plot right under the Route section. Milestone 12.7 adds
the Photos section — import-only (QFileDialog.getOpenFileNames over
existing image files), no camera capture (real Pi hardware, out of
scope here). The whole dialog scrolls internally (QScrollArea) now that
it has this many sections — the dialog's own window stays a fixed,
reasonable size.

`format_journal_entry_row()` is a free function (not a method) —
testable without Qt, see tests/test_trip_detail_dialog.py. It's defined
here rather than in modules/expeditions/module.py because gui/ isn't
allowed to import modules/ directly (CLAUDE.md's one-directional
layering: gui/ talks to modules/ only through ModuleBase.get_widget()).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.journal_manager import JournalEntry
from gui.trip_map_view import TripMapView

_PHOTO_THUMBNAIL_SIZE = QSize(96, 96)
_PHOTO_PREVIEW_MAX_SIZE = 480


def format_journal_entry_row(entry: JournalEntry) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_trip_detail_dialog.py)."""
    conditions = f"  [{entry.conditions}]" if entry.conditions else ""
    return f"{entry.title}{conditions}  ({entry.updated_at})"


class TripDetailDialog(QDialog):
    def __init__(self, context: AppContext, trip_id: str, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.trip_id = trip_id
        trip = self.context.trips.get_trip(trip_id)

        self.setWindowTitle(f"Trip: {trip.name}" if trip is not None else "Trip")
        self.setFixedSize(560, 640)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

        if trip is not None and trip.activity_type:
            header_text = f"{trip.name}  [{trip.activity_type}]"
        elif trip is not None:
            header_text = trip.name
        else:
            header_text = "(missing trip)"
        header = QLabel(header_text)
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        route_title = QLabel("Planned Route")
        route_title.setObjectName("SubtitleLabel")
        layout.addWidget(route_title)

        self._waypoint_combo = QComboBox()
        layout.addWidget(self._waypoint_combo)

        add_to_route_button = QPushButton("Add to Route")
        add_to_route_button.clicked.connect(self._on_add_to_route)
        layout.addWidget(add_to_route_button)

        self._route_list = QListWidget()
        layout.addWidget(self._route_list, stretch=1)

        remove_from_route_button = QPushButton("Remove Selected From Route")
        remove_from_route_button.clicked.connect(self._on_remove_from_route)
        layout.addWidget(remove_from_route_button)

        self._distance_label = QLabel("")
        self._distance_label.setObjectName("ReadoutLabel")
        layout.addWidget(self._distance_label)

        map_title = QLabel("Route Map (schematic — not a real basemap)")
        map_title.setObjectName("SubtitleLabel")
        layout.addWidget(map_title)

        self._map_view = TripMapView(self.context, self.trip_id)
        layout.addWidget(self._map_view)

        speed_title = QLabel("Speed & Distance (Logged Checkpoints)")
        speed_title.setObjectName("SubtitleLabel")
        layout.addWidget(speed_title)

        self._split_waypoint_combo = QComboBox()
        layout.addWidget(self._split_waypoint_combo)

        log_arrival_button = QPushButton("Log Arrival Now")
        log_arrival_button.clicked.connect(self._on_log_arrival)
        layout.addWidget(log_arrival_button)

        self._splits_summary_label = QLabel("")
        self._splits_summary_label.setObjectName("ReadoutLabel")
        self._splits_summary_label.setWordWrap(True)
        layout.addWidget(self._splits_summary_label)

        gear_title = QLabel("Gear Checklist")
        gear_title.setObjectName("SubtitleLabel")
        layout.addWidget(gear_title)

        self._gear_list = QListWidget()
        self._gear_list.itemChanged.connect(self._on_gear_item_changed)
        layout.addWidget(self._gear_list, stretch=1)

        inventory_row = QHBoxLayout()
        self._inventory_combo = QComboBox()
        inventory_row.addWidget(self._inventory_combo, stretch=1)
        add_from_inventory_button = QPushButton("Add From Inventory")
        add_from_inventory_button.clicked.connect(self._on_add_gear_from_inventory)
        inventory_row.addWidget(add_from_inventory_button)
        layout.addLayout(inventory_row)

        custom_gear_row = QHBoxLayout()
        self._custom_gear_edit = QLineEdit()
        self._custom_gear_edit.setPlaceholderText("Custom gear item (not in Inventory)")
        custom_gear_row.addWidget(self._custom_gear_edit, stretch=1)
        add_custom_button = QPushButton("Add Custom")
        add_custom_button.clicked.connect(self._on_add_custom_gear)
        custom_gear_row.addWidget(add_custom_button)
        layout.addLayout(custom_gear_row)

        remove_gear_button = QPushButton("Remove Selected Gear Item")
        remove_gear_button.clicked.connect(self._on_remove_gear_item)
        layout.addWidget(remove_gear_button)

        journal_title = QLabel("Journal / Weather Log")
        journal_title.setObjectName("SubtitleLabel")
        layout.addWidget(journal_title)

        self._journal_list = QListWidget()
        layout.addWidget(self._journal_list, stretch=1)

        self._log_title_edit = QLineEdit()
        self._log_title_edit.setPlaceholderText("Log entry title")
        layout.addWidget(self._log_title_edit)

        self._log_body_edit = QTextEdit()
        self._log_body_edit.setPlaceholderText("What happened...")
        self._log_body_edit.setFixedHeight(70)
        layout.addWidget(self._log_body_edit)

        self._log_conditions_edit = QLineEdit()
        self._log_conditions_edit.setPlaceholderText("Conditions/Weather (e.g. Clear, ~15C, light wind)")
        layout.addWidget(self._log_conditions_edit)

        add_log_button = QPushButton("Add Log Entry")
        add_log_button.clicked.connect(self._on_add_log_entry)
        layout.addWidget(add_log_button)

        photos_title = QLabel("Photos")
        photos_title.setObjectName("SubtitleLabel")
        layout.addWidget(photos_title)

        self._photo_list = QListWidget()
        self._photo_list.setViewMode(QListWidget.ViewMode.IconMode)
        self._photo_list.setIconSize(_PHOTO_THUMBNAIL_SIZE)
        self._photo_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._photo_list.itemDoubleClicked.connect(self._on_preview_photo)
        layout.addWidget(self._photo_list, stretch=1)

        photo_buttons = QHBoxLayout()
        add_photo_button = QPushButton("Add Photo(s)")
        add_photo_button.clicked.connect(self._on_add_photos)
        photo_buttons.addWidget(add_photo_button)

        remove_photo_button = QPushButton("Remove Selected Photo")
        remove_photo_button.clicked.connect(self._on_remove_photo)
        photo_buttons.addWidget(remove_photo_button)
        layout.addLayout(photo_buttons)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        close_button.clicked.connect(self.accept)
        outer_layout.addWidget(buttons)

        self._refresh()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self._refresh_waypoint_combo()
        self._refresh_route_list()
        self._refresh_distance_label()
        self._refresh_split_waypoint_combo()
        self._refresh_splits_summary()
        self._refresh_inventory_combo()
        self._refresh_gear_list()
        self._refresh_journal_list()
        self._refresh_photo_list()

    def _refresh_waypoint_combo(self) -> None:
        self._waypoint_combo.clear()
        for waypoint in self.context.waypoints.all_waypoints():
            self._waypoint_combo.addItem(waypoint.name, waypoint.waypoint_id)

    def _refresh_route_list(self) -> None:
        self._route_list.clear()
        trip = self.context.trips.get_trip(self.trip_id)
        if trip is None:
            return
        for waypoint_id in trip.waypoint_ids:
            waypoint = self.context.waypoints.get_waypoint(waypoint_id)
            label = waypoint.name if waypoint is not None else f"(missing waypoint {waypoint_id})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, waypoint_id)
            self._route_list.addItem(item)

    def _refresh_distance_label(self) -> None:
        distance = self.context.trips.planned_route_distance_km(self.trip_id)
        if distance is None:
            self._distance_label.setText("Planned distance: add at least 2 waypoints to the route.")
        else:
            self._distance_label.setText(f"Planned distance: {distance:.2f} km")

    def _refresh_split_waypoint_combo(self) -> None:
        self._split_waypoint_combo.clear()
        for waypoint in self.context.waypoints.all_waypoints():
            self._split_waypoint_combo.addItem(waypoint.name, waypoint.waypoint_id)

    def _refresh_splits_summary(self) -> None:
        trip = self.context.trips.get_trip(self.trip_id)
        if trip is None or not trip.splits:
            self._splits_summary_label.setText("No checkpoints logged yet.")
            return

        lines = [f"Checkpoints logged: {len(trip.splits)}"]
        total_distance = self.context.trips.total_distance_km(self.trip_id)
        average_speed = self.context.trips.average_speed_kmh(self.trip_id)
        if total_distance is not None:
            lines.append(f"Total logged distance: {total_distance:.2f} km")
        if average_speed is not None:
            lines.append(f"Average speed: {average_speed:.2f} km/h")

        for leg in self.context.trips.leg_summaries(self.trip_id):
            from_waypoint = self.context.waypoints.get_waypoint(leg.from_waypoint_id)
            to_waypoint = self.context.waypoints.get_waypoint(leg.to_waypoint_id)
            from_name = from_waypoint.name if from_waypoint is not None else "?"
            to_name = to_waypoint.name if to_waypoint is not None else "?"
            speed_text = f"{leg.speed_kmh:.2f} km/h" if leg.speed_kmh is not None else "n/a"
            lines.append(f"{from_name} -> {to_name}: {leg.distance_km:.2f} km, {speed_text}")

        self._splits_summary_label.setText("\n".join(lines))

    def _refresh_inventory_combo(self) -> None:
        self._inventory_combo.clear()
        for item in self.context.inventory.all_items():
            self._inventory_combo.addItem(item.name, item.item_id)

    def _refresh_gear_list(self) -> None:
        trip = self.context.trips.get_trip(self.trip_id)
        if trip is None:
            return
        # Block signals while repopulating — setCheckState() below would
        # otherwise fire itemChanged and toggle_gear_packed() on every
        # refresh, not just on a real user click.
        self._gear_list.blockSignals(True)
        self._gear_list.clear()
        for gear_item in trip.gear:
            item = QListWidgetItem(gear_item.label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if gear_item.packed else Qt.CheckState.Unchecked)
            self._gear_list.addItem(item)
        self._gear_list.blockSignals(False)

    def _refresh_journal_list(self) -> None:
        self._journal_list.clear()
        for entry in self.context.journal.entries_for_trip(self.trip_id):
            self._journal_list.addItem(format_journal_entry_row(entry))

    def _refresh_photo_list(self) -> None:
        self._photo_list.clear()
        trip = self.context.trips.get_trip(self.trip_id)
        if trip is None:
            return
        for filename in trip.photo_filenames:
            path = self.context.trips.photo_path(self.trip_id, filename)
            icon = QIcon(str(path)) if path.exists() else QIcon()
            item = QListWidgetItem(icon, filename)
            item.setData(Qt.ItemDataRole.UserRole, filename)
            self._photo_list.addItem(item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add_to_route(self) -> None:
        waypoint_id = self._waypoint_combo.currentData()
        if waypoint_id is None:
            return
        self.context.trips.add_waypoint_to_route(self.trip_id, waypoint_id)
        self._refresh_route_list()
        self._refresh_distance_label()
        self._map_view.refresh()

    def _on_remove_from_route(self) -> None:
        item = self._route_list.currentItem()
        if item is None:
            return
        waypoint_id = item.data(Qt.ItemDataRole.UserRole)
        self.context.trips.remove_waypoint_from_route(self.trip_id, waypoint_id)
        self._refresh_route_list()
        self._refresh_distance_label()
        self._map_view.refresh()

    def _on_log_arrival(self) -> None:
        waypoint_id = self._split_waypoint_combo.currentData()
        if waypoint_id is None:
            return
        self.context.trips.record_split(self.trip_id, waypoint_id)
        self._refresh_splits_summary()

    def _on_add_gear_from_inventory(self) -> None:
        item_id = self._inventory_combo.currentData()
        if item_id is None:
            return
        inventory_item = self.context.inventory.get_item(item_id)
        if inventory_item is None:
            return
        self.context.trips.add_gear_item(self.trip_id, label=inventory_item.name, item_id=item_id)
        self._refresh_gear_list()

    def _on_add_custom_gear(self) -> None:
        label = self._custom_gear_edit.text().strip()
        if not label:
            return
        self.context.trips.add_gear_item(self.trip_id, label=label)
        self._custom_gear_edit.clear()
        self._refresh_gear_list()

    def _on_gear_item_changed(self, item: QListWidgetItem) -> None:
        index = self._gear_list.row(item)
        self.context.trips.toggle_gear_packed(self.trip_id, index)

    def _on_remove_gear_item(self) -> None:
        row = self._gear_list.currentRow()
        if row < 0:
            return
        self.context.trips.remove_gear_item(self.trip_id, row)
        self._refresh_gear_list()

    def _on_add_log_entry(self) -> None:
        title = self._log_title_edit.text().strip()
        if not title:
            return
        self.context.journal.add_entry(
            title=title,
            body=self._log_body_edit.toPlainText(),
            trip_id=self.trip_id,
            conditions=self._log_conditions_edit.text().strip(),
        )
        self._log_title_edit.clear()
        self._log_body_edit.clear()
        self._log_conditions_edit.clear()
        self._refresh_journal_list()

    def _on_add_photos(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Photo(s)", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        for file_path in file_paths:
            self.context.trips.add_photo(self.trip_id, Path(file_path))
        self._refresh_photo_list()

    def _on_remove_photo(self) -> None:
        item = self._photo_list.currentItem()
        if item is None:
            return
        filename = item.data(Qt.ItemDataRole.UserRole)
        self.context.trips.remove_photo(self.trip_id, filename)
        self._refresh_photo_list()

    def _on_preview_photo(self, item: QListWidgetItem) -> None:
        filename = item.data(Qt.ItemDataRole.UserRole)
        path = self.context.trips.photo_path(self.trip_id, filename)
        if not path.exists():
            return

        preview = QDialog(self)
        preview.setWindowTitle(filename)
        preview_layout = QVBoxLayout(preview)
        image_label = QLabel()
        pixmap = QPixmap(str(path))
        image_label.setPixmap(
            pixmap.scaled(
                _PHOTO_PREVIEW_MAX_SIZE,
                _PHOTO_PREVIEW_MAX_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        preview_layout.addWidget(image_label)
        preview.exec()
