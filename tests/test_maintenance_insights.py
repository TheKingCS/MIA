"""
tests.test_maintenance_insights
==================================

Unit tests for core.maintenance_insights — isolates _DATA_DIR for
maintenance/data_logger/insight files into a tmp_path scratch area,
same monkeypatch pattern as test_maintenance_manager.py's own
isolated_paths, plus insight_manager's files added.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

import core.data_logger_manager as data_logger_manager_module
import core.insight_manager as insight_manager_module
import core.maintenance_manager as maintenance_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.insight_manager import InsightManager
from core.maintenance_insights import format_maintenance_insights_message, scan_maintenance_insights
from core.maintenance_manager import MaintenanceManager

TODAY = date(2026, 9, 11)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(maintenance_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(maintenance_manager_module, "_MAINTENANCE_FILE", data_dir / "maintenance.json")
    monkeypatch.setattr(maintenance_manager_module, "_DOCUMENT_ROOT", tmp_path / "maintenance_documents")
    monkeypatch.setattr(data_logger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(data_logger_manager_module, "_READINGS_FILE", data_dir / "data_logger_readings.json")
    monkeypatch.setattr(insight_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(insight_manager_module, "_INSIGHTS_FILE", data_dir / "insights.json")
    monkeypatch.setattr(insight_manager_module, "_RECOMMENDATIONS_FILE", data_dir / "recommendations.json")
    return data_dir


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.data_logger = DataLoggerManager(context)
    context.maintenance = MaintenanceManager(context)
    context.insights = InsightManager(context)
    return context


def _asset(context):
    return context.maintenance.add_asset(name="Truck")


# ------------------------------------------------------------------
# Calendar tasks
# ------------------------------------------------------------------

def test_scan_flags_an_overdue_calendar_task(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    last_completed = (TODAY - timedelta(days=40)).isoformat()
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Oil change", interval_days=30, last_completed=last_completed,
    )

    new_insights = scan_maintenance_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "overdue"
    assert new_insights[0].source_id == task.task_id
    assert new_insights[0].message == "'Oil change' is overdue by 10 days."
    assert len(context.insights.recommendations_for_insight(new_insights[0].insight_id)) == 1


def test_scan_flags_a_due_soon_calendar_task(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    last_completed = (TODAY - timedelta(days=28)).isoformat()
    context.maintenance.add_task(
        asset_id=asset.asset_id, title="Tire rotation", interval_days=30, last_completed=last_completed,
    )

    new_insights = scan_maintenance_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "due_soon"
    assert new_insights[0].message == "'Tire rotation' is due in 2 days."


def test_scan_does_not_flag_a_calendar_task_far_from_due(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    context.maintenance.add_task(
        asset_id=asset.asset_id, title="Annual inspection", interval_days=365,
        last_completed=TODAY.isoformat(),
    )

    assert scan_maintenance_insights(context, TODAY) == []


def test_scan_does_not_flag_a_never_completed_one_time_task(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    context.maintenance.add_task(asset_id=asset.asset_id, title="Someday project")

    assert scan_maintenance_insights(context, TODAY) == []


# ------------------------------------------------------------------
# Meter tasks
# ------------------------------------------------------------------

def test_scan_flags_a_due_meter_task(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Oil change", trigger_type="mileage", meter_interval=1000,
    )
    context.maintenance.mark_complete(task.task_id, meter_value=0)
    context.maintenance.log_reading(task.task_id, value=1200)

    new_insights = scan_maintenance_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "due"
    assert new_insights[0].message == "'Oil change' is due now."


def test_scan_flags_a_due_soon_meter_task_via_projection(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Filter change", trigger_type="runtime", meter_interval=100,
    )
    context.maintenance.mark_complete(task.task_id, meter_value=0)
    two_days_ago = (TODAY - timedelta(days=2)).isoformat() + "T00:00:00"
    now_ts = TODAY.isoformat() + "T00:00:00"
    context.data_logger.add_reading(series_id=task.series_id, value=90, timestamp=two_days_ago)
    context.data_logger.add_reading(series_id=task.series_id, value=95, timestamp=now_ts)

    new_insights = scan_maintenance_insights(context, TODAY)

    # is_meter_task_due is False (95 < 100) -- this must come from the
    # forward-looking projection, not the "already due" path.
    assert len(new_insights) == 1
    assert new_insights[0].kind == "due_soon"
    assert "projected to be due in" in new_insights[0].message


def test_scan_does_not_flag_a_meter_task_with_no_readings(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    context.maintenance.add_task(
        asset_id=asset.asset_id, title="Oil change", trigger_type="mileage", meter_interval=1000,
    )

    assert scan_maintenance_insights(context, TODAY) == []


# ------------------------------------------------------------------
# Sensor tasks
# ------------------------------------------------------------------

def test_scan_flags_a_due_sensor_task(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Water filter", trigger_type="sensor",
        threshold_value=20.0, threshold_direction="below",
    )
    context.maintenance.log_reading(task.task_id, value=15.0)

    new_insights = scan_maintenance_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "due"
    assert new_insights[0].message == "'Water filter' is reading has crossed its threshold."


def test_scan_does_not_flag_a_sensor_task_within_range(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Water filter", trigger_type="sensor",
        threshold_value=20.0, threshold_direction="below",
    )
    context.maintenance.log_reading(task.task_id, value=50.0)

    assert scan_maintenance_insights(context, TODAY) == []


# ------------------------------------------------------------------
# Idempotency / resolution — the real "never naggy" mechanism
# ------------------------------------------------------------------

def test_scan_does_not_duplicate_on_a_second_scan(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    context.maintenance.add_task(
        asset_id=asset.asset_id, title="Oil change", interval_days=30,
        last_completed=(TODAY - timedelta(days=40)).isoformat(),
    )

    first_run = scan_maintenance_insights(context, TODAY)
    second_run = scan_maintenance_insights(context, TODAY)

    assert len(first_run) == 1
    assert second_run == []
    assert len(context.insights.all_insights()) == 1


def test_scan_resolves_insight_once_the_task_is_completed(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Oil change", interval_days=30,
        last_completed=(TODAY - timedelta(days=40)).isoformat(),
    )
    new_insights = scan_maintenance_insights(context, TODAY)
    insight_id = new_insights[0].insight_id

    context.maintenance.mark_complete(task.task_id, completed_date=TODAY.isoformat())
    scan_maintenance_insights(context, TODAY)

    assert context.insights.get_insight(insight_id).status == "resolved"


def test_scan_resolves_a_stale_kind_when_escalating_from_due_soon_to_overdue(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    task = context.maintenance.add_task(
        asset_id=asset.asset_id, title="Tire rotation", interval_days=30,
        last_completed=(TODAY - timedelta(days=28)).isoformat(),
    )
    due_soon_insights = scan_maintenance_insights(context, TODAY)
    due_soon_id = due_soon_insights[0].insight_id
    assert due_soon_insights[0].kind == "due_soon"

    later = TODAY + timedelta(days=10)  # now genuinely overdue
    overdue_insights = scan_maintenance_insights(context, later)

    assert len(overdue_insights) == 1
    assert overdue_insights[0].kind == "overdue"
    assert context.insights.get_insight(due_soon_id).status == "resolved"


def test_scan_with_no_maintenance_service_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.insights = InsightManager(context)
    assert scan_maintenance_insights(context, TODAY) == []


def test_scan_with_no_insights_service_returns_empty(isolated_paths):
    context = _make_context()
    context.insights = None
    asset = _asset(context)
    context.maintenance.add_task(
        asset_id=asset.asset_id, title="Oil change", interval_days=30,
        last_completed=(TODAY - timedelta(days=40)).isoformat(),
    )
    assert scan_maintenance_insights(context, TODAY) == []


# ------------------------------------------------------------------
# format_maintenance_insights_message
# ------------------------------------------------------------------

def test_format_maintenance_insights_message_none_when_empty():
    assert format_maintenance_insights_message([]) is None


def test_format_maintenance_insights_message_joins_multiple(isolated_paths):
    context = _make_context()
    asset = _asset(context)
    context.maintenance.add_task(
        asset_id=asset.asset_id, title="Oil change", interval_days=30,
        last_completed=(TODAY - timedelta(days=40)).isoformat(),
    )
    context.maintenance.add_task(
        asset_id=asset.asset_id, title="Tire rotation", interval_days=30,
        last_completed=(TODAY - timedelta(days=28)).isoformat(),
    )

    new_insights = scan_maintenance_insights(context, TODAY)
    message = format_maintenance_insights_message(new_insights)

    assert "Oil change" in message
    assert "Tire rotation" in message
