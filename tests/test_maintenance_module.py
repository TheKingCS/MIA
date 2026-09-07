"""
tests.test_maintenance_module
================================

Unit tests for the pure logic behind the Maintenance module:
core.maintenance_manager's recurrence functions (next_due_date/
days_until_due/is_overdue) and modules.maintenance.module's row
formatters. No Qt event loop needed — importing the module only
defines widget classes; nothing here instantiates one.
"""

from __future__ import annotations

from datetime import date

from core.maintenance_manager import (
    MaintenanceAsset,
    MaintenanceTask,
    days_until_due,
    is_overdue,
    next_due_date,
)
from modules.maintenance.module import format_asset_row, format_task_row


def _task(interval_days=None, last_completed=None):
    return MaintenanceTask(
        task_id="t1", asset_id="a1", title="Oil change",
        interval_days=interval_days, last_completed=last_completed,
    )


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
