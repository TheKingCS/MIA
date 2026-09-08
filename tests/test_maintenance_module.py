"""
tests.test_maintenance_module
================================

Unit tests for the pure logic behind the Maintenance module:
core.maintenance_manager's recurrence functions (next_due_date/
days_until_due/is_overdue, plus v2's meter_used_since_last/
is_meter_task_due/is_sensor_task_due/predicted_due_date) and
modules.maintenance.module's row formatters. No Qt event loop needed —
importing the module only defines widget classes; nothing here
instantiates one. Meter/sensor tests build a plain list[Reading]
fixture directly rather than going through DataLoggerManager, since
every function under test takes readings as an explicit parameter.
"""

from __future__ import annotations

from datetime import date

from core.data_logger_manager import Reading
from core.maintenance_manager import (
    MaintenanceAsset,
    MaintenanceTask,
    days_until_due,
    is_meter_task_due,
    is_overdue,
    is_sensor_task_due,
    meter_used_since_last,
    next_due_date,
    predicted_due_date,
)
from modules.maintenance.module import format_asset_row, format_task_row


def _task(interval_days=None, last_completed=None):
    return MaintenanceTask(
        task_id="t1", asset_id="a1", title="Oil change",
        interval_days=interval_days, last_completed=last_completed,
    )


def _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0, meter_unit="miles"):
    return MaintenanceTask(
        task_id="t2", asset_id="a1", title="Oil change", trigger_type="mileage",
        meter_unit=meter_unit, meter_interval=meter_interval,
        last_completed_meter_value=last_completed_meter_value, last_completed="2026-08-01",
    )


def _sensor_task(threshold_value=11.5, threshold_direction="below"):
    return MaintenanceTask(
        task_id="t3", asset_id="a1", title="Check battery", trigger_type="sensor",
        meter_unit="V", threshold_value=threshold_value, threshold_direction=threshold_direction,
    )


def _reading(value, timestamp, series_id="maintenance_t2"):
    return Reading(reading_id="r", series_id=series_id, value=value, unit="", note="", timestamp=timestamp)


# ------------------------------------------------------------------
# next_due_date / days_until_due / is_overdue
# ------------------------------------------------------------------

def test_next_due_date_none_for_one_time_task():
    assert next_due_date(_task(interval_days=None, last_completed="2026-08-01")) is None


def test_next_due_date_none_when_never_completed():
    assert next_due_date(_task(interval_days=30, last_completed=None)) is None


def test_next_due_date_computes_from_last_completed_plus_interval():
    task = _task(interval_days=30, last_completed="2026-08-10")
    assert next_due_date(task) == date(2026, 9, 9)


def test_days_until_due_positive_when_not_yet_due():
    task = _task(interval_days=30, last_completed="2026-08-10")  # due 2026-09-09
    assert days_until_due(task, date(2026, 9, 7)) == 2


def test_days_until_due_negative_when_overdue():
    task = _task(interval_days=30, last_completed="2026-07-01")  # due 2026-07-31
    assert days_until_due(task, date(2026, 9, 7)) == -38


def test_days_until_due_zero_on_the_due_date_itself():
    task = _task(interval_days=30, last_completed="2026-08-08")  # due 2026-09-07
    assert days_until_due(task, date(2026, 9, 7)) == 0


def test_days_until_due_none_for_one_time_or_never_completed():
    assert days_until_due(_task(interval_days=None), date(2026, 9, 7)) is None
    assert days_until_due(_task(interval_days=90, last_completed=None), date(2026, 9, 7)) is None


def test_is_overdue_true_past_due_date():
    task = _task(interval_days=30, last_completed="2026-07-01")
    assert is_overdue(task, date(2026, 9, 7)) is True


def test_is_overdue_false_on_the_due_date_itself():
    # Due today is not yet overdue — overdue means the due date has passed.
    task = _task(interval_days=30, last_completed="2026-08-08")
    assert is_overdue(task, date(2026, 9, 7)) is False


def test_is_overdue_false_for_one_time_or_never_completed():
    assert is_overdue(_task(interval_days=None), date(2026, 9, 7)) is False
    assert is_overdue(_task(interval_days=90, last_completed=None), date(2026, 9, 7)) is False


# ------------------------------------------------------------------
# format_asset_row / format_task_row
# ------------------------------------------------------------------

def test_format_asset_row():
    asset = MaintenanceAsset(asset_id="a1", name="Lawn Mower", category="Power Equipment")
    assert format_asset_row(asset) == "Lawn Mower   [Power Equipment]"


def test_format_task_row_overdue():
    asset = MaintenanceAsset(asset_id="a1", name="2019 Ford F-150", category="Vehicle")
    task = _task(interval_days=30, last_completed="2026-07-01")  # 38 days overdue on 2026-09-07
    assert format_task_row(task, asset, date(2026, 9, 7)) == "[OVERDUE 38d]  Oil change   (2019 Ford F-150)"


def test_format_task_row_due_today():
    asset = MaintenanceAsset(asset_id="a1", name="2019 Ford F-150", category="Vehicle")
    task = _task(interval_days=30, last_completed="2026-08-08")
    assert format_task_row(task, asset, date(2026, 9, 7)) == "[DUE TODAY]  Oil change   (2019 Ford F-150)"


