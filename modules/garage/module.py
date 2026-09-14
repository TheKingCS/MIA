"""
modules.garage.module
========================

Garage — a read-only, at-a-glance place to check on cars and other
motorized property equipment, without digging through every maintenance
task in the general Maintenance module. Purely a filtered aggregation
view over core.maintenance_manager (self.context.maintenance) — same
"no add/edit/delete of its own" stance as modules/dashboard/module.py;
managing an asset or task still happens in Maintenance, this just
answers "how's the truck doing" faster.

A "Manage in Maintenance" button navigates there via the existing
"assistant.open_module_requested" event (gui/main_window.py already
subscribes to it — same mechanism gui/home_dashboard.py's cards and
modules/field_kit/module.py's docked-Core auto-navigate use).

**Mission-to-asset tagging (2026-09-13)**: this module's own docstring
used to say no deep link to a specific asset existed anywhere — that's
now closed. Clicking an asset's own section header opens a real detail
page (same `QStackedWidget` "← Back" pattern `modules/real_estate/module.py`
already uses) showing its full task status plus
`gui/widgets/asset_missions_panel.py`'s shared "Related Missions" list
— real parity with Real Estate/Property/Greenhouse, at the user's own
explicit request, not a Garage-only special case.

Filtered to GARAGE_CATEGORIES (Vehicle, Power Equipment) — the "cars and
motorized things" the user asked this view to cover, not every
maintenance category (Appliance/Property/Tool stay in the general
Maintenance module only). This was originally floated as folding into
"MIA Workshop," but modules/workshop/module.py is a distinct
electronics/fab business pipeline (Components/Materials/Jobs/Products/
Ledger) with zero asset/serial/maintenance-schedule concepts — Garage
reads from Maintenance instead, which already owns this exact data
model (assets/tasks/documents/meter+sensor readings).

Layout follows the "glance tier -> needs-attention zone -> grouped
detail" information-architecture pattern from an earlier MIA Homestead
dashboard redesign: 3 hero glance tiles first (Tracked / Needs
Attention / Next Up), then everything across every garage asset that
needs a human pulled into one distinctly-labeled "Needs Attention"
zone, then full per-asset detail grouped under each asset's own
sub-header (its status lines, not squeezed into a single flat list).

is_garage_asset()/task_needs_attention()/format_task_status_line()/
format_attention_line() are free functions (not methods) — testable
without Qt, see tests/test_garage_module.py. These deliberately don't
import modules.maintenance.module's format_task_row/format_asset_row —
modules never import another module directly (CLAUDE.md's
one-directional layering rule); same stance modules/dashboard/module.py
already documents for its own summary-line functions. The underlying
due/overdue math (days_until_due/is_meter_task_due/is_sensor_task_due/
meter_used_since_last) IS reused directly from core.maintenance_manager
— only the presentation strings are independently owned.

**"Nature" re-skin pilot (2026-09-14)**: Garage is the first module
rebuilt against the user's own reference mockup — a warm photographic
hero header + forest-green/coral rounded cards, a deliberately
different visual direction from the teal HUD system (BlueprintFrame/
#DashboardCard/#MonitorTile) every other module still uses. This is an
explicit pilot: get sign-off on the look here before touching
Greenhouse/Kitchen/Workout/Real Estate/Missions/Skills/Household, per
the user's own chosen sequencing. The reference mockup's own asset
photography (mower/truck/Camaro thumbnails) was too low-resolution
(~150px) to extract and ship — `gui/widgets/photo_background_frame.py`
paints a gradient placeholder until real photography exists; swapping
in a real photo later needs no other code changes. The per-asset
detail page (`_build_detail_page()`) got the same treatment later the
same day — see its own docstring below for that pass's details
(NatureAssetCard/NatureGlanceTile throughout); nothing here is still
on the old teal-HUD look.
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
from gui.widgets.photo_background_frame import PhotoBackgroundFrame
from modules.module_base import ModuleBase

GARAGE_CATEGORIES = ["Vehicle", "Power Equipment"]
_SECTION_ITEM_LIMIT = 20


def is_garage_asset(asset: MaintenanceAsset) -> bool:
    """Pure filter — testable without Qt (see tests/test_garage_module.py)."""
    return asset.category in GARAGE_CATEGORIES


def task_needs_attention(task: MaintenanceTask, today: date, readings: Optional[list[Reading]] = None) -> bool:
    """Pure logic — testable without Qt. A calendar task counts as
    needing attention once its due date has arrived (not just past it —
    "due today" belongs in the same zone as overdue, not left for the
    per-asset detail section to surface quietly)."""
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
    vocabulary as modules.maintenance.module.format_task_row but
    independently owned (see module docstring)."""
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
    """Pure formatting logic — testable without Qt. Same as
    format_task_status_line but with the asset name appended, for the
    flat cross-asset "Needs Attention" zone."""
    asset_name = asset.name if asset is not None else "Unknown asset"
    return f"{format_task_status_line(task, today, readings)}   ({asset_name})"


