"""
tests/test_sensors.py — sensors that send their own readings (core/sensors.py): a sensor added by a person gets a key
shown once and kept as a hash; its readings go through its app's own reading action (the Lab, Power, the Greenhouse)
as that person; a key does nothing else, a reading must be a number and not too soon, and removing a sensor stops its
key at once.
"""

from datetime import datetime, timedelta

import pytest

from core import sensors
from core.actions import ACTION_TYPES, ActionError


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The shared engine world with a sensor store."""
    from tests.engine_world import build_world

    from core.data_logger_manager import DataLoggerManager
    from core.energy_manager import EnergyManager
    from core.grow_lab import GrowLab

    context = build_world(tmp_path, monkeypatch)
    context.data_logger = DataLoggerManager(context, data_dir=tmp_path / "dev")
    context.energy = EnergyManager(context, data_dir=tmp_path / "dev")
    context.grow_lab = GrowLab(context, data_dir=tmp_path / "dev")
    context.sensors = sensors.SensorStore(context, data_dir=tmp_path / "dev")
    return context


def _same(context, profile_id):
    """view_for in a single-person world: the context itself."""
    return context


NOW = datetime(2026, 11, 9, 8, 0)


def test_a_lab_sensors_readings_land_in_its_series_and_the_key_is_kept_only_as_a_hash(world):
    sensor, key = world.sensors.add("p1", "Bench probe", "lab", {"series": "soil moisture", "unit": "%"})
    assert sensor["goes_to"] == "The Lab: soil moisture (%)" and "key_hash" not in sensor
    raw = (world.sensors.data_dir / sensors.FILE).read_text()
    assert key not in raw and sensors._hash(key) in raw
    done = sensors.reading(world, _same, key, "41.5", now=NOW)
    assert done["value"] == 41.5
    assert [r.value for r in world.data_logger.readings_for("soil moisture")] == [41.5]
    assert world.sensors.get(sensor["id"])["count"] == 1


def test_a_reading_must_be_a_number_not_too_soon_and_from_a_real_key(world):
    _s, key = world.sensors.add("p1", "Probe", "lab", {"series": "temp"})
    with pytest.raises(sensors.SensorError, match="isn't a sensor"):
        sensors.reading(world, _same, "mia-s-nope", 1, now=NOW)
    with pytest.raises(sensors.SensorError, match="one number"):
        sensors.reading(world, _same, key, "warm", now=NOW)
    with pytest.raises(sensors.SensorError, match="one number"):
        sensors.reading(world, _same, key, float("nan"), now=NOW)
    sensors.reading(world, _same, key, 20, now=NOW)
    with pytest.raises(sensors.SensorError, match="Too soon"):
        sensors.reading(world, _same, key, 21, now=NOW + timedelta(seconds=5))
    sensors.reading(world, _same, key, 21, now=NOW + timedelta(seconds=sensors.MIN_GAP))


def test_greenhouse_and_power_sensors_use_their_apps_reading_actions(world):
    from core.grow_lab import series_id

    world.grow_lab.add_system("Tank 1")
    g, gkey = world.sensors.add("p1", "pH probe", "greenhouse", {"place": "Tank 1", "measure": "pH"})
    assert g["target"]["measure"] == "ph"  # the grow lab's own measure, said by name
    sensors.reading(world, _same, gkey, 6.8, now=NOW)
    assert [r.value for r in world.data_logger.readings_for(series_id("Tank 1", "ph"))] == [6.8]
    with pytest.raises(sensors.SensorError, match="measures one of"):
        world.sensors.add("p1", "Odd", "greenhouse", {"place": "Tank 1", "measure": "vibes"})
    source = world.energy.add_energy_source("Solar bank", "Solar")
    _p, pkey = world.sensors.add("p1", "Battery monitor", "power", {"source_id": source.source_id, "meter": "battery",
                                                                     "unit": "%"})
    sensors.reading(world, _same, pkey, 87, now=NOW)
    assert [r.value for r in world.energy.energy_source_readings(source.source_id, "battery")] == [87]


def test_adding_a_sensor_needs_its_name_and_target(world):
    with pytest.raises(sensors.SensorError, match="Lab, Power or the Greenhouse"):
        world.sensors.add("p1", "x", "kitchen", {})
    with pytest.raises(sensors.SensorError, match="name"):
        world.sensors.add("p1", " ", "lab", {"series": "a"})
    with pytest.raises(sensors.SensorError, match="the series"):
        world.sensors.add("p1", "Probe", "lab", {})


def test_removing_a_sensor_stops_its_key_and_its_readings_stay(world):
    sensor, key = world.sensors.add("p1", "Probe", "lab", {"series": "temp"})
    sensors.reading(world, _same, key, 20, now=NOW)
    assert "its key stops working" in ACTION_TYPES["sensor.remove"].describe(world, {"sensor_id": sensor["id"]})
    ACTION_TYPES["sensor.remove"].execute(world, {"sensor_id": sensor["id"]})
    with pytest.raises(sensors.SensorError):
        sensors.reading(world, _same, key, 21, now=NOW + timedelta(minutes=5))
    assert len(world.data_logger.readings_for("temp")) == 1
    with pytest.raises(ActionError):
        ACTION_TYPES["sensor.remove"].describe(world, {"sensor_id": sensor["id"]})


def test_the_page_lists_only_the_persons_own_sensors(world):
    world.sensors.add("p1", "Mine", "lab", {"series": "a"})
    world.sensors.add("p2", "Theirs", "lab", {"series": "b"})
    page = sensors.screen(world, "p1")
    assert [s["name"] for s in page["sensors"]] == ["Mine"] and {a["id"] for a in page["apps"]} == set(sensors.TARGETS)
    assert sensors.screen(object(), "p1") == {"available": False, "sensors": []}