def test_format_task_row_due_in_future():
    asset = MaintenanceAsset(asset_id="a1", name="2019 Ford F-150", category="Vehicle")
    task = _task(interval_days=30, last_completed="2026-08-10")
    assert format_task_row(task, asset, date(2026, 9, 7)) == "[DUE IN 2d]  Oil change   (2019 Ford F-150)"


def test_format_task_row_never_done_recurring():
    asset = MaintenanceAsset(asset_id="a1", name="2019 Ford F-150", category="Vehicle")
    task = _task(interval_days=30, last_completed=None)
    assert format_task_row(task, asset, date(2026, 9, 7)) == "[NEVER DONE]  Oil change   (2019 Ford F-150)"


def test_format_task_row_one_time_not_yet_done():
    asset = MaintenanceAsset(asset_id="a1", name="2019 Ford F-150", category="Vehicle")
    task = _task(interval_days=None, last_completed=None)
    assert format_task_row(task, asset, date(2026, 9, 7)) == "[ONE-TIME]  Oil change   (2019 Ford F-150)"


def test_format_task_row_one_time_done():
    asset = MaintenanceAsset(asset_id="a1", name="2019 Ford F-150", category="Vehicle")
    task = _task(interval_days=None, last_completed="2026-08-01")
    assert format_task_row(task, asset, date(2026, 9, 7)) == "[DONE]  Oil change   (2019 Ford F-150)"


def test_format_task_row_unknown_asset():
    task = _task(interval_days=None, last_completed=None)
    assert format_task_row(task, None, date(2026, 9, 7)) == "[ONE-TIME]  Oil change   (Unknown asset)"


# ------------------------------------------------------------------
# Meter mechanism (runtime/mileage/cycles/condition)
# ------------------------------------------------------------------

def test_meter_used_since_last_none_when_never_completed():
    task = _meter_task(last_completed_meter_value=None)
    assert meter_used_since_last(task, [_reading(41000, "2026-09-01T00:00:00")]) is None


def test_meter_used_since_last_none_when_no_readings():
    assert meter_used_since_last(_meter_task(), []) is None


def test_meter_used_since_last_computes_delta_from_baseline():
    task = _meter_task(last_completed_meter_value=40000.0)
    readings = [_reading(41000, "2026-09-01T00:00:00"), _reading(42500, "2026-09-05T00:00:00")]
    assert meter_used_since_last(task, readings) == 2500


def test_is_meter_task_due_false_below_interval():
    task = _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0)
    assert is_meter_task_due(task, [_reading(42500, "2026-09-05T00:00:00")]) is False


def test_is_meter_task_due_true_at_or_past_interval():
    task = _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0)
    assert is_meter_task_due(task, [_reading(45500, "2026-09-05T00:00:00")]) is True


def test_is_meter_task_due_false_with_no_readings():
    assert is_meter_task_due(_meter_task(), []) is False


# ------------------------------------------------------------------
# Threshold mechanism (sensor)
# ------------------------------------------------------------------

def test_is_sensor_task_due_below_direction():
    task = _sensor_task(threshold_value=11.5, threshold_direction="below")
    assert is_sensor_task_due(task, [_reading(11.2, "2026-09-05T00:00:00")]) is True
    assert is_sensor_task_due(task, [_reading(12.6, "2026-09-05T00:00:00")]) is False


def test_is_sensor_task_due_above_direction():
    task = _sensor_task(threshold_value=100.0, threshold_direction="above")
    assert is_sensor_task_due(task, [_reading(104.0, "2026-09-05T00:00:00")]) is True
    assert is_sensor_task_due(task, [_reading(90.0, "2026-09-05T00:00:00")]) is False


def test_is_sensor_task_due_false_with_no_readings():
    assert is_sensor_task_due(_sensor_task(), []) is False


# ------------------------------------------------------------------
# Prediction — never a fabricated guess
# ------------------------------------------------------------------

def test_predicted_due_date_none_for_calendar_task():
    assert predicted_due_date(_task(interval_days=30, last_completed="2026-08-01"), [], date(2026, 9, 7)) is None


def test_predicted_due_date_none_with_fewer_than_two_readings():
    task = _meter_task()
    assert predicted_due_date(task, [], date(2026, 9, 7)) is None
    assert predicted_due_date(task, [_reading(41000, "2026-09-01T00:00:00")], date(2026, 9, 7)) is None


def test_predicted_due_date_none_when_already_due():
    task = _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0)
    readings = [_reading(44000, "2026-08-01T00:00:00"), _reading(45500, "2026-09-01T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 9, 7)) is None


def test_predicted_due_date_none_when_usage_rate_is_zero_or_negative():
    task = _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0)
    readings = [_reading(41000, "2026-08-01T00:00:00"), _reading(41000, "2026-09-01T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 9, 7)) is None


def test_predicted_due_date_projects_forward_from_real_usage_rate():
    # 1000 units used over 10 days = 100/day. Baseline 40000, interval
    # 5000, latest reading 41000 -> 4000 units remaining -> 40 days out.
    task = _meter_task(meter_interval=5000.0, last_completed_meter_value=40000.0)
    readings = [_reading(40000, "2026-08-22T00:00:00"), _reading(41000, "2026-09-01T00:00:00")]
    result = predicted_due_date(task, readings, date(2026, 9, 7))
    assert result is not None
    estimated_date, caveat = result
    assert estimated_date == date(2026, 10, 17)  # today + 40 days (4000 units remaining / 100 per day)
    assert "at current usage" in caveat
    assert "miles/week" in caveat
