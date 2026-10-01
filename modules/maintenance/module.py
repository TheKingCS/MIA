"""
modules.maintenance.module
=============================

Maintenance: recurring upkeep tracking for anything the user owns that
needs it — vehicles, power equipment (mower, e-bike), appliances, the
property itself, and tools. Two tabs (Assets, Tasks), same
`QTabWidget` multi-feature-in-one-module shape as
modules/workshop/module.py, since Assets and Tasks are two views over
one closely-related data set rather than separate top-level modules.

All persistence/recurrence logic lives in core/maintenance_manager.py
(self.context.maintenance) — this module is the Qt-facing wrapper
around it, same split as Notes/Calendar/Alarm/Workshop.

The Tasks tab's "Schedule…" action is the real calendar-aware piece:
it opens gui/schedule_task_dialog.py, which reads
self.context.calendar.events_for_date() live as the picked date
changes, showing a real warning (not a static hint) if that day
already has something on it — informs, never blocks, same stance
every other action in this app takes.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.ownership import possessive
from core.data_logger_manager import Reading
from core.gamification import SkillWeight
from core.maintenance_manager import (
    MaintenanceAsset,
    MaintenanceTask,
    days_until_due,
    is_overdue,
    is_sensor_task_due,
    meter_used_since_last,
    next_occurrence_date,
    predicted_due_date,
    task_urgency,
)
from core.search_manager import SearchResult
from gui.add_edit_asset_dialog import AddEditAssetDialog
from gui.add_edit_maintenance_task_dialog import AddEditMaintenanceTaskDialog
from gui.log_asset_reading_dialog import LogAssetReadingDialog
from gui.log_reading_dialog import LogReadingDialog
from gui.mark_complete_dialog import MarkCompleteDialog
from gui.schedule_task_dialog import ScheduleTaskDialog
from gui.widgets.blueprint_frame import BlueprintFrame
from gui.widgets.glow import apply_panel_glow
from gui.widgets.sensor_chart import build_sensor_chart_view
from modules.module_base import ModuleBase


def format_asset_row(asset: MaintenanceAsset) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_maintenance_module.py)."""
    return f"{asset.name}   [{asset.category}]"


# "Smart calendar" pass (2026-09-12) — reuses this app's own already-
# established critical/warning colors (gui/styles.py's NotificationCard
# convention) rather than inventing new ones; on_track/unknown keep the
# list's default color (no entry here — see _color_for_urgency() below).
_URGENCY_COLORS = {
    "overdue": "#e06666",
    "due_soon": "#e0af68",
}


def _color_for_urgency(urgency: str) -> Optional[QColor]:
    """None means "leave the row at its default color" — never fabricate
    a color for on_track/unknown, same "don't decorate a non-event"
    restraint format_task_row() itself already applies."""
    hex_color = _URGENCY_COLORS.get(urgency)
    return QColor(hex_color) if hex_color else None


def format_priority_badge(priority: str) -> str:
    """Pure formatting logic — testable without Qt. "" for the default
    "normal" (no visual noise for the common case, same precedent as
    Mission's abandon_reason "(none)" convention)."""
    if priority == "high":
        return "[HIGH] "
    if priority == "low":
        return "[low] "
    return ""


def format_overview_row(task: MaintenanceTask, asset: Optional[MaintenanceAsset], occurrence_date) -> str:
    """Pure formatting logic — testable without Qt. For the Overview
    tab's This Week/This Month lists."""
    asset_name = asset.name if asset is not None else "Unknown asset"
    # %-d (no leading zero) is POSIX-only and not portable to native
    # Windows Python — %d plus a manual lstrip keeps this cross-platform.
    day = occurrence_date.strftime("%d").lstrip("0") or "0"
    date_text = f"{occurrence_date.strftime('%a %b')} {day}"
    return f"{date_text} — {format_priority_badge(task.priority)}{task.title} ({asset_name})"


