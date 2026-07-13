"""
modules.expeditions.module
=============================

Expedition Mode — docs/ROADMAP.md milestone 12.1. Two-level CRUD:
Expeditions (the top-level dated outing, core.expedition_manager.Expedition)
at the top, and the selected Expedition's Trips (one activity/leg each —
hike, paddle, ride, fishing trip, etc., see core.trip_manager.ACTIVITY_TYPES
— core.trip_manager.Trip) below it. Selecting a Trip opens the Trip
detail dialog (gui/trip_detail_dialog.py), which milestone 12.1 uses
only for planned-route management (waypoint picker + ordered list +
planned distance) — gear (12.3), journal/weather (12.4), logged speed/
distance (12.5), the schematic map (12.6), and photos (12.7) all extend
that same dialog in later milestones rather than each getting a
separate screen.

format_expedition_row()/format_trip_row() are free functions (not
methods) — testable without Qt, see tests/test_expeditions_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from core.expedition_manager import Expedition
from core.trip_manager import Trip
from gui.add_edit_expedition_dialog import AddEditExpeditionDialog
from gui.add_edit_trip_dialog import AddEditTripDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from gui.trip_detail_dialog import TripDetailDialog
from modules.module_base import ModuleBase


def format_expedition_row(expedition: Expedition) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_expeditions_module.py)."""
    date_range = expedition.start_date
    if expedition.end_date and expedition.end_date != expedition.start_date:
        date_range = f"{expedition.start_date} - {expedition.end_date}"
    location = f"  ({expedition.location})" if expedition.location else ""
    return f"{expedition.name}  [{date_range}]{location}"


