"""
core.dashboard_widgets
=========================

The Home dashboard's widget registry — 2026-07-15, "framework first"
per the widget/dashboard-customization conversation (`docs/VISION.md`'s
companion-philosophy update names weather/trading-bot/music/current-
project widgets; this is the generic mechanism underneath all of them,
built before any specific one beyond what already existed).

Same shape as `core/module_manager.py`'s enable/disable/rescan pattern
(`is_enabled()`/`set_enabled()`, a `disabled_ids` config list, an event-
bus publish on change so a live view can rebuild without a restart) —
reused deliberately rather than inventing a second convention for what
is, structurally, the same problem: "the user can enable/disable/
reorder a set of registered things."

Pure data + config-backed state here — the actual widget QWidget
construction stays in `gui/home_dashboard.py` (gui/ owns rendering,
core/ owns the registry/truth), same split as ModuleManager (core,
discovers module_ids) vs. MainWindow (gui, builds the actual grid).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class WidgetDescriptor:
    widget_id: str
    display_name: str
    icon: str


class DashboardWidgetRegistry:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._widgets: dict[str, WidgetDescriptor] = {}

    def register(self, descriptor: WidgetDescriptor) -> None:
        self._widgets[descriptor.widget_id] = descriptor
        log.info("Registered dashboard widget: %s", descriptor.widget_id)

    def all_widgets(self) -> list[WidgetDescriptor]:
        """Every registered widget, in registration order — what the
        Customize dialog lists (including currently-disabled ones)."""
        return list(self._widgets.values())

    # ------------------------------------------------------------------
    # Enable / disable — same convention as ModuleManager
    # ------------------------------------------------------------------

    def is_enabled(self, widget_id: str) -> bool:
        if widget_id not in self._widgets:
            return False
        disabled_ids = self.context.config.get("dashboard.disabled_widgets", [])
        return widget_id not in disabled_ids

    def set_enabled(self, widget_id: str, enabled: bool) -> None:
        disabled_ids = list(self.context.config.get("dashboard.disabled_widgets", []))
        if enabled:
            if widget_id in disabled_ids:
                disabled_ids.remove(widget_id)
        else:
            if widget_id not in disabled_ids:
                disabled_ids.append(widget_id)

        self.context.config.set("dashboard.disabled_widgets", disabled_ids)
        self.context.config.save()
        self.context.events.publish("dashboard.widgets_changed")
        log.info("Dashboard widget '%s' %s", widget_id, "enabled" if enabled else "disabled")

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    def set_order(self, widget_ids: list[str]) -> None:
        self.context.config.set("dashboard.widget_order", widget_ids)
        self.context.config.save()
        self.context.events.publish("dashboard.widgets_changed")

    def enabled_widgets_in_order(self) -> list[WidgetDescriptor]:
        """What `gui/home_dashboard.py` actually renders — enabled
        widgets only, in the user's chosen order. A widget registered
        after the user last reordered (or never explicitly ordered at
        all) falls back to registration order, appended at the end."""
        stored_order = self.context.config.get("dashboard.widget_order", [])
        ordered_ids = [wid for wid in stored_order if wid in self._widgets]
        remaining_ids = [wid for wid in self._widgets if wid not in ordered_ids]
        all_ids = ordered_ids + remaining_ids
        return [self._widgets[wid] for wid in all_ids if self.is_enabled(wid)]