def format_task_row(
    task: MaintenanceTask,
    asset: Optional[MaintenanceAsset],
    today: date,
    readings: Optional[list[Reading]] = None,
) -> str:
    """Pure formatting logic — testable without Qt. Status prefix leads
    with the most urgent real fact (overdue beats due-soon beats
    on-schedule beats one-time/never-completed/no-data), matching this
    app's general "surface the summary before the detail" dashboard-card
    convention applied here to a list row instead. `readings` is only
    consulted for meter/sensor tasks — pass core.maintenance_manager
    .MaintenanceManager.readings_for_task(task.task_id) for those; a
    calendar task ignores it entirely."""
    asset_name = asset.name if asset is not None else "Unknown asset"
    readings = readings or []

    if task.trigger_type == "calendar":
        remaining = days_until_due(task, today)
        if remaining is None:
            if task.interval_days is None:
                status = "[ONE-TIME]" if not task.last_completed else "[DONE]"
            else:
                status = "[NEVER DONE]"
        elif remaining < 0:
            status = f"[OVERDUE {-remaining}d]"
        elif remaining == 0:
            status = "[DUE TODAY]"
        else:
            status = f"[DUE IN {remaining}d]"
        return f"{status}  {format_priority_badge(task.priority)}{task.title}   ({asset_name})"

    if task.is_meter_task:
        unit = task.meter_unit or "units"
        if task.last_completed_meter_value is None:
            status = "[NEVER DONE]"
        elif not readings:
            status = "[NO READINGS LOGGED]"
        else:
            used = meter_used_since_last(task, readings) or 0.0
            interval = task.meter_interval or 0.0
            remaining_units = interval - used
            if remaining_units <= 0:
                status = f"[OVERDUE {-remaining_units:.0f} {unit}]"
            else:
                status = f"[{used:.0f}/{interval:.0f} {unit}]"
                prediction = predicted_due_date(task, readings, today)
                if prediction is not None:
                    _estimated, caveat = prediction
                    status += f"  ({caveat})"
                elif len(readings) < 2:
                    status += "  (not enough data logged yet)"
        return f"{status}  {format_priority_badge(task.priority)}{task.title}   ({asset_name})"

    # Sensor (threshold) task.
    if not readings:
        status = "[NO READINGS LOGGED]"
    else:
        latest = readings[-1].value
        unit = task.meter_unit or ""
        if is_sensor_task_due(task, readings):
            status = f"[DUE — {latest:g}{unit} {task.threshold_direction} {task.threshold_value:g}{unit}]"
        else:
            status = f"[OK — {latest:g}{unit}]"
    return f"{status}  {format_priority_badge(task.priority)}{task.title}   ({asset_name})"


