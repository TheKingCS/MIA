"""
tests.test_energy_manager
============================

Unit tests for core.energy_manager. Isolates _DATA_DIR/
_ENERGY_SOURCES_FILE (and core.data_logger_manager's own data file,
since readings are real DataLogger entries this manager passes
through), same monkeypatch pattern as tests/test_data_logger_manager
.py's isolated_paths.
"""

from __future__ import annotations

import pytest

import core.data_logger_manager as data_logger_manager_module
import core.energy_manager as energy_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.energy_manager import EnergyManager
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(energy_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(energy_manager_module, "_ENERGY_SOURCES_FILE", data_dir / "energy_sources.json")
    monkeypatch.setattr(data_logger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(data_logger_manager_module, "_READINGS_FILE", data_dir / "data_logger_readings.json")
    return data_dir


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.data_logger = DataLoggerManager(context)
    return context


def _make_manager(context: AppContext) -> EnergyManager:
    manager = EnergyManager(context)
    context.energy = manager
    return manager


# ------------------------------------------------------------------
# EnergySource CRUD
# ------------------------------------------------------------------

def test_add_energy_source_defaults_and_persists(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Rooftop Solar Array", source_type="Solar", notes="12 panels")

    reloaded = EnergyManager(context)
    found = reloaded.get_energy_source(source.source_id)
    assert found is not None
    assert found.name == "Rooftop Solar Array"
    assert found.source_type == "Solar"
    assert found.notes == "12 panels"


def test_add_energy_source_coerces_unknown_type_to_other(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Mystery Box", source_type="Nonsense")
    assert source.source_type == "Other"


def test_update_energy_source_rejects_unknown_field(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Backup Generator", source_type="Generator")
    with pytest.raises(ValueError):
        manager.update_energy_source(source.source_id, not_a_real_field="x")


def test_update_energy_source_coerces_unknown_type_to_other(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Backup Generator", source_type="Generator")
    updated = manager.update_energy_source(source.source_id, source_type="Nonsense")
    assert updated.source_type == "Other"


def test_update_energy_source_raises_for_unknown_id(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.update_energy_source("no-such-id", name="X")


def test_get_energy_source_found_and_not_found(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Propane Tank", source_type="Propane")
    assert manager.get_energy_source(source.source_id) is not None
    assert manager.get_energy_source("no-such-id") is None


def test_all_energy_sources_sorted_by_name(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    manager.add_energy_source(name="Zed Generator")
    manager.add_energy_source(name="Aquaponics Solar Bank")
    names = [s.name for s in manager.all_energy_sources()]
    assert names == ["Aquaponics Solar Bank", "Zed Generator"]


def test_energy_source_from_dict_backward_compatible_with_old_shape():
    from core.energy_manager import EnergySource
    old_shape = {"source_id": "s1", "name": "Propane Tank"}
    source = EnergySource.from_dict(old_shape)
    assert source.source_type == "Other"
    assert source.notes == ""


# ------------------------------------------------------------------
# Readings — thin passthrough to DataLoggerManager
# ------------------------------------------------------------------

def test_log_energy_reading_raises_for_unknown_source(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    with pytest.raises(ValueError):
        manager.log_energy_reading("no-such-id", "kWh Generated", 12.4)


def test_log_energy_reading_writes_through_data_logger(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Backup Generator", source_type="Generator")

    manager.log_energy_reading(source.source_id, "kWh Generated", 12.4, unit="kWh", note="test run")

    series_id = EnergyManager._energy_source_series_id(source.source_id, "kWh Generated")
    readings = context.data_logger.readings_for(series_id)
    assert len(readings) == 1
    assert readings[0].value == 12.4
    assert readings[0].unit == "kWh"
    assert readings[0].note == "test run"


def test_energy_source_meter_names_derived_from_series_prefix_only(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Backup Generator", source_type="Generator")

    manager.log_energy_reading(source.source_id, "kWh Generated", 12.4)
    manager.log_energy_reading(source.source_id, "Fuel Level %", 80.0)

    assert manager.energy_source_meter_names(source.source_id) == ["Fuel Level %", "kWh Generated"]


def test_energy_source_readings_returns_only_that_meter(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Backup Generator", source_type="Generator")

    manager.log_energy_reading(source.source_id, "kWh Generated", 12.4)
    manager.log_energy_reading(source.source_id, "Fuel Level %", 80.0)

    readings = manager.energy_source_readings(source.source_id, "kWh Generated")
    assert len(readings) == 1
    assert readings[0].value == 12.4


def test_delete_energy_source_removes_record_only_leaves_readings_orphaned(isolated_paths):
    context = _make_context()
    manager = _make_manager(context)
    source = manager.add_energy_source(name="Backup Generator", source_type="Generator")
    manager.log_energy_reading(source.source_id, "kWh Generated", 12.4)

    manager.delete_energy_source(source.source_id)

    assert manager.get_energy_source(source.source_id) is None
    # Real history isn't deleted along with the EnergySource record —
    # same non-cascading stance every other "delete a parent record"
    # path in this codebase takes.
    assert manager.energy_source_meter_names(source.source_id) == ["kWh Generated"]
    readings = manager.energy_source_readings(source.source_id, "kWh Generated")
    assert len(readings) == 1
    assert readings[0].value == 12.4
