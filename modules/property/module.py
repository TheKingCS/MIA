"""
modules.property.module
==========================

Property — a read-only, at-a-glance place to check on the house itself
and everything in it that isn't a vehicle or power equipment: HVAC
filters, water heater, appliances, roof/gutter inspections, tools.
Garage's direct sibling — same "filtered aggregation view over
core.maintenance_manager, no add/edit/delete of its own" shape,
just PROPERTY_CATEGORIES instead of GARAGE_CATEGORIES. Managing an
asset or task still happens in Maintenance; this answers "what does
the house need" faster, the way Garage answers "how's the truck doing"
faster.

Deliberately its own module rather than a tab bolted onto Garage —
"cars and motorized things" and "the house and what's in it" are real,
separate mental categories a user reaches for independently (matches
the reasoning that kept Garage itself out of Workshop). Everything
about the layout, the free-function/no-cross-module-import shape, and
the deliberate "no deep link" limitation is identical to
modules/garage/module.py — see that file's docstring for the fuller
rationale, not repeated here.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from core.data_logger_manager import Reading
from core.maintenance_manager import (
    MaintenanceAsset,
    MaintenanceTask,
    days_until_due,
    is_meter_task_due,
    is_sensor_task_due,
    meter_used_since_last,
)
from modules.module_base import ModuleBase

PROPERTY_CATEGORIES = ["Appliance", "Property", "Tool"]
_SECTION_ITEM_LIMIT = 20


def is_property_asset(asset: MaintenanceAsset) -> bool:
    """Pure filter — testable without Qt (see tests/test_property_module.py)."""
    return asset.category in PROPERTY_CATEGORIES


def task_needs_attention(task: MaintenanceTask, today: date, readings: Optional[list[Reading]] = None) -> bool:
    """Pure logic — testable without Qt. Identical rule to
    modules.garage.module's version (calendar tasks count as needing
    attention from their due date onward, not just once overdue)."""
    readings = readings or []
    if task.trigger_type == "calendar":
        remaining = days_until_due(task, today)
        return remaining is not None and remaining <= 0
    if task.is_meter_task:
        return is_meter_task_due(task, readings)
    if task.is_sensor_task:
        return is_sensor_task_due(task, readings)
    return False


def format_task_status_line(task: MaintenanceTask, today: date, readings: Optional[list[Reading]] = None) -> str:
    """Pure formatting logic — testable without Qt. Same status
    vocabulary as modules.garage.module.format_task_status_line, owned
    independently here since modules never import another module
    directly (CLAUDE.md's one-directional layering rule)."""
    readings = readings or []

    if task.trigger_type == "calendar":
        remaining = days_until_due(task, today)
        if remaining is None:
            if task.interval_days is None:
                status = "one-time" if not task.last_completed else "done"
            else:
                status = "never done"
        elif remaining < 0:
            status = f"overdue {-remaining}d"
        elif remaining == 0:
            status = "due today"
        else:
            status = f"due in {remaining}d"
        return f"{task.title} — {status}"

    if task.is_meter_task:
        unit = task.meter_unit or "units"
        if task.last_completed_meter_value is None:
            status = "never done"
        elif not readings:
            status = "no readings logged"
        else:
            used = meter_used_since_last(task, readings) or 0.0
            interval = task.meter_interval or 0.0
            remaining_units = interval - used
            status = f"overdue {-remaining_units:.0f} {unit}" if remaining_units <= 0 else f"{used:.0f}/{interval:.0f} {unit}"
        return f"{task.title} — {status}"

    # Sensor task.
    if not readings:
        status = "no readings logged"
    else:
        latest = readings[-1].value
        unit = task.meter_unit or ""
        status = f"due — {latest:g}{unit}" if is_sensor_task_due(task, readings) else f"ok — {latest:g}{unit}"
    return f"{task.title} — {status}"


def format_attention_line(
    task: MaintenanceTask, asset: Optional[MaintenanceAsset], today: date, readings: Optional[list[Reading]] = None
) -> str:
    """Pure formatting logic — testable without Qt."""
    asset_name = asset.name if asset is not None else "Unknown asset"
    return f"{format_task_status_line(task, today, readings)}   ({asset_name})"


def format_glance_next_up(attention_count: int, first_task: Optional[MaintenanceTask]) -> str:
    """Pure formatting logic — testable without Qt. Same "don't rank
    across incomparable units" stance as modules.garage.module's version."""
    if attention_count == 0:
        return "All caught up"
    if attention_count == 1 and first_task is not None:
        return first_task.title
    return f"{attention_count} items"


class PropertyModule(ModuleBase):
    module_id = "property"
    display_name = "Property"
    description = "At-a-glance status for the house, appliances, and tools."
    icon = "\U0001F3E0"  # house

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list_layout: Optional[QVBoxLayout] = None
        self._tracked_value_label: Optional[QLabel] = None
        self._attention_value_label: Optional[QLabel] = None
        self._next_up_value_label: Optional[QLabel] = None

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

        manage_button = QPushButton("Manage in Maintenance →")
        manage_button.clicked.connect(self._on_manage_in_maintenance)
        outer.addWidget(manage_button, alignment=Qt.AlignmentFlag.AlignLeft)

        glance_row = QHBoxLayout()
        glance_row.setSpacing(24)
        self._tracked_value_label = self._build_glance_tile(glance_row, "Tracked")
        self._attention_value_label = self._build_glance_tile(glance_row, "Needs Attention")
        self._next_up_value_label = self._build_glance_tile(glance_row, "Next Up")
        outer.addLayout(glance_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._list_layout = QVBoxLayout(content)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        self._refresh()
        return page

    def _on_manage_in_maintenance(self) -> None:
        self.context.events.publish("assistant.open_module_requested", module_id="maintenance")

    def _build_glance_tile(self, row_layout: QHBoxLayout, caption: str) -> QLabel:
        tile = QVBoxLayout()
        value_label = QLabel("—")
        value_label.setObjectName("TitleLabel")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption_label = QLabel(caption)
        caption_label.setObjectName("SubtitleLabel")
        caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.addWidget(value_label)
        tile.addWidget(caption_label)
        row_layout.addLayout(tile)
        return value_label

    def _refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        today = date.today()
        assets = [a for a in self.context.maintenance.all_assets() if is_property_asset(a)]

        attention_entries: list[tuple[MaintenanceTask, MaintenanceAsset, list[Reading]]] = []
        asset_status_lines: dict[str, list[str]] = {}

        for asset in assets:
            lines = []
            for task in self.context.maintenance.tasks_for_asset(asset.asset_id):
                readings = (
                    self.context.maintenance.readings_for_task(task.task_id) if task.trigger_type != "calendar" else []
                )
                lines.append(format_task_status_line(task, today, readings))
                if task_needs_attention(task, today, readings):
                    attention_entries.append((task, asset, readings))
            asset_status_lines[asset.asset_id] = lines

        self._tracked_value_label.setText(str(len(assets)))
        self._attention_value_label.setText(str(len(attention_entries)))
        first_task = attention_entries[0][0] if attention_entries else None
        self._next_up_value_label.setText(format_glance_next_up(len(attention_entries), first_task))

        attention_lines = [
            format_attention_line(task, asset, today, readings) for task, asset, readings in attention_entries
        ][:_SECTION_ITEM_LIMIT]
        self._add_section("Needs Attention", attention_lines)

        if not assets:
            self._add_section(
                "House, Appliances & Tools",
                [],
                empty_text="Nothing tracked yet — add an Appliance, Property, or Tool asset in Maintenance.",
            )
            return

        for asset in assets:
            self._add_section(f"{asset.name}  [{asset.category}]", asset_status_lines[asset.asset_id][:_SECTION_ITEM_LIMIT])

    def _add_section(self, title: str, lines: list[str], empty_text: str = "Nothing here yet.") -> None:
        section_label = QLabel(title)
        section_label.setStyleSheet("font-weight: 600;")
        self._list_layout.addWidget(section_label)

        if not lines:
            empty_label = QLabel(empty_text)
            empty_label.setObjectName("SubtitleLabel")
            self._list_layout.addWidget(empty_label)
            return

        for line in lines:
            item_label = QLabel(f"- {line}")
            item_label.setWordWrap(True)
            self._list_layout.addWidget(item_label)