def is_quick_stat_task(task: MaintenanceTask) -> bool:
    """Pure filter — testable without Qt. A meter/sensor task with no
    due-date configuration at all (no meter_interval / no
    threshold_value) is a pure live-reading tracker — e.g. "Engine
    Hours"/"Fuel Level" — not something that itself goes overdue, so
    it belongs in the detail page's quick-stats strip, not the Current
    Tasks list. (Other meter/sensor tasks, like the mower's hour-based
    Oil & filter change, DO have a meter_interval and stay in Current
    Tasks as usual.)"""
    if task.is_meter_task:
        return task.meter_interval is None
    if task.is_sensor_task:
        return task.threshold_value is None
    return False


def format_quick_stat_value(readings: list[Reading], unit: str) -> str:
    """Pure formatting logic — testable without Qt. The latest logged
    reading for a quick-stat task, or an honest "no reading logged"
    rather than fabricating one."""
    if not readings:
        return "no reading logged"
    return f"{readings[-1].value:g} {unit}".strip()


def next_up_tasks(
    actionable_tasks: list[MaintenanceTask], attention_tasks: list[MaintenanceTask], limit: int = 3
) -> list[MaintenanceTask]:
    """Pure logic — testable without Qt. Actionable tasks not already
    in the attention list, in their existing order — deliberately no
    cross-type ranking across days/hours/percent (same "don't rank
    across incomparable units" stance as format_glance_next_up()
    below), capped at `limit` for the Overview tab's "Next Up" card."""
    attention_ids = {t.task_id for t in attention_tasks}
    return [t for t in actionable_tasks if t.task_id not in attention_ids][:limit]


def format_glance_next_up(attention_count: int, first_task: Optional[MaintenanceTask]) -> str:
    """Pure formatting logic — testable without Qt. Deliberately doesn't
    try to rank across mechanically-incomparable units (days vs. miles
    vs. a raw sensor value) — just names the one thing needing
    attention when there's exactly one, a count otherwise, and an
    honest "All caught up" when there's nothing."""
    if attention_count == 0:
        return "All caught up"
    if attention_count == 1 and first_task is not None:
        return first_task.title
    return f"{attention_count} items"


