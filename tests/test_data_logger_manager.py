"""
tests.test_data_logger_manager
=================================

Unit tests for core.data_logger_manager. Isolates _DATA_DIR/_READINGS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_inventory_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.data_logger_manager as data_logger_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    readings_file = data_dir / "data_logger_readings.json"
    monkeypatch.setattr(data_logger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(data_logger_manager_module, "_READINGS_FILE", readings_file)
    return data_dir, readings_file


def _make_manager() -> DataLoggerManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return DataLoggerManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.list_series() == []
    assert manager.readings_for("anything") == []


def test_add_reading_creates_the_series_implicitly(isolated_paths):
    manager = _make_manager()
    manager.add_reading("soil_moisture", 42.0, unit="%")
    assert manager.list_series() == ["soil_moisture"]


def test_add_reading_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_reading("multimeter_voltage", 3.3, unit="V", note="bench PSU")

    reloaded = _make_manager()
    readings = reloaded.readings_for("multimeter_voltage")
    assert len(readings) == 1
    assert readings[0].value == 3.3
    assert readings[0].unit == "V"
    assert readings[0].note == "bench PSU"


def test_readings_for_returns_only_that_series_oldest_first(isolated_paths):
    manager = _make_manager()
    manager.add_reading("a", 1.0, timestamp="2026-01-01T10:00:00")
    manager.add_reading("b", 99.0, timestamp="2026-01-01T10:05:00")
    manager.add_reading("a", 2.0, timestamp="2026-01-01T09:00:00")

    readings = manager.readings_for("a")
    assert [r.value for r in readings] == [2.0, 1.0]


def test_list_series_is_sorted_and_distinct(isolated_paths):
    manager = _make_manager()
    manager.add_reading("soil_moisture", 1.0)
    manager.add_reading("multimeter_voltage", 2.0)
    manager.add_reading("soil_moisture", 3.0)
    assert manager.list_series() == ["multimeter_voltage", "soil_moisture"]


def test_delete_reading_removes_only_that_reading(isolated_paths):
    manager = _make_manager()
    first = manager.add_reading("a", 1.0)
    manager.add_reading("a", 2.0)

    manager.delete_reading(first.reading_id)

    readings = manager.readings_for("a")
    assert len(readings) == 1
    assert readings[0].value == 2.0


def test_corrupt_file_starts_empty_rather_than_crashing(isolated_paths):
    data_dir, readings_file = isolated_paths
    data_dir.mkdir(parents=True)
    readings_file.write_text("not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.list_series() == []
