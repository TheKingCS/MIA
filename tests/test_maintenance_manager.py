"""
tests.test_maintenance_manager
=================================

Unit tests for core.maintenance_manager — the biggest, most complex
manager in this codebase (six trigger types, a linear-projection
estimator, document storage, Data Logger + Calendar integration) that
had zero direct test coverage before this file (only its GUI module's
formatting functions were tested).

Isolates _DATA_DIR/_MAINTENANCE_FILE/_DOCUMENT_ROOT (module constants,
not config-driven, so monkeypatched directly — same pattern
test_calendar_manager.py/test_trip_manager.py already use for their
own hardcoded path constants), plus core.data_logger_manager's and
core.calendar_manager's own _DATA_DIR/file constants for the tests
that exercise real cross-manager integration (log_reading/
schedule_task). The pure recurrence/meter/threshold/prediction
functions take readings/dates as explicit parameters (see the module's
own docstring on this convention) and are tested directly against
hand-built Reading/MaintenanceTask instances — no manager or isolation
needed for those.
"""

from __future__ import annotations

from datetime import date

import pytest

import json

import core.calendar_manager as calendar_manager_module
import core.config_manager as config_manager_module
import core.data_logger_manager as data_logger_manager_module
import core.maintenance_manager as maintenance_manager_module
import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager, Reading
from core.event_bus import EventBus
from core.maintenance_manager import (
    MaintenanceAsset,
    MaintenanceManager,
    MaintenanceTask,
    days_until_due,
    is_meter_task_due,
    is_overdue,
    is_sensor_task_due,
    meter_used_since_last,
    next_due_date,
    next_occurrence_date,
    predicted_due_date,
    task_urgency,
)
from core.profile_manager import ProfileManager
from core.skill_manager import SkillManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(maintenance_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(maintenance_manager_module, "_MAINTENANCE_FILE", data_dir / "maintenance.json")
    monkeypatch.setattr(maintenance_manager_module, "_DOCUMENT_ROOT", tmp_path / "maintenance_documents")
    monkeypatch.setattr(data_logger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(data_logger_manager_module, "_READINGS_FILE", data_dir / "data_logger_readings.json")
    monkeypatch.setattr(calendar_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(calendar_manager_module, "_EVENTS_FILE", data_dir / "calendar_events.json")
    # Real once a test constructs a real ProfileManager too (2026-09-11
    # gamification hook tests below) — see test_workout_manager.py's
    # own isolated_paths for the identical reasoning.
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    # "My Hero's Path" (2026-09-11) — needed once a test constructs a
    # real SkillManager too, same reasoning as config_manager above.
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    return data_dir


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.data_logger = DataLoggerManager(context)
    context.calendar = CalendarManager(context)
    return context


def _make_manager(context: AppContext) -> MaintenanceManager:
    manager = MaintenanceManager(context)
    context.maintenance = manager
    return manager


def _task(**overrides) -> MaintenanceTask:
    defaults = dict(task_id="t1", asset_id="a1", title="Oil change")
    defaults.update(overrides)
    return MaintenanceTask(**defaults)


def _reading(value: float, timestamp: str) -> Reading:
    return Reading(reading_id="r", series_id="s", value=value, timestamp=timestamp)


# ------------------------------------------------------------------
# Dataclass backward compatibility
# ------------------------------------------------------------------

def test_maintenance_asset_from_dict_backward_compatible_with_old_shape():
    asset = MaintenanceAsset.from_dict({"asset_id": "a1", "name": "Mower"})
    assert asset.category == "Other"
    assert asset.documents == []


def test_maintenance_task_from_dict_backward_compatible_with_old_shape():
    task = MaintenanceTask.from_dict({"task_id": "t1", "asset_id": "a1", "title": "Oil change"})
    assert task.trigger_type == "calendar"
    assert task.threshold_direction == "below"
    assert task.auto_schedule is False


def test_maintenance_task_series_id():
    task = _task(task_id="abc123")
    assert task.series_id == "maintenance_abc123"


def test_maintenance_task_is_meter_task_and_is_sensor_task():
    assert _task(trigger_type="runtime").is_meter_task is True
    assert _task(trigger_type="runtime").is_sensor_task is False
    assert _task(trigger_type="sensor").is_sensor_task is True
    assert _task(trigger_type="sensor").is_meter_task is False
    assert _task(trigger_type="calendar").is_meter_task is False
    assert _task(trigger_type="calendar").is_sensor_task is False


# ------------------------------------------------------------------
# Pure recurrence logic — next_due_date / days_until_due / is_overdue
# ------------------------------------------------------------------

def test_next_due_date_none_for_one_time_task():
    task = _task(interval_days=None, last_completed="2026-01-01")
    assert next_due_date(task) is None


def test_next_due_date_none_when_never_completed():
    task = _task(interval_days=90, last_completed=None)
    assert next_due_date(task) is None


def test_next_due_date_computes_forward_from_last_completed():
    task = _task(interval_days=90, last_completed="2026-01-01")
    assert next_due_date(task) == date(2026, 4, 1)


def test_days_until_due_none_when_next_due_date_is_none():
    task = _task(interval_days=None, last_completed=None)
    assert days_until_due(task, date(2026, 1, 1)) is None


def test_days_until_due_negative_when_overdue():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert days_until_due(task, date(2026, 1, 15)) == -4


def test_days_until_due_zero_when_due_today():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert days_until_due(task, date(2026, 1, 11)) == 0


def test_days_until_due_positive_when_in_the_future():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert days_until_due(task, date(2026, 1, 5)) == 6


def test_is_overdue_true_when_negative_remaining():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert is_overdue(task, date(2026, 1, 15)) is True


def test_is_overdue_false_when_due_today_or_future():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert is_overdue(task, date(2026, 1, 11)) is False
    assert is_overdue(task, date(2026, 1, 5)) is False


def test_is_overdue_false_for_one_time_or_never_completed_task():
    assert is_overdue(_task(interval_days=None), date(2026, 1, 1)) is False
    assert is_overdue(_task(interval_days=10, last_completed=None), date(2026, 1, 1)) is False


# ------------------------------------------------------------------
# Meter mechanism — meter_used_since_last / is_meter_task_due
# ------------------------------------------------------------------

def test_meter_used_since_last_none_without_baseline():
    task = _task(trigger_type="mileage", last_completed_meter_value=None)
    readings = [_reading(1000, "2026-01-01T00:00:00")]
    assert meter_used_since_last(task, readings) is None


def test_meter_used_since_last_none_without_readings():
    task = _task(trigger_type="mileage", last_completed_meter_value=50000)
    assert meter_used_since_last(task, []) is None


def test_meter_used_since_last_computes_diff_from_latest_reading():
    task = _task(trigger_type="mileage", last_completed_meter_value=50000)
    readings = [_reading(50100, "2026-01-01T00:00:00"), _reading(50300, "2026-01-05T00:00:00")]
    assert meter_used_since_last(task, readings) == 300


def test_is_meter_task_due_false_without_meter_interval():
    task = _task(trigger_type="mileage", meter_interval=None, last_completed_meter_value=50000)
    readings = [_reading(53000, "2026-01-01T00:00:00")]
    assert is_meter_task_due(task, readings) is False


def test_is_meter_task_due_false_when_under_interval():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    readings = [_reading(52000, "2026-01-01T00:00:00")]
    assert is_meter_task_due(task, readings) is False


def test_is_meter_task_due_true_when_at_or_over_interval():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    readings = [_reading(53000, "2026-01-01T00:00:00")]
    assert is_meter_task_due(task, readings) is True
    readings_over = [_reading(53500, "2026-01-01T00:00:00")]
    assert is_meter_task_due(task, readings_over) is True


# ------------------------------------------------------------------
# Threshold mechanism — is_sensor_task_due
# ------------------------------------------------------------------

def test_is_sensor_task_due_false_without_threshold_value():
    task = _task(trigger_type="sensor", threshold_value=None)
    assert is_sensor_task_due(task, [_reading(10, "2026-01-01T00:00:00")]) is False


def test_is_sensor_task_due_false_without_readings():
    task = _task(trigger_type="sensor", threshold_value=20)
    assert is_sensor_task_due(task, []) is False


def test_is_sensor_task_due_below_direction():
    task = _task(trigger_type="sensor", threshold_value=20, threshold_direction="below")
    assert is_sensor_task_due(task, [_reading(15, "2026-01-01T00:00:00")]) is True
    assert is_sensor_task_due(task, [_reading(25, "2026-01-01T00:00:00")]) is False


def test_is_sensor_task_due_above_direction():
    task = _task(trigger_type="sensor", threshold_value=80, threshold_direction="above")
    assert is_sensor_task_due(task, [_reading(85, "2026-01-01T00:00:00")]) is True
    assert is_sensor_task_due(task, [_reading(75, "2026-01-01T00:00:00")]) is False


def test_is_sensor_task_due_uses_latest_reading_by_timestamp():
    task = _task(trigger_type="sensor", threshold_value=20, threshold_direction="below")
    readings = [_reading(10, "2026-01-01T00:00:00"), _reading(25, "2026-01-05T00:00:00")]
    assert is_sensor_task_due(task, readings) is False  # latest (25) is above threshold


# ------------------------------------------------------------------
# predicted_due_date — linear usage-rate projection
# ------------------------------------------------------------------

def test_predicted_due_date_none_for_non_meter_task():
    task = _task(trigger_type="calendar")
    readings = [_reading(1, "2026-01-01T00:00:00"), _reading(2, "2026-01-02T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 1, 1)) is None


def test_predicted_due_date_none_without_meter_interval():
    task = _task(trigger_type="mileage", meter_interval=None, last_completed_meter_value=50000)
    readings = [_reading(50100, "2026-01-01T00:00:00"), _reading(50200, "2026-01-02T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 1, 2)) is None


def test_predicted_due_date_none_with_fewer_than_two_readings():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    assert predicted_due_date(task, [], date(2026, 1, 1)) is None
    assert predicted_due_date(task, [_reading(50100, "2026-01-01T00:00:00")], date(2026, 1, 1)) is None


def test_predicted_due_date_none_without_completion_baseline():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=None)
    readings = [_reading(100, "2026-01-01T00:00:00"), _reading(200, "2026-01-02T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 1, 2)) is None


def test_predicted_due_date_none_when_already_due():
    task = _task(trigger_type="mileage", meter_interval=1000, last_completed_meter_value=50000)
    readings = [_reading(50900, "2026-01-01T00:00:00"), _reading(51100, "2026-01-02T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 1, 2)) is None


def test_predicted_due_date_none_when_readings_have_the_same_timestamp():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    readings = [_reading(50100, "2026-01-01T00:00:00"), _reading(50200, "2026-01-01T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 1, 1)) is None


def test_predicted_due_date_none_when_usage_rate_is_not_increasing():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    readings = [_reading(50200, "2026-01-01T00:00:00"), _reading(50100, "2026-01-05T00:00:00")]
    assert predicted_due_date(task, readings, date(2026, 1, 5)) is None


def test_predicted_due_date_real_projection_weeks_phrasing():
    task = _task(trigger_type="runtime", meter_unit="hrs", meter_interval=100, last_completed_meter_value=0)
    # 4 readings over 7 days, 21 hours used -> 3 hrs/day, remaining 79 hrs -> ~26.3 days -> ~4 weeks
    readings = [
        _reading(0, "2026-01-01T00:00:00"),
        _reading(7, "2026-01-02T00:00:00"),
        _reading(14, "2026-01-05T00:00:00"),
        _reading(21, "2026-01-08T00:00:00"),
    ]
    result = predicted_due_date(task, readings, date(2026, 1, 8))
    assert result is not None
    estimated, caveat = result
    assert estimated > date(2026, 1, 8)
    assert "weeks" in caveat
    assert "hrs/week" in caveat
    assert "4 logged readings" in caveat


def test_predicted_due_date_days_phrasing_for_short_estimates():
    task = _task(trigger_type="mileage", meter_unit="miles", meter_interval=100, last_completed_meter_value=0)
    readings = [_reading(0, "2026-01-01T00:00:00"), _reading(90, "2026-01-02T00:00:00")]
    result = predicted_due_date(task, readings, date(2026, 1, 2))
    assert result is not None
    estimated, caveat = result
    assert "days" in caveat
    assert "weeks" not in caveat


# ------------------------------------------------------------------
# task_urgency — "smart calendar" pass (2026-09-12)
# ------------------------------------------------------------------

def test_task_urgency_calendar_overdue():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert task_urgency(task, [], date(2026, 1, 15)) == "overdue"


def test_task_urgency_calendar_due_soon():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert task_urgency(task, [], date(2026, 1, 9)) == "due_soon"  # 2 days remaining


def test_task_urgency_calendar_on_track():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert task_urgency(task, [], date(2026, 1, 1)) == "on_track"  # 10 days remaining


def test_task_urgency_calendar_unknown_when_never_completed():
    task = _task(interval_days=10, last_completed=None)
    assert task_urgency(task, [], date(2026, 1, 1)) == "unknown"


def test_task_urgency_meter_unknown_without_baseline():
    task = _task(trigger_type="mileage", last_completed_meter_value=None)
    assert task_urgency(task, [_reading(100, "2026-01-01T00:00:00")], date(2026, 1, 1)) == "unknown"


def test_task_urgency_meter_overdue():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    readings = [_reading(53000, "2026-01-01T00:00:00")]
    assert task_urgency(task, readings, date(2026, 1, 1)) == "overdue"


def test_task_urgency_meter_due_soon():
    task = _task(trigger_type="mileage", meter_unit="miles", meter_interval=100, last_completed_meter_value=0)
    readings = [_reading(0, "2026-01-01T00:00:00"), _reading(90, "2026-01-02T00:00:00")]
    assert task_urgency(task, readings, date(2026, 1, 2)) == "due_soon"


def test_task_urgency_meter_on_track():
    task = _task(trigger_type="mileage", meter_unit="miles", meter_interval=100, last_completed_meter_value=0)
    readings = [_reading(0, "2026-01-01T00:00:00"), _reading(5, "2026-01-02T00:00:00")]
    assert task_urgency(task, readings, date(2026, 1, 2)) == "on_track"


def test_task_urgency_sensor_unknown_without_readings():
    task = _task(trigger_type="sensor", threshold_value=20, threshold_direction="below")
    assert task_urgency(task, [], date(2026, 1, 1)) == "unknown"


def test_task_urgency_sensor_overdue():
    task = _task(trigger_type="sensor", threshold_value=20, threshold_direction="below")
    readings = [_reading(15, "2026-01-01T00:00:00")]
    assert task_urgency(task, readings, date(2026, 1, 1)) == "overdue"


def test_task_urgency_sensor_on_track():
    task = _task(trigger_type="sensor", threshold_value=20, threshold_direction="below")
    readings = [_reading(25, "2026-01-01T00:00:00")]
    assert task_urgency(task, readings, date(2026, 1, 1)) == "on_track"


# ------------------------------------------------------------------
# next_occurrence_date — "smart calendar" pass (2026-09-12)
# ------------------------------------------------------------------

def test_next_occurrence_date_calendar_matches_next_due_date():
    task = _task(interval_days=10, last_completed="2026-01-01")
    assert next_occurrence_date(task, [], date(2026, 1, 5)) == next_due_date(task)


def test_next_occurrence_date_calendar_none_when_never_completed():
    task = _task(interval_days=10, last_completed=None)
    assert next_occurrence_date(task, [], date(2026, 1, 1)) is None


def test_next_occurrence_date_meter_today_when_already_due():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    readings = [_reading(53000, "2026-01-01T00:00:00")]
    today = date(2026, 1, 10)
    assert next_occurrence_date(task, readings, today) == today


def test_next_occurrence_date_meter_uses_predicted_estimate():
    task = _task(trigger_type="mileage", meter_unit="miles", meter_interval=100, last_completed_meter_value=0)
    readings = [_reading(0, "2026-01-01T00:00:00"), _reading(90, "2026-01-02T00:00:00")]
    today = date(2026, 1, 2)
    expected = predicted_due_date(task, readings, today)[0]
    assert next_occurrence_date(task, readings, today) == expected


def test_next_occurrence_date_meter_none_without_enough_data():
    task = _task(trigger_type="mileage", meter_interval=3000, last_completed_meter_value=50000)
    assert next_occurrence_date(task, [], date(2026, 1, 1)) is None


def test_next_occurrence_date_sensor_today_when_due():
    task = _task(trigger_type="sensor", threshold_value=20, threshold_direction="below")
    readings = [_reading(15, "2026-01-01T00:00:00")]
    today = date(2026, 1, 10)
    assert next_occurrence_date(task, readings, today) == today


def test_next_occurrence_date_sensor_none_when_not_due():
    task = _task(trigger_type="sensor", threshold_value=20, threshold_direction="below")
    readings = [_reading(25, "2026-01-01T00:00:00")]
    assert next_occurrence_date(task, readings, date(2026, 1, 10)) is None


# ------------------------------------------------------------------
# priority — "smart calendar" pass (2026-09-12)
# ------------------------------------------------------------------

def test_task_priority_defaults_to_normal():
    assert _task().priority == "normal"


def test_task_priority_round_trips_through_to_dict_from_dict():
    task = _task(priority="high")
    assert MaintenanceTask.from_dict(task.to_dict()).priority == "high"


def test_task_priority_backward_compatible_with_old_shape():
    task = MaintenanceTask.from_dict({"task_id": "t1", "asset_id": "a1", "title": "Oil change"})
    assert task.priority == "normal"


def test_add_task_defaults_priority_to_normal(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change")
    assert task.priority == "normal"


def test_add_task_accepts_a_real_priority(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", priority="high")
    assert task.priority == "high"


# ------------------------------------------------------------------
# MaintenanceManager — Asset CRUD
# ------------------------------------------------------------------

def test_reload_picks_up_changes_written_by_another_instance(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_asset(name="Lawn Mower")

    # Simulate another process/instance writing to the same file.
    other = MaintenanceManager(context)
    other.add_asset(name="Truck")

    assert len(manager.all_assets()) == 1  # stale in-memory state
    manager.reload()
    assert len(manager.all_assets()) == 2


def test_add_asset_defaults_and_persists(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_asset(name="Lawn Mower", category="Power Equipment")

    reloaded = MaintenanceManager(context)
    found = reloaded.get_asset(reloaded.all_assets()[0].asset_id)
    assert found.name == "Lawn Mower"
    assert found.category == "Power Equipment"


def test_add_asset_owner_profile_id_defaults_to_none(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Lawn Mower")
    assert asset.owner_profile_id is None


def test_add_asset_owner_profile_id_persists_across_a_fresh_load(isolated_paths):
    """Per-profile/per-vehicle rewards (2026-09-14)."""
    context = _make_context()
    manager = _make_manager(context)
    manager.add_asset(name="Ridgeline", category="Vehicle", owner_profile_id="zac-id")

    reloaded = MaintenanceManager(context)
    found = reloaded.all_assets()[0]
    assert found.owner_profile_id == "zac-id"


def test_update_asset_can_reassign_owner_profile_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Ridgeline")
    manager.update_asset(asset.asset_id, owner_profile_id="zac-id")
    assert manager.get_asset(asset.asset_id).owner_profile_id == "zac-id"


def test_update_asset_changes_fields(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Lawn Mower")
    manager.update_asset(asset.asset_id, name="Riding Mower", manufacturer="John Deere")
    updated = manager.get_asset(asset.asset_id)
    assert updated.name == "Riding Mower"
    assert updated.manufacturer == "John Deere"


def test_update_asset_rejects_unknown_field(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Lawn Mower")
    with pytest.raises(ValueError):
        manager.update_asset(asset.asset_id, not_a_real_field="x")


def test_update_asset_raises_for_unknown_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.update_asset("no-such-id", name="X")


def test_get_asset_found_and_not_found(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Lawn Mower")
    assert manager.get_asset(asset.asset_id) is not None
    assert manager.get_asset("no-such-id") is None


def test_all_assets_sorted_by_name(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_asset(name="Zed Truck")
    manager.add_asset(name="Aardvark Mower")
    assert [a.name for a in manager.all_assets()] == ["Aardvark Mower", "Zed Truck"]


def test_delete_asset_cascades_tasks_and_document_folder(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Lawn Mower")
    manager.add_task(asset_id=asset.asset_id, title="Change oil")

    source = tmp_path / "manual.pdf"
    source.write_bytes(b"fake pdf")
    manager.add_document(asset.asset_id, source)
    doc_dir = maintenance_manager_module._DOCUMENT_ROOT / asset.asset_id
    assert doc_dir.exists()

    manager.delete_asset(asset.asset_id)

    assert manager.get_asset(asset.asset_id) is None
    assert manager.tasks_for_asset(asset.asset_id) == []
    assert not doc_dir.exists()


# ------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------

def test_add_document_copies_file_and_records_filename(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    source = tmp_path / "warranty.pdf"
    source.write_bytes(b"warranty contents")

    filename = manager.add_document(asset.asset_id, source)

    assert filename == "warranty.pdf"
    assert asset.documents == ["warranty.pdf"]
    stored = manager.document_path(asset.asset_id, "warranty.pdf")
    assert stored.exists()
    assert stored.read_bytes() == b"warranty contents"
    assert stored != source  # a real copy, not the original path


def test_add_document_raises_for_unknown_asset(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    source = tmp_path / "file.pdf"
    source.write_bytes(b"x")
    with pytest.raises(ValueError):
        manager.add_document("no-such-asset", source)


def test_remove_document_deletes_stored_copy_not_original(isolated_paths, tmp_path):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    source = tmp_path / "warranty.pdf"
    source.write_bytes(b"warranty contents")
    manager.add_document(asset.asset_id, source)

    manager.remove_document(asset.asset_id, "warranty.pdf")

    assert asset.documents == []
    assert not manager.document_path(asset.asset_id, "warranty.pdf").exists()
    assert source.exists()  # the user's original file is untouched


def test_remove_document_raises_for_unknown_asset(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.remove_document("no-such-asset", "x.pdf")


# ------------------------------------------------------------------
# Task CRUD
# ------------------------------------------------------------------

def test_add_task_defaults_and_persists(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    manager.add_task(asset_id=asset.asset_id, title="Oil change", interval_days=90)

    reloaded = MaintenanceManager(context)
    task = reloaded.all_tasks()[0]
    assert task.title == "Oil change"
    assert task.interval_days == 90
    assert task.trigger_type == "calendar"


def test_add_task_reward_baseline_value_defaults_to_none(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles")
    assert task.reward_baseline_value is None


def test_add_task_reward_baseline_value_persists_across_a_fresh_load(isolated_paths):
    """Per-profile/per-vehicle rewards (2026-09-14) — a vehicle with
    real prior history starts reward tracking from this baseline."""
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    manager.add_task(
        asset_id=asset.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles",
        reward_baseline_value=207000.0,
    )

    reloaded = MaintenanceManager(context)
    task = reloaded.all_tasks()[0]
    assert task.reward_baseline_value == 207000.0


def test_update_task_can_set_reward_baseline_value(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles")
    manager.update_task(task.task_id, reward_baseline_value=207000.0)
    assert manager.get_task(task.task_id).reward_baseline_value == 207000.0


def test_update_task_changes_fields(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change")
    manager.update_task(task.task_id, title="Oil + filter change", interval_days=180)
    updated = manager.get_task(task.task_id)
    assert updated.title == "Oil + filter change"
    assert updated.interval_days == 180


def test_update_task_rejects_unknown_field(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change")
    with pytest.raises(ValueError):
        manager.update_task(task.task_id, not_a_real_field="x")


def test_update_task_raises_for_unknown_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.update_task("no-such-id", title="X")


def test_delete_task(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change")
    manager.delete_task(task.task_id)
    assert manager.get_task(task.task_id) is None


def test_get_task_found_and_not_found(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change")
    assert manager.get_task(task.task_id) is not None
    assert manager.get_task("no-such-id") is None


def test_all_tasks_returns_every_task(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    manager.add_task(asset_id=asset.asset_id, title="Oil change")
    manager.add_task(asset_id=asset.asset_id, title="Tire rotation")
    assert {t.title for t in manager.all_tasks()} == {"Oil change", "Tire rotation"}


def test_tasks_for_asset_filters(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset1 = manager.add_asset(name="Truck")
    asset2 = manager.add_asset(name="Mower")
    manager.add_task(asset_id=asset1.asset_id, title="Oil change")
    manager.add_task(asset_id=asset2.asset_id, title="Blade sharpen")
    assert [t.title for t in manager.tasks_for_asset(asset1.asset_id)] == ["Oil change"]


# ------------------------------------------------------------------
# mark_complete
# ------------------------------------------------------------------

def test_mark_complete_sets_last_completed_to_given_date(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="calendar")
    manager.mark_complete(task.task_id, completed_date="2026-03-01")
    assert manager.get_task(task.task_id).last_completed == "2026-03-01"


def test_mark_complete_defaults_to_today(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change")
    manager.mark_complete(task.task_id)
    assert manager.get_task(task.task_id).last_completed == date.today().isoformat()


def test_mark_complete_grants_xp_to_the_active_profile(isolated_paths):
    """2026-09-11 gamification pass — a real, distinct completion event
    each call, including a recurring task's own legitimate
    re-completion on schedule."""
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)
    context.profiles.create_profile(name="Alex", make_active=True)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="calendar")

    manager.mark_complete(task.task_id)

    assert context.profiles.get_active_profile().total_xp == 10


def test_mark_complete_grants_xp_with_no_active_profile_does_not_raise(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="calendar")
    manager.mark_complete(task.task_id)  # must not raise


def test_mark_complete_grants_home_maintenance_skill_xp(isolated_paths):
    """"My Hero's Path" (2026-09-11)."""
    isolated_paths.mkdir(parents=True, exist_ok=True)
    (isolated_paths / "skill_definitions.json").write_text(
        json.dumps({"skills": [{"skill_id": "home_maintenance", "name": "Home Maintenance", "category": "Homestead"}]})
    )
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)
    context.skills = SkillManager(context)
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="calendar")

    manager.mark_complete(task.task_id)

    assert context.skills.get_progress(profile.profile_id, "home_maintenance").total_xp == 10


def test_mark_complete_meter_task_with_explicit_value(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="mileage", meter_interval=3000)
    manager.mark_complete(task.task_id, meter_value=50000)
    assert manager.get_task(task.task_id).last_completed_meter_value == 50000


def test_mark_complete_meter_task_defaults_to_latest_logged_reading(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="mileage", meter_interval=3000)
    manager.log_reading(task.task_id, 50000)
    manager.log_reading(task.task_id, 50250)

    manager.mark_complete(task.task_id)

    assert manager.get_task(task.task_id).last_completed_meter_value == 50250


def test_mark_complete_meter_task_no_readings_leaves_baseline_none(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="mileage", meter_interval=3000)
    manager.mark_complete(task.task_id)
    assert manager.get_task(task.task_id).last_completed_meter_value is None


def test_mark_complete_non_meter_task_does_not_touch_meter_value(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Wash truck", trigger_type="calendar")
    manager.mark_complete(task.task_id)
    assert manager.get_task(task.task_id).last_completed_meter_value is None


def test_mark_complete_raises_for_unknown_task(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.mark_complete("no-such-id")


# ------------------------------------------------------------------
# Task readings — real DataLoggerManager integration
# ------------------------------------------------------------------

def test_log_reading_raises_for_unknown_task(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.log_reading("no-such-id", 100.0)


def test_log_reading_writes_through_data_logger_keyed_by_series_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change", trigger_type="mileage", meter_unit="miles")

    manager.log_reading(task.task_id, 50100.0, note="fill-up")

    readings = context.data_logger.readings_for(task.series_id)
    assert len(readings) == 1
    assert readings[0].value == 50100.0
    assert readings[0].unit == "miles"  # falls back to task.meter_unit when unit not given
    assert readings[0].note == "fill-up"


def test_readings_for_task_returns_empty_for_unknown_task(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    assert manager.readings_for_task("no-such-id") == []


def test_log_reading_stamps_the_active_profile_id(isolated_paths):
    """Multi-user pass (2026-09-14) — same auto-attribution precedent
    core.workout_manager.WorkoutSession.profile_id already established."""
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles")

    reading = manager.log_reading(task.task_id, 50100.0)

    assert reading.profile_id == profile.profile_id


def test_log_reading_with_no_active_profile_leaves_profile_id_none(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Odometer", trigger_type="mileage", meter_unit="miles")

    reading = manager.log_reading(task.task_id, 50100.0)

    assert reading.profile_id is None


# ------------------------------------------------------------------
# Asset-level usage stats — independent of any task
# ------------------------------------------------------------------

def test_log_asset_reading_raises_for_unknown_asset(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.log_asset_reading("no-such-id", "Fuel", 12.0)


def test_log_asset_reading_stamps_the_active_profile_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    context.profiles = ProfileManager(context)
    profile = context.profiles.create_profile(name="Alex", make_active=True)
    asset = manager.add_asset(name="Truck")

    reading = manager.log_asset_reading(asset.asset_id, "Fuel", 12.0)

    assert reading.profile_id == profile.profile_id


def test_asset_meter_names_derived_from_series_prefix_only(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    manager.log_asset_reading(asset.asset_id, "Fuel", 12.0)
    manager.log_asset_reading(asset.asset_id, "Odometer", 50000.0)
    assert manager.asset_meter_names(asset.asset_id) == ["Fuel", "Odometer"]


def test_asset_readings_returns_only_that_meter(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    manager.log_asset_reading(asset.asset_id, "Fuel", 12.0)
    manager.log_asset_reading(asset.asset_id, "Odometer", 50000.0)
    readings = manager.asset_readings(asset.asset_id, "Fuel")
    assert len(readings) == 1
    assert readings[0].value == 12.0


# ------------------------------------------------------------------
# Calendar integration
# ------------------------------------------------------------------

def test_schedule_task_creates_real_calendar_event_and_stores_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    asset = manager.add_asset(name="Truck")
    task = manager.add_task(asset_id=asset.asset_id, title="Oil change")

    event = manager.schedule_task(task.task_id, "2026-03-01")

    assert event.title == "Maintenance: Oil change (Truck)"
    assert event.date == "2026-03-01"
    updated_task = manager.get_task(task.task_id)
    assert updated_task.calendar_event_id == event.event_id
    real_events = context.calendar.events_for_date("2026-03-01")
    assert any(e.event_id == event.event_id for e in real_events)


def test_schedule_task_raises_for_unknown_task(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.schedule_task("no-such-id", "2026-03-01")
