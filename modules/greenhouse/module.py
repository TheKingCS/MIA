"""
modules.greenhouse.module
============================

Greenhouse — a read-only, at-a-glance place to check on garden/plant
assets (a greenhouse, aquaponics system, raised beds — anything logged
in core.maintenance_manager under category "Garden/Plant"), without
digging through every maintenance category in the general Maintenance
module. Garage/Property's third sibling — same "filtered aggregation
view over core.maintenance_manager, no add/edit/delete of its own"
shape, just GREENHOUSE_CATEGORIES instead of GARAGE_CATEGORIES/
PROPERTY_CATEGORIES.

Added 2026-09-13, at the user's own explicit request for real parity
across "areas" (the garage, the home, the greenhouse — each is like a
boss with missions fighting to keep it in good standing): before this,
Garden/Plant assets had no dedicated section of their own at all,
unlike Vehicle/Power Equipment (Garage) or Property/Appliance/Tool
(Property) — only the generic, all-categories Maintenance Assets tab.
Clicking an asset's section header opens a real detail page (same
QStackedWidget "← Back" pattern Garage/Property/Real Estate already
use) showing its full task status plus
gui/widgets/asset_missions_panel.py's shared "Related Missions" list.

is_greenhouse_asset()/task_needs_attention()/format_task_status_line()/
format_attention_line() are free functions (not methods), independently
owned rather than imported from modules.garage.module — modules never
import another module directly (CLAUDE.md's one-directional layering
rule), same stance Garage/Property already take relative to each
other.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.data_logger_manager import Reading
from core.maintenance_manager import (
    MaintenanceAsset,
    MaintenanceTask,
    days_until_due,
    is_meter_task_due,
    is_sensor_task_due,
    meter_used_since_last,
)
from gui.widgets.asset_missions_panel import build_asset_missions_panel
from gui.widgets.blueprint_frame import BlueprintFrame
from gui.widgets.glow import apply_panel_glow
from modules.module_base import ModuleBase

GREENHOUSE_CATEGORIES = ["Garden/Plant"]
_SECTION_ITEM_LIMIT = 20


def is_greenhouse_asset(asset: MaintenanceAsset) -> bool:
    """Pure filter — testable without Qt (see tests/test_greenhouse_module.py)."""
    return asset.category in GREENHOUSE_CATEGORIES


def task_needs_attention(task: MaintenanceTask, today: date, readings: Optional[list[Reading]] = None) -> bool:
    """Pure logic — testable without Qt. Identical rule to
    modules.garage.module's/modules.property.module's own versions."""
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
    independently here (modules never import another module directly)."""
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


