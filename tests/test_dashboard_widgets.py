"""
tests.test_dashboard_widgets
===============================

Unit tests for core.dashboard_widgets — same shape as
tests/test_module_manager.py's enable/disable coverage, since
DashboardWidgetRegistry deliberately mirrors ModuleManager's convention.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.dashboard_widgets import DashboardWidgetRegistry, WidgetDescriptor
from core.event_bus import EventBus


class _FakeConfig:
    """Minimal stand-in for ConfigManager — `.get(key, default)` plus `.set()`/`.save()`."""

    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides
        self.saved = False

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)

    def set(self, key: str, value) -> None:
        self._overrides[key] = value

    def save(self) -> None:
        self.saved = True


def _make_registry(overrides: dict | None = None) -> tuple[DashboardWidgetRegistry, EventBus]:
    events = EventBus()
    context = AppContext(config=_FakeConfig(overrides or {}), events=events)
    registry = DashboardWidgetRegistry(context)
    registry.register(WidgetDescriptor("power", "Power", "\U0001F50B"))
    registry.register(WidgetDescriptor("mission", "Mission", "\U0001F3C6"))
    registry.register(WidgetDescriptor("volume", "Volume", "\U0001F50A"))
    return registry, events


def test_all_widgets_returns_every_registered_widget():
    registry, _ = _make_registry()
    ids = {w.widget_id for w in registry.all_widgets()}
    assert ids == {"power", "mission", "volume"}


def test_is_enabled_defaults_true_for_registered_widget():
    registry, _ = _make_registry()
    assert registry.is_enabled("power") is True


def test_is_enabled_false_for_unregistered_widget_id():
    registry, _ = _make_registry()
    assert registry.is_enabled("nonexistent") is False


def test_set_enabled_false_then_true_round_trips():
    registry, _ = _make_registry()
    registry.set_enabled("mission", False)
    assert registry.is_enabled("mission") is False
    registry.set_enabled("mission", True)
    assert registry.is_enabled("mission") is True


def test_set_enabled_persists_via_config_save():
    registry, _ = _make_registry()
    registry.set_enabled("power", False)
    assert registry.context.config.saved is True


def test_set_enabled_publishes_widgets_changed_event():
    registry, events = _make_registry()
    received = []
    events.subscribe("dashboard.widgets_changed", lambda **kwargs: received.append(kwargs))
    registry.set_enabled("power", False)
    assert len(received) == 1


def test_enabled_widgets_in_order_excludes_disabled():
    registry, _ = _make_registry()
    registry.set_enabled("mission", False)
    ids = [w.widget_id for w in registry.enabled_widgets_in_order()]
    assert "mission" not in ids
    assert set(ids) == {"power", "volume"}


def test_enabled_widgets_in_order_respects_stored_order():
    registry, _ = _make_registry({"dashboard.widget_order": ["volume", "power", "mission"]})
    ids = [w.widget_id for w in registry.enabled_widgets_in_order()]
    assert ids == ["volume", "power", "mission"]


def test_enabled_widgets_in_order_appends_unordered_widgets_at_end():
    registry, _ = _make_registry({"dashboard.widget_order": ["volume"]})
    ids = [w.widget_id for w in registry.enabled_widgets_in_order()]
    assert ids[0] == "volume"
    assert set(ids[1:]) == {"power", "mission"}


def test_set_order_persists_and_publishes():
    registry, events = _make_registry()
    received = []
    events.subscribe("dashboard.widgets_changed", lambda **kwargs: received.append(kwargs))
    registry.set_order(["mission", "power", "volume"])
    assert registry.context.config.get("dashboard.widget_order") == ["mission", "power", "volume"]
    assert len(received) == 1