class MaintenanceModule(ModuleBase):
    module_id = "maintenance"
    display_name = "Maintenance"
    description = "Recurring upkeep tracking for vehicles, equipment, appliances, property, and tools."
    icon = "\U0001F527"  # wrench

    def __init__(self, context) -> None:
        super().__init__(context)
        self._asset_filter_edit: Optional[QLineEdit] = None
        self._asset_list: Optional[QListWidget] = None
        self._task_filter_edit: Optional[QLineEdit] = None
        self._task_list: Optional[QListWidget] = None
        self._week_list: Optional[QListWidget] = None
        self._month_list: Optional[QListWidget] = None
        # Design restyle Phase 3 (2026-09-12) — Sensor Monitor tab state.
        self._monitor_asset_combo: Optional[QComboBox] = None
        self._monitor_series_combo: Optional[QComboBox] = None
        self._monitor_tile_row: Optional[QHBoxLayout] = None
        self._monitor_chart_container: Optional[QVBoxLayout] = None
        self._monitor_reading_task_combo: Optional[QComboBox] = None
        self._monitor_reading_value_edit: Optional[QLineEdit] = None
        self._monitor_quest_container: Optional[QVBoxLayout] = None

    def on_load(self) -> None:
        super().on_load()
        self.context.search.register_provider("maintenance", self._search)

    def refresh(self) -> None:
        """Re-read every list (ModuleBase.refresh: records changed elsewhere, e.g. by voice)."""
        self._refresh_asset_list()
        self._refresh_task_list()
        self._refresh_overview()

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
        tabs.addTab(self._build_assets_tab(), "Assets")
        tabs.addTab(self._build_tasks_tab(), "Tasks")
        tabs.addTab(self._build_overview_tab(), "Overview")
        tabs.addTab(self._build_monitor_tab(), "Monitor")
        # Same "every tab refreshes on every tabs.currentChanged" fix
        # this project already applied to Budget's own Summary/Trends
        # staleness bug — Overview needs to reflect whatever was just
        # added/completed on the Tasks tab, not just its state when the
        # module widget was first built. Monitor needs the same: a
        # reading logged on the Tasks tab (via LogReadingDialog) should
        # show up here without rebuilding the whole module widget.
        tabs.currentChanged.connect(lambda _index: self._refresh_overview())
        tabs.currentChanged.connect(lambda _index: self._refresh_monitor())
        layout.addWidget(tabs, stretch=1)

        return widget

    # ------------------------------------------------------------------
    # Assets tab
    # ------------------------------------------------------------------

    def _build_assets_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._asset_filter_edit = QLineEdit()
        self._asset_filter_edit.setPlaceholderText("Filter by name or category…")
        self._asset_filter_edit.textChanged.connect(lambda _text: self._refresh_asset_list())
        layout.addWidget(self._asset_filter_edit)

        self._asset_list = QListWidget()
        layout.addWidget(self._asset_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Asset")
        add_button.clicked.connect(self._on_add_asset)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_asset)
        button_row.addWidget(edit_button)

        log_usage_button = QPushButton("Log Usage…")
        log_usage_button.clicked.connect(self._on_log_asset_reading)
        button_row.addWidget(log_usage_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_asset)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_asset_list()
        return tab

    def _refresh_asset_list(self) -> None:
        query = self._asset_filter_edit.text().strip().lower()
        assets = self.context.maintenance.all_assets()
        if query:
            assets = [a for a in assets if query in a.name.lower() or query in a.category.lower()]

        self._asset_list.clear()
        for asset in assets:
            whose = possessive(self.context, asset.owner_profile_id) if asset.owner_profile_id else ""
            item = QListWidgetItem(format_asset_row(asset) + (f"  ·  {whose}" if whose else ""))
            item.setData(Qt.ItemDataRole.UserRole, asset.asset_id)
            self._asset_list.addItem(item)

    def _selected_asset_id(self) -> Optional[str]:
        item = self._asset_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_asset(self) -> None:
        dialog = AddEditAssetDialog(context=self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.add_asset(
            owner_profile_id=dialog.entered_owner_profile_id,
            name=dialog.entered_name,
            category=dialog.entered_category,
            notes=dialog.entered_notes,
            purchase_date=dialog.entered_purchase_date,
            serial_number=dialog.entered_serial_number,
            manufacturer=dialog.entered_manufacturer,
            model=dialog.entered_model,
            purchase_price=dialog.entered_purchase_price,
            warranty_until=dialog.entered_warranty_until,
        )
        self._refresh_asset_list()

    def _on_edit_asset(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.information(None, "No Asset Selected", "Select an asset to edit.")
            return

        asset = self.context.maintenance.get_asset(asset_id)
        dialog = AddEditAssetDialog(asset=asset, maintenance=self.context.maintenance, context=self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.update_asset(
            asset_id,
            owner_profile_id=dialog.entered_owner_profile_id,
            name=dialog.entered_name,
            category=dialog.entered_category,
            notes=dialog.entered_notes,
            purchase_date=dialog.entered_purchase_date,
            serial_number=dialog.entered_serial_number,
            manufacturer=dialog.entered_manufacturer,
            model=dialog.entered_model,
            purchase_price=dialog.entered_purchase_price,
            warranty_until=dialog.entered_warranty_until,
        )
        self._refresh_asset_list()
        self._refresh_task_list()

    def _on_delete_asset(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.information(None, "No Asset Selected", "Select an asset to delete.")
            return

        asset = self.context.maintenance.get_asset(asset_id)
        task_count = len(self.context.maintenance.tasks_for_asset(asset_id))
        warning = f" Its {task_count} task(s) will be deleted too." if task_count else ""
        confirm = QMessageBox.question(
            None,
            "Delete Asset",
            f"Delete '{asset.name}'?{warning}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.maintenance.delete_asset(asset_id)
        self._refresh_asset_list()
        self._refresh_task_list()

    def _on_log_asset_reading(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.information(None, "No Asset Selected", "Select an asset to log usage for.")
            return

        known_names = self.context.maintenance.asset_meter_names(asset_id)
        dialog = LogAssetReadingDialog(known_meter_names=known_names)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.log_asset_reading(
            asset_id, dialog.entered_meter_name, dialog.entered_value, unit=dialog.entered_unit, note=dialog.entered_note
        )

    # ------------------------------------------------------------------
    # Tasks tab
    # ------------------------------------------------------------------

    def _build_tasks_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._task_filter_edit = QLineEdit()
        self._task_filter_edit.setPlaceholderText("Filter by task or asset name…")
        self._task_filter_edit.textChanged.connect(lambda _text: self._refresh_task_list())
        layout.addWidget(self._task_filter_edit)

        self._task_list = QListWidget()
        layout.addWidget(self._task_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Task")
        add_button.clicked.connect(self._on_add_task)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_task)
        button_row.addWidget(edit_button)

        complete_button = QPushButton("Mark Complete")
        complete_button.clicked.connect(self._on_mark_complete)
        button_row.addWidget(complete_button)

        schedule_button = QPushButton("Schedule…")
        schedule_button.clicked.connect(self._on_schedule_task)
        button_row.addWidget(schedule_button)

        log_reading_button = QPushButton("Log Reading…")
        log_reading_button.clicked.connect(self._on_log_reading)
        button_row.addWidget(log_reading_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_task)
        button_row.addWidget(delete_button)

        layout.addLayout(button_row)

        self._refresh_task_list()
        return tab

    def _refresh_task_list(self) -> None:
        query = self._task_filter_edit.text().strip().lower()
        today = date.today()
        tasks = self.context.maintenance.all_tasks()

        self._task_list.clear()
        for task in tasks:
            asset = self.context.maintenance.get_asset(task.asset_id)
            readings = (
                self.context.maintenance.readings_for_task(task.task_id)
                if task.trigger_type != "calendar"
                else None
            )
            row_text = format_task_row(task, asset, today, readings)
            if query and query not in row_text.lower():
                continue
            item = QListWidgetItem(row_text)
            item.setData(Qt.ItemDataRole.UserRole, task.task_id)
            color = _color_for_urgency(task_urgency(task, readings or [], today))
            if color is not None:
                item.setForeground(color)
            self._task_list.addItem(item)

    def _selected_task_id(self) -> Optional[str]:
        item = self._task_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Overview tab — "smart calendar" pass (2026-09-12): a week/month
    # grouped view over the same tasks the Tasks tab shows, placed by
    # core.maintenance_manager.next_occurrence_date() (never a guessed
    # date — a task with no honest date, e.g. a sensor task that isn't
    # currently due, simply doesn't appear in either list).
    # ------------------------------------------------------------------

    def _build_overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        week_label = QLabel("This Week")
        week_label.setObjectName("SubtitleLabel")
        layout.addWidget(week_label)
        self._week_list = QListWidget()
        layout.addWidget(self._week_list, stretch=1)

        month_label = QLabel("This Month")
        month_label.setObjectName("SubtitleLabel")
        layout.addWidget(month_label)
        self._month_list = QListWidget()
        layout.addWidget(self._month_list, stretch=1)

        self._refresh_overview()
        return tab

    def _refresh_overview(self) -> None:
        today = date.today()
        week_cutoff = today.toordinal() + 7
        month_cutoff = today.toordinal() + 30

        week_rows: list[tuple[date, MaintenanceTask]] = []
        month_rows: list[tuple[date, MaintenanceTask]] = []
        for task in self.context.maintenance.all_tasks():
            readings = (
                self.context.maintenance.readings_for_task(task.task_id)
                if task.trigger_type != "calendar"
                else []
            )
            occurrence = next_occurrence_date(task, readings, today)
            if occurrence is None:
                continue
            if occurrence.toordinal() <= week_cutoff:
                week_rows.append((occurrence, task))
            if occurrence.toordinal() <= month_cutoff:
                month_rows.append((occurrence, task))

        self._populate_overview_list(self._week_list, week_rows, today)
        self._populate_overview_list(self._month_list, month_rows, today)

    def _populate_overview_list(self, list_widget: QListWidget, rows: list, today: date) -> None:
        list_widget.clear()
        for occurrence, task in sorted(rows, key=lambda pair: pair[0]):
            asset = self.context.maintenance.get_asset(task.asset_id)
            item = QListWidgetItem(format_overview_row(task, asset, occurrence))
            item.setData(Qt.ItemDataRole.UserRole, task.task_id)
            readings = (
                self.context.maintenance.readings_for_task(task.task_id)
                if task.trigger_type != "calendar"
                else []
            )
            color = _color_for_urgency(task_urgency(task, readings, today))
            if color is not None:
                item.setForeground(color)
            list_widget.addItem(item)

    # ------------------------------------------------------------------
    # Monitor tab — design restyle Phase 3 (2026-09-12): the handoff's
    # "1c Greenhouse & aquaponics monitor" screen, built as a generic
    # sensor monitor for whichever asset actually has trigger_type
    # "sensor" tasks — see this module's own git history / docs/ROADMAP.md
    # for why the mockup's literal grow-tower/fish/pump/pH content isn't
    # here: none of it has a backing field in MaintenanceAsset/
    # MaintenanceTask, and the design handoff's own rule is to prefer
    # the real model over inventing a number.
    # ------------------------------------------------------------------

    @staticmethod
    def _clear_layout(layout) -> None:
        """Same takeAt(0)/hide/setParent(None)/deleteLater idiom
        modules/missions/module.py's own _refresh_list() already uses."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _assets_with_sensor_tasks(self) -> list[MaintenanceAsset]:
        return [
            asset for asset in self.context.maintenance.all_assets()
            if any(t.is_sensor_task for t in self.context.maintenance.tasks_for_asset(asset.asset_id))
        ]

    def _build_monitor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._monitor_asset_combo = QComboBox()
        self._monitor_asset_combo.currentIndexChanged.connect(lambda _index: self._refresh_monitor())
        layout.addWidget(self._monitor_asset_combo)

        tile_row_widget = QWidget()
        self._monitor_tile_row = QHBoxLayout(tile_row_widget)
        layout.addWidget(tile_row_widget)

        split_row = QHBoxLayout()

        chart_card = BlueprintFrame()
        chart_card.setObjectName("DashboardCard")
        apply_panel_glow(chart_card)
        chart_card_layout = QVBoxLayout(chart_card)

        series_row = QHBoxLayout()
        series_label = QLabel("SENSOR TASK")
        series_label.setObjectName("MonitorTileEyebrow")
        series_row.addWidget(series_label)
        self._monitor_series_combo = QComboBox()
        self._monitor_series_combo.currentIndexChanged.connect(lambda _index: self._refresh_monitor_chart())
        series_row.addWidget(self._monitor_series_combo, stretch=1)
        chart_card_layout.addLayout(series_row)

        chart_container_widget = QWidget()
        self._monitor_chart_container = QVBoxLayout(chart_container_widget)
        chart_card_layout.addWidget(chart_container_widget, stretch=1)

        reading_row = QHBoxLayout()
        self._monitor_reading_task_combo = QComboBox()
        reading_row.addWidget(self._monitor_reading_task_combo, stretch=1)
        self._monitor_reading_value_edit = QLineEdit()
        self._monitor_reading_value_edit.setPlaceholderText("Value")
        reading_row.addWidget(self._monitor_reading_value_edit)
        log_button = QPushButton("Log")
        log_button.clicked.connect(self._on_monitor_log_reading)
        reading_row.addWidget(log_button)
        chart_card_layout.addLayout(reading_row)

        caption = QLabel("Manual entry until real hardware calls the same method.")
        caption.setObjectName("MonitorTileCaption")
        chart_card_layout.addWidget(caption)

        split_row.addWidget(chart_card, stretch=1)

        quest_card = BlueprintFrame(accent=True)
        quest_card.setObjectName("DashboardCard")
        apply_panel_glow(quest_card)
        quest_card.setFixedWidth(400)
        self._monitor_quest_container = QVBoxLayout(quest_card)
        split_row.addWidget(quest_card)

        layout.addLayout(split_row, stretch=1)

        self._refresh_monitor()
        return tab

    def _refresh_monitor(self) -> None:
        if self._monitor_asset_combo is None:
            return

        assets = self._assets_with_sensor_tasks()
        previous_asset_id = self._monitor_asset_combo.currentData()
        self._monitor_asset_combo.blockSignals(True)
        self._monitor_asset_combo.clear()
        for asset in assets:
            self._monitor_asset_combo.addItem(f"{asset.name}   [{asset.category}]", asset.asset_id)
        if previous_asset_id is not None:
            index = self._monitor_asset_combo.findData(previous_asset_id)
            if index >= 0:
                self._monitor_asset_combo.setCurrentIndex(index)
        self._monitor_asset_combo.blockSignals(False)

        self._clear_layout(self._monitor_tile_row)
        self._clear_layout(self._monitor_quest_container)
        self._monitor_reading_task_combo.clear()
        self._monitor_series_combo.blockSignals(True)
        self._monitor_series_combo.clear()

        if not assets:
            empty_label = QLabel("No assets have sensor tasks yet — add one in the Tasks tab.")
            empty_label.setObjectName("SubtitleLabel")
            self._monitor_tile_row.addWidget(empty_label)
            self._monitor_series_combo.blockSignals(False)
            self._refresh_monitor_chart()
            return

        asset_id = self._monitor_asset_combo.currentData()
        sensor_tasks = [
            t for t in self.context.maintenance.tasks_for_asset(asset_id) if t.is_sensor_task
        ] if asset_id else []

        today = date.today()
        due_tasks = []
        for task in sensor_tasks:
            readings = self.context.maintenance.readings_for_task(task.task_id)
            latest = readings[-1] if readings else None

            tile = BlueprintFrame()
            tile.setObjectName("MonitorTile")
            tile_layout = QVBoxLayout(tile)
            eyebrow = QLabel(task.title.upper())
            eyebrow.setObjectName("MonitorTileEyebrow")
            tile_layout.addWidget(eyebrow)
            value_text = f"{latest.value:g} {latest.unit}".strip() if latest is not None else "—"
            value_label = QLabel(value_text)
            value_label.setObjectName("MonitorTileValue")
            tile_layout.addWidget(value_label)
            if task.threshold_value is not None:
                target_caption = QLabel(f"target: {task.threshold_direction} {task.threshold_value:g}")
                target_caption.setObjectName("MonitorTileCaption")
                tile_layout.addWidget(target_caption)
            self._monitor_tile_row.addWidget(tile)

            self._monitor_series_combo.addItem(task.title, task.task_id)
            self._monitor_reading_task_combo.addItem(task.title, task.task_id)

            if readings and is_sensor_task_due(task, readings):
                due_tasks.append(task)

        self._monitor_series_combo.blockSignals(False)
        self._refresh_monitor_chart()
        self._refresh_monitor_quest_card(due_tasks)

    def _refresh_monitor_chart(self) -> None:
        if self._monitor_chart_container is None:
            return
        self._clear_layout(self._monitor_chart_container)

        task_id = self._monitor_series_combo.currentData() if self._monitor_series_combo.count() else None
        if task_id is None:
            empty_label = QLabel("No sensor tasks on this asset yet.")
            empty_label.setObjectName("SubtitleLabel")
            self._monitor_chart_container.addWidget(empty_label)
            return

        task = self.context.maintenance.get_task(task_id)
        readings = self.context.maintenance.readings_for_task(task_id)
        chart_view = build_sensor_chart_view(readings, task.threshold_value, task.threshold_direction) if task else None
        if chart_view is None:
            empty_label = QLabel("No readings yet.")
            empty_label.setObjectName("SubtitleLabel")
            self._monitor_chart_container.addWidget(empty_label)
        else:
            self._monitor_chart_container.addWidget(chart_view)

    def _refresh_monitor_quest_card(self, due_tasks: list[MaintenanceTask]) -> None:
        if not due_tasks:
            hint = QLabel("No sensor thresholds currently crossed.")
            hint.setObjectName("SubtitleLabel")
            self._monitor_quest_container.addWidget(hint)
            self._monitor_quest_container.addStretch(1)
            return

        # Only the first currently-due sensor task gets a card this
        # pass — showing one at a time matches the design's own single-
        # card layout; a real multi-alert stack is separate future scope.
        task = due_tasks[0]
        eyebrow = QLabel("SENSOR TASK · THRESHOLD CROSSED")
        eyebrow.setObjectName("MonitorTileEyebrow")
        self._monitor_quest_container.addWidget(eyebrow)

        title = QLabel(task.title)
        title.setObjectName("MissionDetailTitle")
        title.setWordWrap(True)
        self._monitor_quest_container.addWidget(title)

        body = QLabel("MIA noticed this reading cross its threshold — worth a look.")
        body.setWordWrap(True)
        self._monitor_quest_container.addWidget(body)

        reward = QLabel("+10 XP · home_maintenance")
        reward.setObjectName("MonitorTileCaption")
        self._monitor_quest_container.addWidget(reward)

        quest_button = QPushButton("START QUEST")
        quest_button.clicked.connect(lambda: self._on_start_quest(task.task_id))
        self._monitor_quest_container.addWidget(quest_button)
        self._monitor_quest_container.addStretch(1)

    def _on_monitor_log_reading(self) -> None:
        task_id = self._monitor_reading_task_combo.currentData()
        if task_id is None:
            QMessageBox.information(None, "No Sensor Task", "This asset has no sensor tasks to log a reading against.")
            return
        value_text = self._monitor_reading_value_edit.text().strip()
        try:
            value = float(value_text)
        except ValueError:
            QMessageBox.information(None, "Invalid Value", "Enter a numeric value.")
            return
        self.context.maintenance.log_reading(task_id, value)
        self._monitor_reading_value_edit.clear()
        self._refresh_monitor()

    def _on_start_quest(self, task_id: str) -> None:
        """Finds or creates exactly one Mission for this sensor task
        (core.mission_manager.Mission.maintenance_task_id), then opens
        the Missions module — same "assistant.open_module_requested"
        mechanism gui/home_dashboard.py's own _open_module() already
        uses. No deep-link to the mission's own detail row exists yet
        (see this phase's own plan/ROADMAP entry) — the user finds it
        in the list, which will be the newest entry."""
        existing = self.context.missions.missions_for_maintenance_task(task_id)
        if not existing:
            task = self.context.maintenance.get_task(task_id)
            if task is not None:
                mission = self.context.missions.add_mission(
                    name=f"Inspect: {task.title}",
                    maintenance_task_id=task_id,
                    assigned_by="mia",
                    icon="\U0001F527",
                    summary=f"A sensor reading on '{task.title}' crossed its threshold — take a look.",
                    skill_rewards=[SkillWeight("home_maintenance", 10)],
                )
                self.context.missions.add_objective(mission.mission_id, "Resolve it", "tally", 1)
        self.context.events.publish("assistant.open_module_requested", module_id="missions")

    def _on_add_task(self) -> None:
        assets = self.context.maintenance.all_assets()
        if not assets:
            QMessageBox.information(None, "No Assets Yet", "Add an asset first (Assets tab) before adding a task for it.")
            return

        dialog = AddEditMaintenanceTaskDialog(assets=assets)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.add_task(
            asset_id=dialog.entered_asset_id,
            title=dialog.entered_title,
            interval_days=dialog.entered_interval_days,
            notes=dialog.entered_notes,
            trigger_type=dialog.entered_trigger_type,
            meter_unit=dialog.entered_meter_unit,
            meter_interval=dialog.entered_meter_interval,
            threshold_value=dialog.entered_threshold_value,
            threshold_direction=dialog.entered_threshold_direction,
            auto_schedule=dialog.entered_auto_schedule,
            priority=dialog.entered_priority,
            tracks_lifetime_usage=dialog.entered_tracks_lifetime_usage,
        )
        self._refresh_task_list()

    def _on_edit_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to edit.")
            return

        task = self.context.maintenance.get_task(task_id)
        assets = self.context.maintenance.all_assets()
        dialog = AddEditMaintenanceTaskDialog(assets=assets, task=task)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.update_task(
            task_id,
            asset_id=dialog.entered_asset_id,
            title=dialog.entered_title,
            interval_days=dialog.entered_interval_days,
            notes=dialog.entered_notes,
            trigger_type=dialog.entered_trigger_type,
            meter_unit=dialog.entered_meter_unit,
            meter_interval=dialog.entered_meter_interval,
            threshold_value=dialog.entered_threshold_value,
            threshold_direction=dialog.entered_threshold_direction,
            auto_schedule=dialog.entered_auto_schedule,
            priority=dialog.entered_priority,
            tracks_lifetime_usage=dialog.entered_tracks_lifetime_usage,
        )
        self._refresh_task_list()

    def _on_mark_complete(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to mark complete.")
            return

        task = self.context.maintenance.get_task(task_id)
        if task.is_meter_task:
            latest = self.context.maintenance.readings_for_task(task_id)
            default_value = latest[-1].value if latest else None
            dialog = MarkCompleteDialog(unit=task.meter_unit, default_value=default_value)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.context.maintenance.mark_complete(task_id, meter_value=dialog.entered_value)
        else:
            self.context.maintenance.mark_complete(task_id)
        self._refresh_task_list()

    def _on_log_reading(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to log a reading for.")
            return

        task = self.context.maintenance.get_task(task_id)
        if not (task.is_meter_task or task.is_sensor_task):
            QMessageBox.information(
                None, "Not a Meter/Sensor Task", "Only Runtime, Mileage, Cycles, Condition, and Sensor tasks take logged readings."
            )
            return

        dialog = LogReadingDialog(unit=task.meter_unit)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.log_reading(task_id, dialog.entered_value, note=dialog.entered_note)
        self._refresh_task_list()

    def _on_schedule_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to schedule.")
            return

        dialog = ScheduleTaskDialog(calendar=self.context.calendar)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.schedule_task(task_id, dialog.entered_date)
        self._refresh_task_list()
        QMessageBox.information(None, "Scheduled", f"Added to the Calendar on {dialog.entered_date}.")

    def _on_delete_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to delete.")
            return

        task = self.context.maintenance.get_task(task_id)
        confirm = QMessageBox.question(
            None,
            "Delete Task",
            f"Delete '{task.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.context.maintenance.delete_task(task_id)
        self._refresh_task_list()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search(self, query: str) -> list[SearchResult]:
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        results = []
        for asset in self.context.maintenance.all_assets():
            if query_lower in asset.name.lower() or query_lower in asset.category.lower():
                results.append(SearchResult(
                    title=asset.name,
                    description=f"Maintenance asset — {asset.category}",
                    source=self.display_name,
                    action_type="open_module",
                    action_target=self.module_id,
                ))
        for task in self.context.maintenance.all_tasks():
            if query_lower in task.title.lower():
                asset = self.context.maintenance.get_asset(task.asset_id)
                results.append(SearchResult(
                    title=task.title,
                    description=f"Maintenance task — {asset.name if asset else 'Unknown asset'}",
                    source=self.display_name,
                    action_type="open_module",
                    action_target=self.module_id,
                ))
        return results
