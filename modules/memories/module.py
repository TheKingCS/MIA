"""
modules.memories.module
==========================

Memories — docs/ROADMAP.md milestone v0.17, module #19 in that doc's
"Top-level module sections" list. Displays one recap card per
Expedition (docs/ROADMAP.md 12.1), most-recent-first: duration,
per-activity-type distance/pace, waypoint categories visited, a photo
thumbnail strip, and a per-Trip row with a "View Route Map" button that
reuses gui/trip_detail_dialog.py's existing map view — the "location-
tagged logs surfaced on the maps" cross-link from the v0.17 breakdown,
without inventing any new map code. An "On This Day" section surfaces
above the main list when today's month/day matches a prior year's
Expedition start date.

Read-only: this module has no add/edit/delete of its own — Expeditions/
Trips/Waypoints/Journal entries are all still managed from their own
modules (Expeditions, Navigation, Notes). Memories only aggregates and
displays, matching core.memory_manager.MemoryManager's own read-only
design.

format_recap_header()/format_activity_stats_line()/
format_waypoint_categories_line() are free functions (not methods) —
testable without Qt, see tests/test_memories_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.memory_manager import ActivityStats, ExpeditionRecap
from gui.trip_detail_dialog import TripDetailDialog
from modules.module_base import ModuleBase

_PHOTO_THUMBNAIL_SIZE = QSize(72, 72)


def format_recap_header(recap: ExpeditionRecap) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_memories_module.py)."""
    expedition = recap.expedition
    date_range = expedition.start_date
    if expedition.end_date and expedition.end_date != expedition.start_date:
        date_range = f"{expedition.start_date} - {expedition.end_date}"
    location = f"  ({expedition.location})" if expedition.location else ""
    duration = f"  [{recap.duration_days} day{'s' if recap.duration_days != 1 else ''}]" if recap.duration_days else ""
    return f"{expedition.name}{location}  {date_range}{duration}".strip()


def format_activity_stats_line(stats: ActivityStats) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_memories_module.py)."""
    trip_word = "trip" if stats.trip_count == 1 else "trips"
    parts = [f"{stats.activity_type}: {stats.trip_count} {trip_word}"]
    if stats.distance_km:
        parts.append(f"{stats.distance_km:.1f} km")
    if stats.average_speed_kmh:
        parts.append(f"avg {stats.average_speed_kmh:.1f} km/h")
    return ", ".join(parts)


def format_waypoint_categories_line(categories: dict[str, int]) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_memories_module.py)."""
    if not categories:
        return ""
    parts = [f"{count} {category}" for category, count in sorted(categories.items())]
    return "Visited: " + ", ".join(parts)


class MemoriesModule(ModuleBase):
    module_id = "memories"
    display_name = "Memories"
    description = "Trip recaps, stats, and photos from your Expeditions."
    icon = "\U0001F4F8"  # camera with flash

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list_layout: Optional[QVBoxLayout] = None

    def get_widget(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._list_layout = QVBoxLayout(content)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(12)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        self._refresh()
        return page

    def _refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        on_this_day = self.context.memories.on_this_day()
        if on_this_day:
            section_label = QLabel("On This Day")
            section_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
            self._list_layout.addWidget(section_label)
            for recap in on_this_day:
                self._list_layout.addWidget(self._build_recap_card(recap))

        recaps = self.context.memories.all_recaps()
        if not recaps:
            empty_label = QLabel("No Expeditions yet — start one in the Expeditions module.")
            empty_label.setObjectName("SubtitleLabel")
            self._list_layout.addWidget(empty_label)
            return

        all_label = QLabel("All Expeditions")
        all_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        self._list_layout.addWidget(all_label)
        for recap in recaps:
            self._list_layout.addWidget(self._build_recap_card(recap))

    def _build_recap_card(self, recap: ExpeditionRecap) -> QFrame:
        card = QFrame()
        card.setObjectName("CharacterPanel")  # reuse the dashed-panel style
        layout = QVBoxLayout(card)

        header = QLabel(format_recap_header(recap))
        header.setStyleSheet("font-weight: 600;")
        header.setWordWrap(True)
        layout.addWidget(header)

        for stats in recap.activity_breakdown.values():
            stats_label = QLabel(format_activity_stats_line(stats))
            stats_label.setObjectName("SubtitleLabel")
            layout.addWidget(stats_label)

        categories_line = format_waypoint_categories_line(recap.waypoint_categories_visited)
        if categories_line:
            categories_label = QLabel(categories_line)
            categories_label.setObjectName("SubtitleLabel")
            layout.addWidget(categories_label)

        if recap.journal_highlights:
            latest = recap.journal_highlights[0]
            conditions = f" — {latest.conditions}" if latest.conditions else ""
            highlight_label = QLabel(f"Latest log: '{latest.title}'{conditions}")
            highlight_label.setObjectName("SubtitleLabel")
            highlight_label.setWordWrap(True)
            layout.addWidget(highlight_label)

        if recap.photo_filenames:
            photo_list = QListWidget()
            photo_list.setViewMode(QListWidget.ViewMode.IconMode)
            photo_list.setIconSize(_PHOTO_THUMBNAIL_SIZE)
            photo_list.setFixedHeight(_PHOTO_THUMBNAIL_SIZE.height() + 24)
            photo_list.setFlow(QListWidget.Flow.LeftToRight)
            photo_list.setResizeMode(QListWidget.ResizeMode.Adjust)
            for trip_id, filename in recap.photo_filenames:
                path = self.context.trips.photo_path(trip_id, filename)
                icon = QIcon(str(path)) if path.exists() else QIcon()
                photo_list.addItem(QListWidgetItem(icon, ""))
            layout.addWidget(photo_list)

        trips = self.context.trips.trips_for_expedition(recap.expedition.expedition_id)
        for trip in trips:
            trip_row = QHBoxLayout()
            trip_label = QLabel(f"- {trip.name}" + (f" [{trip.activity_type}]" if trip.activity_type else ""))
            trip_row.addWidget(trip_label, stretch=1)
            map_button = QPushButton("View Route Map")
            map_button.clicked.connect(lambda checked=False, t=trip.trip_id: self._on_view_route_map(t))
            trip_row.addWidget(map_button)
            layout.addLayout(trip_row)

        return card

    def _on_view_route_map(self, trip_id: str) -> None:
        dialog = TripDetailDialog(self.context, trip_id)
        dialog.exec()
