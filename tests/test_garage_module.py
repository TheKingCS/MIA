"""
tests.test_garage_module
===========================

Unit tests for modules.garage.module's pure functions, same style as
tests/test_dashboard_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from datetime import date

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import Reading
from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceAsset, MaintenanceTask
from modules.garage.module import (
    GarageModule,
    format_attention_line,
    format_glance_next_up,
    format_quick_stat_value,
    format_task_status_line,
    is_garage_asset,
    is_quick_stat_task,
    task_needs_attention,
)


def _vehicle(category="Vehicle"):
    return MaintenanceAsset(asset_id="a1", name="2019 Ford F-150", category=category)


def _calendar_task(interval_days=30, last_completed=None):
    return MaintenanceTask(
        task_id="t1", asset_id="a1", title="Oil change",
        trigger_type="calendar", interval_days=interval_days, last_completed=last_completed,
    )


def _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0):
    return MaintenanceTask(
        task_id="t2", asset_id="a1", title="Tire rotation", trigger_type="mileage",
        meter_unit="miles", meter_interval=meter_interval, last_completed_meter_value=last_completed_meter_value,
        last_completed="2026-08-01",
    )


def _sensor_task(threshold_value=11.5, threshold_direction="below"):
    return MaintenanceTask(
        task_id="t3", asset_id="a1", title="Check battery", trigger_type="sensor",
        meter_unit="V", threshold_value=threshold_value, threshold_direction=threshold_direction,
    )


def _reading(value, task_id="t2"):
    return Reading(reading_id="r", series_id=f"maintenance_{task_id}", value=value, unit="", note="", timestamp="2026-09-01T00:00:00")


# ------------------------------------------------------------------
# is_garage_asset
# ------------------------------------------------------------------

def test_is_garage_asset_true_for_vehicle_and_power_equipment():
    assert is_garage_asset(_vehicle("Vehicle")) is True
    assert is_garage_asset(_vehicle("Power Equipment")) is True


def test_is_garage_asset_false_for_other_categories():
    assert is_garage_asset(_vehicle("Appliance")) is False
    assert is_garage_asset(_vehicle("Property")) is False
    assert is_garage_asset(_vehicle("Tool")) is False


# ------------------------------------------------------------------
# task_needs_attention
# ------------------------------------------------------------------

def test_task_needs_attention_calendar_overdue():
    task = _calendar_task(interval_days=30, last_completed="2026-07-01")  # due 2026-07-31
    assert task_needs_attention(task, date(2026, 9, 7)) is True


def test_task_needs_attention_calendar_due_today_counts():
    task = _calendar_task(interval_days=30, last_completed="2026-08-08")  # due 2026-09-07
    assert task_needs_attention(task, date(2026, 9, 7)) is True


def test_task_needs_attention_calendar_not_yet_due():
    task = _calendar_task(interval_days=30, last_completed="2026-09-01")
    assert task_needs_attention(task, date(2026, 9, 7)) is False


def test_task_needs_attention_calendar_never_completed_is_false():
    task = _calendar_task(interval_days=30, last_completed=None)
    assert task_needs_attention(task, date(2026, 9, 7)) is False


def test_task_needs_attention_meter_task():
    task = _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0)
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(46000)]) is True
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(42000)]) is False


def test_task_needs_attention_sensor_task():
    task = _sensor_task(threshold_value=11.5, threshold_direction="below")
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(11.0)]) is True
    assert task_needs_attention(task, date(2026, 9, 7), [_reading(12.6)]) is False


# ------------------------------------------------------------------
# format_task_status_line / format_attention_line
# ------------------------------------------------------------------

def test_format_task_status_line_calendar_overdue():
    task = _calendar_task(interval_days=30, last_completed="2026-07-01")
    assert format_task_status_line(task, date(2026, 9, 7)) == "Oil change — overdue 38d"


def test_format_task_status_line_meter_in_progress():
    task = _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0)
    assert format_task_status_line(task, date(2026, 9, 7), [_reading(42500)]) == "Tire rotation — 2500/5000 miles"


def test_format_task_status_line_meter_no_readings():
    task = _meter_task()
    assert format_task_status_line(task, date(2026, 9, 7), []) == "Tire rotation — no readings logged"


def test_format_task_status_line_sensor_ok():
    task = _sensor_task()
    assert format_task_status_line(task, date(2026, 9, 7), [_reading(12.6)]) == "Check battery — ok — 12.6V"


def test_format_attention_line_includes_asset_name():
    task = _calendar_task(interval_days=30, last_completed="2026-07-01")
    asset = _vehicle()
    assert format_attention_line(task, asset, date(2026, 9, 7)) == "Oil change — overdue 38d   (2019 Ford F-150)"


def test_format_attention_line_unknown_asset():
    task = _calendar_task(interval_days=30, last_completed="2026-07-01")
    assert format_attention_line(task, None, date(2026, 9, 7)) == "Oil change — overdue 38d   (Unknown asset)"


# ------------------------------------------------------------------
# format_glance_next_up
# ------------------------------------------------------------------

def test_format_glance_next_up_none_needing_attention():
    assert format_glance_next_up(0, None) == "All caught up"


def test_format_glance_next_up_single_item_names_it():
    task = _calendar_task()
    assert format_glance_next_up(1, task) == "Oil change"


def test_format_glance_next_up_multiple_items_shows_count():
    assert format_glance_next_up(3, _calendar_task()) == "3 items"


# ------------------------------------------------------------------
# is_quick_stat_task / format_quick_stat_value (Nature re-skin's
# detail page, 2026-09-14)
# ------------------------------------------------------------------

def test_is_quick_stat_task_true_for_meter_task_with_no_interval():
    task = MaintenanceTask(
        task_id="t4", asset_id="a1", title="Engine Hours", trigger_type="runtime", meter_unit="engine hours",
    )
    assert is_quick_stat_task(task) is True


def test_is_quick_stat_task_false_for_meter_task_with_an_interval():
    assert is_quick_stat_task(_meter_task()) is False


def test_is_quick_stat_task_true_for_sensor_task_with_no_threshold():
    task = MaintenanceTask(task_id="t5", asset_id="a1", title="Fuel Level", trigger_type="sensor", meter_unit="%")
    assert is_quick_stat_task(task) is True


def test_is_quick_stat_task_false_for_sensor_task_with_a_threshold():
    assert is_quick_stat_task(_sensor_task()) is False


def test_is_quick_stat_task_false_for_calendar_task():
    assert is_quick_stat_task(_calendar_task()) is False


def test_format_quick_stat_value_uses_latest_reading():
    assert format_quick_stat_value([_reading(1.0), _reading(1.5)], "engine hours") == "1.5 engine hours"


def test_format_quick_stat_value_no_readings():
    assert format_quick_stat_value([], "engine hours") == "no reading logged"


# ------------------------------------------------------------------
# Click-through navigation — no Qt widget needed, same "call the
# handler directly" approach as tests/test_field_kit_module.py's
# open_module_requested checks.
# ------------------------------------------------------------------

def test_manage_in_maintenance_publishes_open_module_event():
    context = AppContext(config=ConfigManager(), events=EventBus())
    navigated_to = []
    context.events.subscribe("assistant.open_module_requested", lambda module_id: navigated_to.append(module_id))

    module = GarageModule(context)
    module._on_manage_in_maintenance()

    assert navigated_to == ["maintenance"]