class GreenhouseModule(ModuleBase):
    module_id = "greenhouse"
    display_name = "Greenhouse"
    description = "At-a-glance status for garden, greenhouse, and aquaponics assets."
    icon = "\U0001F331"  # seedling

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list_layout: Optional[QVBoxLayout] = None
        self._tracked_value_label: Optional[QLabel] = None
        self._attention_value_label: Optional[QLabel] = None
        self._next_up_value_label: Optional[QLabel] = None
        self._stack: Optional[QStackedWidget] = None
        self._list_page: Optional[QWidget] = None
        self._detail_page: Optional[QWidget] = None

    def get_widget(self) -> QWidget:
        self._stack = QStackedWidget()
        self._list_page = self._build_list_page()
        self._stack.addWidget(self._list_page)
        return self._stack

    def focus_record(self, record_id: str) -> None:
        """Cross-module deep-linking (2026-09-13) — same mechanism
        Real Estate/Garage/Property's own focus_record() use."""
        self._show_detail_page(record_id)

    def _show_list_page(self) -> None:
        self._refresh()
        self._stack.setCurrentWidget(self._list_page)

    def _show_detail_page(self, asset_id: str) -> None:
        if self._detail_page is not None:
            self._stack.removeWidget(self._detail_page)
            self._detail_page = None
        self._detail_page = self._build_detail_page(asset_id)
        self._stack.addWidget(self._detail_page)
        self._stack.setCurrentWidget(self._detail_page)

    def _build_detail_page(self, asset_id: str) -> QWidget:
        asset = self.context.maintenance.get_asset(asset_id)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        back_button = QPushButton("← Back to Greenhouse")
        back_button.clicked.connect(self._show_list_page)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        if asset is None:
            layout.addWidget(QLabel("This asset no longer exists."))
            return page

        header = QLabel(f"{asset.name}  [{asset.category}]")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        today = date.today()
        status_title = QLabel("Status")
        status_title.setStyleSheet("font-weight: 600;")
        layout.addWidget(status_title)
        tasks = self.context.maintenance.tasks_for_asset(asset.asset_id)
        if not tasks:
            empty = QLabel("No maintenance tasks tracked for this asset yet.")
            empty.setObjectName("SubtitleLabel")
            layout.addWidget(empty)
        for task in tasks:
            readings = (
                self.context.maintenance.readings_for_task(task.task_id) if task.trigger_type != "calendar" else []
            )
            line = QLabel(f"- {format_task_status_line(task, today, readings)}")
            line.setWordWrap(True)
            layout.addWidget(line)

        layout.addWidget(build_asset_missions_panel(self.context, asset.asset_id))
        layout.addStretch(1)
        return page

    def _build_list_page(self) -> QWidget:
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
        """Design/style catch-up (2026-09-14) — real #MonitorTile card
        (BlueprintFrame + the same eyebrow/value objectNames Maintenance's
        own Sensor Monitor tab uses), not a bare QLabel pair, so this
        glance row reads as an instrument-panel tile like the rest of
        the restyled screens rather than plain stacked text."""
        tile = BlueprintFrame()
        tile.setObjectName("MonitorTile")
        tile_layout = QVBoxLayout(tile)
        eyebrow = QLabel(caption.upper())
        eyebrow.setObjectName("MonitorTileEyebrow")
        tile_layout.addWidget(eyebrow)
        value_label = QLabel("—")
        value_label.setObjectName("MonitorTileValue")
        tile_layout.addWidget(value_label)
        row_layout.addWidget(tile)
        return value_label

    def _refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        today = date.today()
        assets = [a for a in self.context.maintenance.all_assets() if is_greenhouse_asset(a)]

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
                "Garden & Greenhouse",
                [],
                empty_text="Nothing tracked yet — add a Garden/Plant asset in Maintenance.",
            )
            return

        for asset in assets:
            self._add_section(
                f"{asset.name}  [{asset.category}]",
                asset_status_lines[asset.asset_id][:_SECTION_ITEM_LIMIT],
                asset_id=asset.asset_id,
            )

    def _add_section(
        self, title: str, lines: list[str], empty_text: str = "Nothing here yet.", asset_id: Optional[str] = None,
    ) -> None:
        """Design/style catch-up (2026-09-14) — every section is now a
        real #DashboardCard, matching gui/home_dashboard.py's own
        clickable-widget-card convention, instead of a plain QPushButton
        text header with bare QLabel lines floating under it. A given
        asset (asset_id set) gets the clickable QPushButton variant
        (whole card opens its detail page, not just the title text); a
        cross-asset callout like "Needs Attention" (asset_id is None)
        gets the same accent-glow BlueprintFrame treatment Maintenance's
        own Sensor Monitor tab uses for its "due tasks" quest card —
        it's the same kind of thing, a boss's outstanding fight list."""
        if asset_id is not None:
            card = QPushButton()
            card.setObjectName("DashboardCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setToolTip(f"Open {title}")
            card.setMinimumHeight(96)
            card.clicked.connect(lambda checked=False, aid=asset_id: self._show_detail_page(aid))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 16, 18, 16)
            card_layout.setSpacing(6)

            header_row = QHBoxLayout()
            title_label = QLabel(f"{title}  ›")
            title_label.setObjectName("MonitorTileValue")
            header_row.addWidget(title_label, stretch=1)
            card_layout.addLayout(header_row)
        else:
            card = BlueprintFrame(accent=True)
            card.setObjectName("DashboardCard")
            apply_panel_glow(card)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 16, 18, 16)
            card_layout.setSpacing(6)

            eyebrow = QLabel(title.upper())
            eyebrow.setObjectName("MonitorTileEyebrow")
            card_layout.addWidget(eyebrow)

        if not lines:
            empty_label = QLabel(empty_text)
            empty_label.setObjectName("SubtitleLabel")
            empty_label.setWordWrap(True)
            card_layout.addWidget(empty_label)
        for line in lines:
            item_label = QLabel(f"- {line}")
            item_label.setObjectName("MonitorTileCaption")
            item_label.setWordWrap(True)
            card_layout.addWidget(item_label)

        self._list_layout.addWidget(card)