def format_trip_row(trip: Trip) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_expeditions_module.py)."""
    activity = f"[{trip.activity_type}] " if trip.activity_type else ""
    return f"{activity}{trip.name}  [{trip.start_date}]  ({trip.status})"


class ExpeditionsModule(ModuleBase):
    module_id = "expeditions"
    display_name = "Expeditions"
    description = "Expedition Mode: trip routes, gear, weather, and logged speed/distance for any outing."
    icon = "\U0001F3D5"  # camping

    def __init__(self, context) -> None:
        super().__init__(context)
        self._expedition_list: Optional[QListWidget] = None
        self._trip_list: Optional[QListWidget] = None

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

        expedition_title = QLabel("Expeditions")
        expedition_title.setObjectName("SubtitleLabel")
        layout.addWidget(expedition_title)

        self._expedition_list = QListWidget()
        self._expedition_list.currentItemChanged.connect(self._on_expedition_selected)
        layout.addWidget(self._expedition_list, stretch=1)

        expedition_buttons = QHBoxLayout()
        add_expedition_button = QPushButton("Add Expedition")
        add_expedition_button.clicked.connect(self._on_add_expedition)
        expedition_buttons.addWidget(add_expedition_button)

        edit_expedition_button = QPushButton("Edit Selected")
        edit_expedition_button.clicked.connect(self._on_edit_expedition)
        expedition_buttons.addWidget(edit_expedition_button)

        delete_expedition_button = QPushButton("Delete Selected")
        delete_expedition_button.clicked.connect(self._on_delete_expedition)
        expedition_buttons.addWidget(delete_expedition_button)
        layout.addLayout(expedition_buttons)

        trip_title = QLabel("Trips in selected Expedition")
        trip_title.setObjectName("SubtitleLabel")
        layout.addWidget(trip_title)

        self._trip_list = QListWidget()
        self._trip_list.itemDoubleClicked.connect(self._on_open_trip_detail)
        layout.addWidget(self._trip_list, stretch=1)

        trip_buttons = QHBoxLayout()
        add_trip_button = QPushButton("Add Trip")
        add_trip_button.clicked.connect(self._on_add_trip)
        trip_buttons.addWidget(add_trip_button)

        edit_trip_button = QPushButton("Edit Selected")
        edit_trip_button.clicked.connect(self._on_edit_trip)
        trip_buttons.addWidget(edit_trip_button)

        delete_trip_button = QPushButton("Delete Selected")
        delete_trip_button.clicked.connect(self._on_delete_trip)
        trip_buttons.addWidget(delete_trip_button)

        open_trip_button = QPushButton("Open Trip Detail")
        open_trip_button.clicked.connect(self._on_open_trip_detail)
        trip_buttons.addWidget(open_trip_button)
        layout.addLayout(trip_buttons)

        self._refresh_expedition_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_expedition_list(self) -> None:
        previously_selected = self._selected_expedition_id()

        self._expedition_list.clear()
        for expedition in self.context.expeditions.all_expeditions():
            item = QListWidgetItem(format_expedition_row(expedition))
            item.setData(Qt.ItemDataRole.UserRole, expedition.expedition_id)
            self._expedition_list.addItem(item)

        if previously_selected is not None:
            for row in range(self._expedition_list.count()):
                item = self._expedition_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == previously_selected:
                    self._expedition_list.setCurrentItem(item)
                    break
        self._refresh_trip_list()

    def _refresh_trip_list(self) -> None:
        self._trip_list.clear()
        expedition_id = self._selected_expedition_id()
        if expedition_id is None:
            return
        for trip in self.context.trips.trips_for_expedition(expedition_id):
            item = QListWidgetItem(format_trip_row(trip))
            item.setData(Qt.ItemDataRole.UserRole, trip.trip_id)
            self._trip_list.addItem(item)

    def _on_expedition_selected(self) -> None:
        self._refresh_trip_list()

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _selected_expedition_id(self) -> Optional[str]:
        item = self._expedition_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _selected_trip_id(self) -> Optional[str]:
        item = self._trip_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Expedition actions
    # ------------------------------------------------------------------

    def _on_add_expedition(self) -> None:
        dialog = AddEditExpeditionDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.expeditions.add_expedition(
            name=dialog.entered_name,
            start_date=dialog.entered_start_date,
            end_date=dialog.entered_end_date,
            location=dialog.entered_location,
            notes=dialog.entered_notes,
        )
        self._refresh_expedition_list()

    def _on_edit_expedition(self) -> None:
        expedition_id = self._selected_expedition_id()
        if expedition_id is None:
            QMessageBox.information(None, "No Expedition Selected", "Select an Expedition to edit.")
            return

        expedition = self.context.expeditions.get_expedition(expedition_id)
        dialog = AddEditExpeditionDialog(expedition=expedition)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.expeditions.update_expedition(
            expedition_id,
            name=dialog.entered_name,
            start_date=dialog.entered_start_date,
            end_date=dialog.entered_end_date,
            location=dialog.entered_location,
            notes=dialog.entered_notes,
        )
        self._refresh_expedition_list()

    def _on_delete_expedition(self) -> None:
        expedition_id = self._selected_expedition_id()
        if expedition_id is None:
            QMessageBox.information(None, "No Expedition Selected", "Select an Expedition to delete.")
            return

        expedition = self.context.expeditions.get_expedition(expedition_id)
        trip_count = len(self.context.trips.trips_for_expedition(expedition_id))
        if trip_count:
            proceed = QMessageBox.question(
                None,
                "Expedition Has Trips",
                f"'{expedition.name}' has {trip_count} trip(s) under it. Deleting the "
                "Expedition does not delete those trips — they'll just no longer be "
                "grouped under it. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        dialog = DeleteConfirmDialog(expedition.name, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.expeditions.delete_expedition(expedition_id)
        self._refresh_expedition_list()

    # ------------------------------------------------------------------
    # Trip actions
    # ------------------------------------------------------------------

    def _on_add_trip(self) -> None:
        expedition_id = self._selected_expedition_id()
        if expedition_id is None:
            QMessageBox.information(None, "No Expedition Selected", "Select an Expedition to add a trip to.")
            return

        dialog = AddEditTripDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.trips.add_trip(
            expedition_id=expedition_id,
            name=dialog.entered_name,
            start_date=dialog.entered_start_date,
            end_date=dialog.entered_end_date,
            activity_type=dialog.entered_activity_type,
            notes=dialog.entered_notes,
        )
        self._refresh_trip_list()

    def _on_edit_trip(self) -> None:
        trip_id = self._selected_trip_id()
        if trip_id is None:
            QMessageBox.information(None, "No Trip Selected", "Select a trip to edit.")
            return

        trip = self.context.trips.get_trip(trip_id)
        dialog = AddEditTripDialog(trip=trip)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.trips.update_trip(
            trip_id,
            name=dialog.entered_name,
            start_date=dialog.entered_start_date,
            end_date=dialog.entered_end_date,
            activity_type=dialog.entered_activity_type,
            notes=dialog.entered_notes,
        )
        self._refresh_trip_list()

    def _on_delete_trip(self) -> None:
        trip_id = self._selected_trip_id()
        if trip_id is None:
            QMessageBox.information(None, "No Trip Selected", "Select a trip to delete.")
            return

        trip = self.context.trips.get_trip(trip_id)
        dialog = DeleteConfirmDialog(trip.name, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.trips.delete_trip(trip_id)
        self._refresh_trip_list()

    def _on_open_trip_detail(self) -> None:
        trip_id = self._selected_trip_id()
        if trip_id is None:
            QMessageBox.information(None, "No Trip Selected", "Select a trip to open.")
            return

        dialog = TripDetailDialog(self.context, trip_id)
        dialog.exec()
        self._refresh_trip_list()