class GarageModule(ModuleBase):
    module_id = "garage"
    display_name = "Garage"
    description = "At-a-glance status for vehicles and motorized equipment."
    icon = "\U0001F697"  # car

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
        Real Estate/Property/Greenhouse's own focus_record() use."""
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
        """Nature re-skin pilot, detail page — information-architecture
        pass (2026-09-14). The first pass flattened everything into one
        scroll; re-examined the reference mockup and it actually
        organizes into a real tab bar (Overview/Maintenance/Missions/
        Documents/Parts/History) with a distinct "Next Up" card the
        first pass had dropped entirely. Rebuilt around a real tab row
        (a plain button row + QStackedWidget, not QPushButton
        QTabWidget's own unstyled default chrome) — Overview is a
        condensed summary (Needs Attention + Next Up + Asset Details),
        Maintenance/Missions/Documents each get the FULL list, not a
        truncated preview. Still no Parts/History tab — no real data
        model behind either. Every card shows only real data."""
        asset = self.context.maintenance.get_asset(asset_id)

        page = QWidget()
        page.setStyleSheet("background-color: #070f0d;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(150)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 16, 28, 16)
        hero_layout.setSpacing(6)

        back_button = QPushButton("← Back to Garage")
        back_button.clicked.connect(self._show_list_page)
        hero_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        if asset is None:
            hero_layout.addStretch(1)
            missing = QLabel("This asset no longer exists.")
            missing.setObjectName("NatureHeaderTagline")
            hero_layout.addWidget(missing)
            outer.addWidget(hero)
            outer.addStretch(1)
            return page

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        title = QLabel(asset.name)
        title.setObjectName("NatureHeaderTitle")
        header_row.addWidget(title)
        category_badge = QLabel(asset.category)
        category_badge.setObjectName("NatureTileCaption")
        header_row.addWidget(category_badge)
        header_row.addStretch(1)
        hero_layout.addLayout(header_row)

        make_model = " ".join(part for part in [asset.manufacturer, asset.model] if part)
        if make_model:
            subtitle = QLabel(make_model)
            subtitle.setObjectName("NatureHeaderTagline")
            hero_layout.addWidget(subtitle)
        hero_layout.addStretch(1)

        outer.addWidget(hero)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 0)
        body_layout.setSpacing(12)

        today = date.today()
        tasks = self.context.maintenance.tasks_for_asset(asset.asset_id)
        readings_by_task = {
            task.task_id: (
                self.context.maintenance.readings_for_task(task.task_id) if task.trigger_type != "calendar" else []
            )
            for task in tasks
        }
        quick_stat_tasks = [t for t in tasks if is_quick_stat_task(t)]
        actionable_tasks = [t for t in tasks if not is_quick_stat_task(t)]
        attention_tasks = [t for t in actionable_tasks if task_needs_attention(t, today, readings_by_task[t.task_id])]
        upcoming_tasks = next_up_tasks(actionable_tasks, attention_tasks)

        if quick_stat_tasks:
            stats_row = QHBoxLayout()
            stats_row.setSpacing(16)
            for task in quick_stat_tasks:
                self._build_quick_stat_tile(stats_row, task, readings_by_task[task.task_id])
            body_layout.addLayout(stats_row)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(24)
        stack = QStackedWidget()
        tab_pages = {
            "Overview": self._build_overview_tab(asset, attention_tasks, upcoming_tasks, today, readings_by_task),
            "Maintenance": self._build_maintenance_tab(actionable_tasks, attention_tasks, today, readings_by_task),
            "Missions": self._build_missions_tab(asset),
            "Documents": self._build_documents_tab(asset),
        }
        tab_buttons: dict[str, QPushButton] = {}

        def _select_tab(name: str) -> None:
            for key, button in tab_buttons.items():
                button.setProperty("active", key == name)
                button.style().unpolish(button)
                button.style().polish(button)
            stack.setCurrentWidget(tab_pages[name])

        for name, widget in tab_pages.items():
            button = QPushButton(name)
            button.setObjectName("NatureTabButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, n=name: _select_tab(n))
            tab_buttons[name] = button
            tab_row.addWidget(button)
            stack.addWidget(widget)
        tab_row.addStretch(1)
        body_layout.addLayout(tab_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(stack)
        body_layout.addWidget(scroll, stretch=1)

        outer.addWidget(body, stretch=1)
        _select_tab("Overview")
        return page

    def _build_overview_tab(
        self,
        asset: MaintenanceAsset,
        attention_tasks: list[MaintenanceTask],
        upcoming_tasks: list[MaintenanceTask],
        today: date,
        readings_by_task: dict[str, list[Reading]],
    ) -> QWidget:
        """Overview — a condensed summary, not the full task/mission/
        document lists (those live in their own tabs): Needs Attention,
        Next Up, and static Asset Details."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(16)

        if attention_tasks:
            attention_card = QFrame()
            attention_card.setObjectName("NatureAttentionPanel")
            attention_layout = QVBoxLayout(attention_card)
            attention_layout.setContentsMargins(18, 16, 18, 16)
            attention_layout.setSpacing(6)
            attention_title = QLabel("⚠  Needs Attention")
            attention_title.setObjectName("NatureAttentionTitle")
            attention_layout.addWidget(attention_title)
            for task in attention_tasks:
                line = QLabel(f"•  {format_task_status_line(task, today, readings_by_task[task.task_id])}")
                line.setObjectName("NatureAttentionLine")
                line.setWordWrap(True)
                attention_layout.addWidget(line)
            layout.addWidget(attention_card)

        next_up_card = QFrame()
        next_up_card.setObjectName("NatureAssetCard")
        next_up_layout = QVBoxLayout(next_up_card)
        next_up_layout.setContentsMargins(18, 16, 18, 16)
        next_up_layout.setSpacing(6)
        next_up_title = QLabel("Next Up")
        next_up_title.setObjectName("NatureSectionTitle")
        next_up_layout.addWidget(next_up_title)
        if not upcoming_tasks:
            empty = QLabel("Nothing else upcoming.")
            empty.setObjectName("NatureTileCaption")
            next_up_layout.addWidget(empty)
        for task in upcoming_tasks:
            line = QLabel(f"•  {format_task_status_line(task, today, readings_by_task[task.task_id])}")
            line.setObjectName("NatureAssetLine")
            line.setWordWrap(True)
            next_up_layout.addWidget(line)
        layout.addWidget(next_up_card)

        details = [
            ("Make", asset.manufacturer),
            ("Model", asset.model),
            ("Serial #", asset.serial_number),
            ("Purchase Date", asset.purchase_date),
        ]
        details = [(label, value) for label, value in details if value]
        if details:
            details_card = QFrame()
            details_card.setObjectName("NatureAssetCard")
            details_layout = QVBoxLayout(details_card)
            details_layout.setContentsMargins(18, 16, 18, 16)
            details_layout.setSpacing(6)
            details_title = QLabel("Asset Details")
            details_title.setObjectName("NatureSectionTitle")
            details_layout.addWidget(details_title)
            for label, value in details:
                row = QLabel(f"{label}: {value}")
                row.setObjectName("NatureAssetLine")
                details_layout.addWidget(row)
            layout.addWidget(details_card)

        layout.addStretch(1)
        return page

    def _build_maintenance_tab(
        self,
        actionable_tasks: list[MaintenanceTask],
        attention_tasks: list[MaintenanceTask],
        today: date,
        readings_by_task: dict[str, list[Reading]],
    ) -> QWidget:
        """Maintenance — every real task, not the Overview tab's
        Needs-Attention-only subset."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(16)

        tasks_card = QFrame()
        tasks_card.setObjectName("NatureAssetCard")
        tasks_layout = QVBoxLayout(tasks_card)
        tasks_layout.setContentsMargins(18, 16, 18, 16)
        tasks_layout.setSpacing(6)
        tasks_title = QLabel("Current Tasks")
        tasks_title.setObjectName("NatureSectionTitle")
        tasks_layout.addWidget(tasks_title)
        if not actionable_tasks:
            empty = QLabel("No maintenance tasks tracked for this asset yet.")
            empty.setObjectName("NatureTileCaption")
            tasks_layout.addWidget(empty)
        attention_ids = {t.task_id for t in attention_tasks}
        for task in actionable_tasks:
            line = QLabel(f"•  {format_task_status_line(task, today, readings_by_task[task.task_id])}")
            line.setObjectName("NatureAssetLine")
            if task.task_id in attention_ids:
                line.setProperty("tone", "danger")
            line.setWordWrap(True)
            tasks_layout.addWidget(line)
        layout.addWidget(tasks_card)
        layout.addStretch(1)
        return page

    def _build_missions_tab(self, asset: MaintenanceAsset) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(16)

        missions_card = QFrame()
        missions_card.setObjectName("NatureAssetCard")
        missions_layout = QVBoxLayout(missions_card)
        missions_layout.setContentsMargins(18, 16, 18, 16)
        missions_layout.addWidget(build_asset_missions_panel(self.context, asset.asset_id))
        layout.addWidget(missions_card)
        layout.addStretch(1)
        return page

    def _build_documents_tab(self, asset: MaintenanceAsset) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(16)

        documents_card = QFrame()
        documents_card.setObjectName("NatureAssetCard")
        documents_layout = QVBoxLayout(documents_card)
        documents_layout.setContentsMargins(18, 16, 18, 16)
        documents_layout.setSpacing(6)
        documents_title = QLabel("Documents")
        documents_title.setObjectName("NatureSectionTitle")
        documents_layout.addWidget(documents_title)
        if not asset.documents:
            empty = QLabel("No documents attached yet.")
            empty.setObjectName("NatureTileCaption")
            documents_layout.addWidget(empty)
        else:
            for filename in asset.documents:
                row = QLabel(f"📄  {filename}")
                row.setObjectName("NatureAssetLine")
                documents_layout.addWidget(row)
        layout.addWidget(documents_card)
        layout.addStretch(1)
        return page

    def _build_quick_stat_tile(self, row_layout: QHBoxLayout, task: MaintenanceTask, readings: list[Reading]) -> None:
        tile = QFrame()
        tile.setObjectName("NatureGlanceTile")
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(14, 12, 14, 12)
        tile_layout.setSpacing(2)
        value_label = QLabel(format_quick_stat_value(readings, task.meter_unit))
        value_label.setObjectName("NatureTileValue")
        tile_layout.addWidget(value_label)
        caption_label = QLabel(task.title)
        caption_label.setObjectName("NatureTileCaption")
        tile_layout.addWidget(caption_label)
        row_layout.addWidget(tile, stretch=1)

    def _build_list_page(self) -> QWidget:
        """Nature re-skin pilot (2026-09-14) — a fixed-height photo
        hero (icon badge + title + tagline over the background photo/
        placeholder gradient) followed by a solid dark body, rather
        than wrapping the whole scrollable page in the photo frame:
        the reference mockup itself only really shows photo behind the
        header — by the time you reach the card stack it's already
        effectively solid dark, so this is a closer match, not just a
        simpler implementation."""
        page = QWidget()
        page.setStyleSheet("background-color: #070f0d;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(150)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 20, 28, 16)
        hero_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        icon_badge = QLabel(self.icon)
        icon_badge.setObjectName("NatureIconBadge")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(icon_badge)
        title = QLabel(self.display_name)
        title.setObjectName("NatureHeaderTitle")
        header_row.addWidget(title)
        header_row.addStretch(1)
        hero_layout.addLayout(header_row)

        tagline = QLabel(self.description)
        tagline.setObjectName("NatureHeaderTagline")
        hero_layout.addWidget(tagline)
        hero_layout.addStretch(1)

        manage_button = QPushButton("Manage in Maintenance →")
        manage_button.clicked.connect(self._on_manage_in_maintenance)
        hero_layout.addWidget(manage_button, alignment=Qt.AlignmentFlag.AlignLeft)

        outer.addWidget(hero)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 24)
        body_layout.setSpacing(16)

        glance_row = QHBoxLayout()
        glance_row.setSpacing(16)
        self._tracked_value_label = self._build_glance_tile(glance_row, "Tracked", "\U0001F331")
        self._attention_value_label = self._build_glance_tile(glance_row, "Needs Attention", "⚠", danger=True)
        self._next_up_value_label = self._build_glance_tile(glance_row, "Next Up", "\U0001F4C5")
        body_layout.addLayout(glance_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._list_layout = QVBoxLayout(content)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(16)
        scroll.setWidget(content)
        body_layout.addWidget(scroll, stretch=1)

        outer.addWidget(body, stretch=1)

        self._refresh()
        return page

    def _on_manage_in_maintenance(self) -> None:
        self.context.events.publish("assistant.open_module_requested", module_id="maintenance")

    def _build_glance_tile(
        self, row_layout: QHBoxLayout, caption: str, icon: str, danger: bool = False
    ) -> QLabel:
        """Nature re-skin pilot (2026-09-14) — a rounded translucent
        #NatureGlanceTile with an icon badge, replacing the teal HUD's
        #MonitorTile for this one pilot page."""
        tile = QFrame()
        tile.setObjectName("NatureGlanceTile")
        if danger:
            tile.setProperty("tone", "danger")
        tile_layout = QHBoxLayout(tile)
        tile_layout.setContentsMargins(14, 12, 14, 12)
        tile_layout.setSpacing(10)

        icon_badge = QLabel(icon)
        icon_badge.setObjectName("NatureIconBadge")
        if danger:
            icon_badge.setProperty("tone", "danger")
        icon_badge.setFixedSize(36, 36)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile_layout.addWidget(icon_badge)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        value_label = QLabel("—")
        value_label.setObjectName("NatureTileValue")
        if danger:
            value_label.setProperty("tone", "danger")
        text_col.addWidget(value_label)
        caption_label = QLabel(caption)
        caption_label.setObjectName("NatureTileCaption")
        text_col.addWidget(caption_label)
        tile_layout.addLayout(text_col)

        row_layout.addWidget(tile, stretch=1)
        return value_label

    def _refresh(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        today = date.today()
        assets = [a for a in self.context.maintenance.all_assets() if is_garage_asset(a)]

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
                "Vehicles & Equipment",
                [],
                empty_text="No vehicles or motorized equipment tracked yet — add one in Maintenance.",
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
        """Nature re-skin pilot (2026-09-14) — a given asset (asset_id
        set) is a rounded #NatureAssetCard (whole card opens its detail
        page); a cross-asset callout like "Needs Attention" (asset_id
        is None) is a #NatureAttentionPanel — coral-bordered, matching
        the reference mockup's own "Needs Attention" box exactly.
        Individual overdue lines get the danger text tone; other lines
        stay neutral, same as the mockup's own mixed-color line list."""
        if asset_id is not None:
            card = QPushButton()
            card.setObjectName("NatureAssetCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setToolTip(f"Open {title}")
            card.setMinimumHeight(90)
            card.clicked.connect(lambda checked=False, aid=asset_id: self._show_detail_page(aid))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(4)

            name, _, category = title.partition("  [")
            title_label = QLabel(f"{name}  ›")
            title_label.setObjectName("NatureAssetTitle")
            card_layout.addWidget(title_label)
            if category:
                category_label = QLabel(category.rstrip("]"))
                category_label.setObjectName("NatureAssetCategory")
                card_layout.addWidget(category_label)
        else:
            card = QFrame()
            card.setObjectName("NatureAttentionPanel")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 16, 18, 16)
            card_layout.setSpacing(6)

            eyebrow = QLabel(f"⚠  {title}")
            eyebrow.setObjectName("NatureAttentionTitle")
            card_layout.addWidget(eyebrow)

        if not lines:
            empty_label = QLabel(empty_text)
            empty_label.setObjectName("NatureTileCaption")
            empty_label.setWordWrap(True)
            card_layout.addWidget(empty_label)
        for line in lines:
            item_label = QLabel(f"•  {line}")
            item_label.setObjectName("NatureAttentionLine" if asset_id is None else "NatureAssetLine")
            if asset_id is not None and "overdue" in line:
                item_label.setProperty("tone", "danger")
            item_label.setWordWrap(True)
            card_layout.addWidget(item_label)

        self._list_layout.addWidget(card)
