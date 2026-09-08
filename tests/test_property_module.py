"""
tests.test_property_module
=============================

Unit tests for modules.property.module's pure functions — same style
and, deliberately, near-identical cases to tests/test_garage_module.py,
since the two modules share the same logic shape and differ only in
which Maintenance categories they filter to.
"""

from __future__ import annotations

from datetime import date

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import Reading
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceAsset, MaintenanceTask
from modules.property.module import (
    PropertyModule,
    format_attention_line,
    format_glance_next_up,
    format_task_status_line,
    is_property_asset,
    task_needs_attention,
)


def _house(category="Property"):
    return MaintenanceAsset(asset_id="a1", name="Main House", category=category)


def _calendar_task(interval_days=90, last_completed=None):
    return MaintenanceTask(
        task_id="t1", asset_id="a1", title="Replace HVAC filter",
        trigger_type="calendar", interval_days=interval_days, last_completed=last_completed,
    )


def _meter_task(meter_interval=200.0, last_completed_meter_value=0.0):
    return MaintenanceTask(
        task_id="t2", asset_id="a1", title="Service water heater", trigger_type="runtime",
        meter_unit="engine hours", meter_interval=meter_interval, last_completed_meter_value=last_completed_meter_value,
        last_completed="2026-08-01",
    )


def _sensor_task(threshold_value=30.0, threshold_direction="above"):
    return MaintenanceTask(
        task_id="t3", asset_id="a1", title="Check radon level", trigger_type="sensor",
        meter_unit="pCi/L", threshold_value=threshold_value, threshold_direction=threshold_direction,
    )


def _reading(value, task_id="t2"):
    return Reading(reading_id="r", series_id=f"maintenance_{task_id}", value=value, unit="", note="", timestamp="2026-09-01T00:00:00")


# ------------------------------------------------------------------
# is_property_asset
# ------------------------------------------------------------------

def test_is_property_asset_true_for_appliance_property_and_tool():
    assert is_property_asset(_house("Appliance")) is True
    assert is_property_asset(_house("Property")) is True
    assert is_property_asset(_house("Tool")) is True


def test_is_property_asset_false_for_other_categories():
    assert is_property_asset(_house("Vehicle")) is False
    assert is_property_asset(_house("Power Equipment")) is False
    assert is_property_asset(_house("Other")) is False


# ------------------------------------------------------------------
# task_needs_attention
# ------------------------------------------------------------------

def test_task_needs_attention_calendar_overdue():
    task = _calendar_task(interval_days=90, last_completed="2026-01-01")
    assert task_needs_attention(task, date(2026, 9, 7)) is True


def test_task_needs_attention_calendar_due_today_counts():
    task = _calendar_task(interval_days=90, last_completed="2026-06-09")  # due 2026-09-07
    assert task_needs_attention(task, date(2026, 9, 7)) is True


def test_task_needs_attention_calendar_not_yet_due():
    task = _calendar_task(interval_days=90, last_completed="2026-09-01")
    assert task_needs_attention(task, date(2026, 9, 7)) is False


def test_task_needs_attention_calendar_never_completed_is_false():
    task = _calendar_task(interval_days=90, last_completed=None)
    assert task_needs_attention(task, date(2026, 9, 7)) is False


def test_task_needs_attention_meter_task():
    task = _meter_task(meter_interval=200.0, last_completed_meter_value=0.0)
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(250)]) is True
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(100)]) is False


def test_task_needs_attention_sensor_task():
    task = _sensor_task(threshold_value=30.0, threshold_direction="above")
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(35.0)]) is True
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(10.0)]) is False


# ------------------------------------------------------------------
# format_task_status_line / format_attention_line
# ------------------------------------------------------------------

def test_format_task_status_line_calendar_overdue():
    task = _calendar_task(interval_days=90, last_completed="2026-01-01")
    assert format_task_status_line(task, date(2026, 9, 7)) == "Replace HVAC filter — overdue 159d"


def test_format_task_status_line_meter_in_progress():
    task = _meter_task(meter_interval=200.0, last_completed_meter_value=0.0)
    assert format_task_status_line(task, date(2026, 9, 7), [_reading(120)]) == "Service water heater — 120/200 engine hours"


def test_format_task_status_line_meter_no_readings():
    task = _meter_task()
    assert format_task_status_line(task, date(2026, 9, 7), []) == "Service water heater — no readings logged"


def test_format_task_status_line_sensor_ok():
    task = _sensor_task()
    assert format_task_status_line(task, date(2026, 9, 7), [_reading(10.0)]) == "Check radon level — ok — 10pCi/L"


def test_format_attention_line_includes_asset_name():
    task = _calendar_task(interval_days=90, last_completed="2026-01-01")
    asset = _house()
    assert format_attention_line(task, asset, date(2026, 9, 7)) == "Replace HVAC filter — overdue 159d   (Main House)"


def test_format_attention_line_unknown_asset():
    task = _calendar_task(interval_days=90, last_completed="2026-01-01")
    assert format_attention_line(task, None, date(2026, 9, 7)) == "Replace HVAC filter — overdue 159d   (Unknown asset)"


# ------------------------------------------------------------------
# format_glance_next_up
# ------------------------------------------------------------------

def test_format_glance_next_up_none_needing_attention():
    assert format_glance_next_up(0, None) == "All caught up"


def test_format_glance_next_up_single_item_names_it():
    task = _calendar_task()
    assert format_glance_next_up(1, task) == "Replace HVAC filter"


def test_format_glance_next_up_multiple_items_shows_count():
    assert format_glance_next_up(3, _calendar_task()) == "3 items"


# ------------------------------------------------------------------
# Click-through navigation
# ------------------------------------------------------------------

def test_manage_in_maintenance_publishes_open_module_event():
    context = AppContext(config=ConfigManager(), events=EventBus())
    navigated_to = []
    context.events.subscribe("assistant.open_module_requested", lambda module_id: navigated_to.append(module_id))

    module = PropertyModule(context)
    module._on_manage_in_maintenance()

    assert navigated_to == ["maintenance"]
