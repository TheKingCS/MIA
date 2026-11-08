"""The Lab on the web (DEC-0125, the design canvas's Lab, DEC-0113: core/web_lab.py, core/lab_reading_actions.py and
core/assistant_lab_actions.py): the Data Logger's series as chips, one in full with plain numbers and a chart placed
by core, readings logged and deleted as actions, other apps' series read only (an upkeep task's sensor readings named by
its asset and task, linked from its row), and delete by voice."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import core.data_logger_manager as data_logger_manager_module
import core.energy_manager as energy_manager_module
from core.actions import ACTION_TYPES, ActionError
from core.app_context import AppContext
from core.assistant_actions import AssistantActionRegistry
from core.assistant_lab_actions import register_lab_actions
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager, Reading
from core.energy_manager import EnergyManager
from core.event_bus import EventBus
from core.web_lab import chart, lab_page, owner_of, resolve_series, stats

NOW = datetime(2026, 11, 7, 18, 0, 0)


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A context with the data logger and energy sources on temporary files."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr(energy_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(energy_manager_module, "_ENERGY_SOURCES_FILE", data_dir / "energy_sources.json")
    monkeypatch.setattr(data_logger_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(data_logger_manager_module, "_READINGS_FILE", data_dir / "data_logger_readings.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.data_logger = DataLoggerManager(context)
    context.energy = EnergyManager(context)
    return context


def run(context, kind, **params):
    """Checks then runs an action kind, as the screen's approve does."""
    action = ACTION_TYPES[kind]
    return action.describe(context, params), action.execute(context, params)


def reading(value, unit="%"):
    """A reading for the pure helpers."""
    return Reading("r", "s", value, unit)


def test_a_series_is_found_whatever_its_case_and_other_apps_series_are_known():
    assert resolve_series(["Soil Moisture"], " soil moisture ") == "Soil Moisture"
    assert resolve_series(["Soil Moisture"], "Tank pH") == "Tank pH"
    assert owner_of("energy_source_ab12_Level")[1] == "Power" and owner_of("maintenance_asset_x_Hours")[1] == "Garage"
    assert owner_of("Soil Moisture") is None


def test_plain_numbers_and_the_chart_points_come_from_core():
    rs = [reading(v) for v in (40, 30, 50, 45)]
    assert stats(rs) == {"latest": "45%", "low": "30%", "high": "50%", "average": "41.25%", "change": "+5%", "count": 4}
    assert stats([]) == {} and stats(rs[:1])["change"] == ""
    c = chart(rs)
    assert [(p["x"], p["y"]) for p in c["points"]] == [(0, 0.5), (0.3333, 0), (0.6667, 1), (1, 0.75)]
    assert (c["low"], c["high"]) == ("30%", "50%") and chart(rs[:1])["points"] == []


def test_readings_are_logged_and_deleted_and_the_newest_series_is_shown(home):
    said, done = run(home, "lab_reading.add", series="Soil moisture", value="42", unit="%")
    assert said == "Log 42 % to Soil moisture" and done == "Logged 42 % to Soil moisture."
    run(home, "lab_reading.add", series="SOIL MOISTURE", value="38", unit="%", note="before watering")
    assert home.data_logger.list_series() == ["Soil moisture"]  # one series, whatever the case
    with pytest.raises(ActionError):
        run(home, "lab_reading.add", series="Soil moisture", value="damp")
    with pytest.raises(ActionError):
        run(home, "lab_reading.add", series="", value="1")
    page = lab_page(home, now=NOW)
    chosen = page["chosen"]
    assert [s["name"] for s in page["series"]] == ["Soil moisture"] and chosen["own"]
    assert chosen["readings"][0]["text"] == "38%" and chosen["readings"][0]["note"] == "before watering"
    assert chosen["stats"]["change"] == "-4%" and len(chosen["chart"]["points"]) == 2
    run(home, "lab_reading.delete", reading_id=chosen["readings"][0]["id"])
    assert lab_page(home, now=NOW)["chosen"]["stats"]["count"] == 1


def test_another_apps_series_is_listed_apart_and_read_only(home):
    source = home.energy.add_energy_source("Propane tank", "Propane")
    home.energy.log_energy_reading(source.source_id, "Level", 62, "%", "")
    page = lab_page(home, now=NOW)
    assert page["series"] == [] and page["chosen"] is None
    other = page["other_series"][0]
    assert (other["name"], other["app"], other["page"]) == ("Propane tank · Level", "Power", "power.html")
    detail = lab_page(home, series=other["id"], now=NOW)["chosen"]
    assert not detail["own"] and detail["app"] == "Power"
    with pytest.raises(ActionError):
        run(home, "lab_reading.delete", reading_id=detail["readings"][0]["id"])
    with pytest.raises(ActionError):
        run(home, "lab_reading.add", series=other["id"], value="50")


def test_the_last_reading_is_deleted_by_voice(home):
    for i, v in enumerate((7.1, 6.9)):
        home.data_logger.add_reading("Tank pH", v, "pH", timestamp=(NOW - timedelta(days=2 - i)).isoformat())
    registry = AssistantActionRegistry()
    register_lab_actions(registry)
    tool = registry._actions["delete_lab_reading"].handler
    assert tool(home, {"series": "tank ph"}) == "Deleted the reading from Tank pH."
    assert [r.value for r in home.data_logger.readings_for("Tank pH")] == [7.1]
    assert tool(home, {"series": "Shop temp"}) == "There are no readings in 'Shop temp'."


def test_an_upkeep_tasks_sensor_readings_are_garages_named_by_asset_and_task():
    from types import SimpleNamespace

    from core.web_lab import _name, owner_of

    assert owner_of("maintenance_t1")[1] == "Garage" and owner_of("maintenance_asset_x_Hours")[0] == "maintenance_asset_"
    book = SimpleNamespace(get_task=lambda i: SimpleNamespace(asset_id="a1", title="Filter pressure") if i == "t1" else None,
                           get_asset=lambda i: SimpleNamespace(name="Furnace") if i == "a1" else None)
    context = SimpleNamespace(maintenance=book)
    assert _name(context, "maintenance_t1") == "Furnace · Filter pressure"
    assert _name(context, "maintenance_gone") == "Removed · Reading"


def test_a_sensor_tasks_row_links_to_its_chart_once_there_are_two_readings(home, tmp_path):
    from datetime import date

    from core.maintenance_manager import MaintenanceManager
    from core.web_equipment import _task_row

    home.maintenance = MaintenanceManager(home, data_dir=tmp_path / "upkeep")
    furnace = home.maintenance.add_asset("Furnace", "Appliance")
    task = home.maintenance.add_task(furnace.asset_id, "Filter pressure", trigger_type="sensor", meter_unit="inH2O",
                                     threshold_value=0.8, threshold_direction="above")
    assert _task_row(home, task, furnace, date.today())["series"] is None
    home.maintenance.log_reading(task.task_id, 0.4)
    home.maintenance.log_reading(task.task_id, 0.6)
    assert _task_row(home, task, furnace, date.today())["series"] == task.series_id
    assert any(r["name"] == "Furnace · Filter pressure" for r in lab_page(home)["other_series"])
