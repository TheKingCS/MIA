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
from PySide6.QtWidgets import (
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

from core.data_logger_manager import Reading
from core.maintenance_manager import (
    MaintenanceAsset,
    MaintenanceTask,
    days_until_due,
    is_overdue,
    is_sensor_task_due,
    meter_used_since_last,
    predicted_due_date,
)
from core.search_manager import SearchResult
from gui.add_edit_asset_dialog import AddEditAssetDialog
from gui.add_edit_maintenance_task_dialog import AddEditMaintenanceTaskDialog
from gui.log_asset_reading_dialog import LogAssetReadingDialog
from gui.log_reading_dialog import LogReadingDialog
from gui.mark_complete_dialog import MarkCompleteDialog
from gui.schedule_task_dialog import ScheduleTaskDialog
from modules.module_base import ModuleBase


def format_asset_row(asset: MaintenanceAsset) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_maintenance_module.py)."""
    return f"{asset.name}   [{asset.category}]"


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
        return f"{status}  {task.title}   ({asset_name})"

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
        return f"{status}  {task.title}   ({asset_name})"

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
    return f"{status}  {task.title}   ({asset_name})"


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

    def on_load(self) -> None:
        super().on_load()
        self.context.search.register_provider("maintenance", self._search)

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
            item = QListWidgetItem(format_asset_row(asset))
            item.setData(Qt.ItemDataRole.UserRole, asset.asset_id)
            self._asset_list.addItem(item)

    def _selected_asset_id(self) -> Optional[str]:
        item = self._asset_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_asset(self) -> None:
        dialog = AddEditAssetDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.add_asset(
            name=dialog.entered_name,
            category=dialog.entered_category,
            notes=dialog.entered_notes,
            purchase_date=dialog.entered_purchase_date,
            serial_number=dialog.entered_serial_number,
            manufacturer=dialog.entered_manufacturer,
            model=dialog.entered_model,
        )
        self._refresh_asset_list()

    def _on_edit_asset(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.information(None, "No Asset Selected", "Select an asset to edit.")
            return

        asset = self.context.maintenance.get_asset(asset_id)
        dialog = AddEditAssetDialog(asset=asset, maintenance=self.context.maintenance)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.maintenance.update_asset(
            asset_id,
            name=dialog.entered_name,
            category=dialog.entered_category,
            notes=dialog.entered_notes,
            purchase_date=dialog.entered_purchase_date,
            serial_number=dialog.entered_serial_number,
            manufacturer=dialog.entered_manufacturer,
            model=dialog.entered_model,
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
            self._task_list.addItem(item)

    def _selected_task_id(self) -> Optional[str]:
        item = self._task_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

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
