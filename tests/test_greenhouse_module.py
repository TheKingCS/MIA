"""
tests.test_greenhouse_module
===============================

Unit tests for modules.greenhouse.module's pure functions, same style
as tests/test_garage_module.py/tests/test_property_module.py (no Qt
event loop, no fixtures).
"""

from __future__ import annotations

from datetime import date

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import Reading
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceAsset, MaintenanceTask
from modules.greenhouse.module import (
    GreenhouseModule,
    format_attention_line,
    format_glance_next_up,
    format_task_status_line,
    is_greenhouse_asset,
    task_needs_attention,
)


def _plant_asset(category="Garden/Plant"):
    return MaintenanceAsset(asset_id="a1", name="Greenhouse Aquaponics", category=category)


def _calendar_task(interval_days=14, last_completed=None):
    return MaintenanceTask(
        task_id="t1", asset_id="a1", title="Prune tomatoes",
        trigger_type="calendar", interval_days=interval_days, last_completed=last_completed,
    )


def _sensor_task(threshold_value=20.0, threshold_direction="below"):
    return MaintenanceTask(
        task_id="t3", asset_id="a1", title="Fuel Level", trigger_type="sensor",
        meter_unit="%", threshold_value=threshold_value, threshold_direction=threshold_direction,
    )


def _reading(value, task_id="t3"):
    return Reading(reading_id="r", series_id=f"maintenance_{task_id}", value=value, unit="", note="", timestamp="2026-09-01T00:00:00")


# ----------------------------------------------------------------------
# is_greenhouse_asset
# ----------------------------------------------------------------------

def test_is_greenhouse_asset_true_for_garden_plant():
    assert is_greenhouse_asset(_plant_asset("Garden/Plant")) is True


def test_is_greenhouse_asset_false_for_other_categories():
    assert is_greenhouse_asset(_plant_asset("Vehicle")) is False
    assert is_greenhouse_asset(_plant_asset("Property")) is False
    assert is_greenhouse_asset(_plant_asset("Appliance")) is False


# ----------------------------------------------------------------------
# task_needs_attention
# ----------------------------------------------------------------------

def test_task_needs_attention_calendar_overdue():
    task = _calendar_task(interval_days=14, last_completed="2026-08-01")  # due 2026-08-15
    assert task_needs_attention(task, date(2026, 9, 7)) is True


def test_task_needs_attention_calendar_not_yet_due():
    task = _calendar_task(interval_days=14, last_completed="2026-09-05")
    assert task_needs_attention(task, date(2026, 9, 7)) is False


def test_task_needs_attention_sensor_task():
    task = _sensor_task(threshold_value=20.0, threshold_direction="below")
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(15.0)]) is True
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(50.0)]) is False


# ----------------------------------------------------------------------
# format_task_status_line / format_attention_line
# ----------------------------------------------------------------------

def test_format_task_status_line_calendar_overdue():
    task = _calendar_task(interval_days=14, last_completed="2026-08-01")
    assert format_task_status_line(task, date(2026, 9, 7)) == "Prune tomatoes — overdue 23d"


def test_format_task_status_line_sensor_due():
    task = _sensor_task()
    assert format_task_status_line(task, date(2026, 9, 7), [_reading(15.0)]) == "Fuel Level — due — 15%"


def test_format_task_status_line_sensor_no_readings():
    task = _sensor_task()
    assert format_task_status_line(task, date(2026, 9, 7), []) == "Fuel Level — no readings logged"


def test_format_attention_line_includes_asset_name():
    task = _calendar_task(interval_days=14, last_completed="2026-08-01")
    asset = _plant_asset()
    assert format_attention_line(task, asset, date(2026, 9, 7)) == "Prune tomatoes — overdue 23d   (Greenhouse Aquaponics)"


def test_format_attention_line_unknown_asset():
    task = _calendar_task(interval_days=14, last_completed="2026-08-01")
    assert format_attention_line(task, None, date(2026, 9, 7)) == "Prune tomatoes — overdue 23d   (Unknown asset)"


# ----------------------------------------------------------------------
# format_glance_next_up
# ----------------------------------------------------------------------

def test_format_glance_next_up_none_needing_attention():
    assert format_glance_next_up(0, None) == "All caught up"


def test_format_glance_next_up_single_item_names_it():
    task = _calendar_task()
    assert format_glance_next_up(1, task) == "Prune tomatoes"


def test_format_glance_next_up_multiple_items_shows_count():
    assert format_glance_next_up(3, _calendar_task()) == "3 items"


# ----------------------------------------------------------------------
# Click-through navigation
# ----------------------------------------------------------------------

def test_manage_in_maintenance_publishes_open_module_event():
    context = AppContext(config=ConfigManager(), events=EventBus())
    navigated_to = []
    context.events.subscribe("assistant.open_module_requested", lambda module_id: navigated_to.append(module_id))

    module = GreenhouseModule(context)
    module._on_manage_in_maintenance()

    assert navigated_to == ["maintenance"]
