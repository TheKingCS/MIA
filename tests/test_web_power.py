"""Power on the web (DEC-0125, the design canvas's Power, DEC-0113: core/web_power.py and core/power_actions.py):
energy sources with their latest reading per meter, a meter for a percent (amber when low), when it was logged,
and every change as an action; the device's battery when it has one."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import core.data_logger_manager as data_logger_manager_module
import core.energy_manager as energy_manager_module
from core.actions import ACTION_TYPES, ActionError
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.energy_manager import EnergyManager
from core.event_bus import EventBus
from core.web_power import ago, meter_of, power_page, reading_text

NOW = datetime(2026, 11, 7, 18, 0, 0)


@pytest.fixture
def home(tmp_path, monkeypatch):
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
    said = action.describe(context, params)
    return said, action.execute(context, params)


def test_readings_read_plainly_and_a_percent_is_a_meter():
    assert (reading_text(62, "%"), reading_text(3.8, "kWh"), reading_text(40, "")) == ("62%", "3.8 kWh", "40")
    assert meter_of(20, "%") == {"pct": 20, "tone": "attention"} and meter_of(62, "%")["tone"] == "ok"
    assert meter_of(3.8, "kWh") is None
    assert ago(NOW - timedelta(minutes=30), NOW) == "30 min ago" and ago(NOW - timedelta(days=1), NOW) == "yesterday"
    assert ago(NOW - timedelta(days=15), NOW) == "2 weeks ago" and ago(None, NOW) == ""


def test_a_source_is_added_read_and_shown_low_first(home):
    run(home, "energy_source.add", name="Propane tank", source_type="Propane")
    run(home, "energy_source.add", name="Generator fuel", source_type="Generator")
    propane, generator = sorted(home.energy.all_energy_sources(), key=lambda s: s.name, reverse=True)
    said, done = run(home, "energy.reading", source_id=propane.source_id, value="62", unit="%")
    assert said == "Log 62 % for Propane tank (Level)" and done == "Logged 62 % for Propane tank."
    run(home, "energy.reading", source_id=generator.source_id, value="20", unit="%")
    page = power_page(home)
    assert [s["name"] for s in page["sources"]] == ["Generator fuel", "Propane tank"]  # the low one needs you first
    gen = page["sources"][0]
    assert gen["needs_you"] and gen["meters"][0]["text"] == "20%" and gen["meters"][0]["meter"]["tone"] == "attention"
    with pytest.raises(ActionError):
        run(home, "energy.reading", source_id=propane.source_id, value="lots")
    run(home, "energy_source.delete", source_id=generator.source_id)
    assert [s["name"] for s in power_page(home)["sources"]] == ["Propane tank"]


def test_the_battery_when_the_device_has_one(home):
    assert power_page(home)["battery"] == {"available": False}
    home.power = SimpleNamespace(is_available=lambda: True,
                                 read=lambda: SimpleNamespace(percent=18.4, plugged_in=False, seconds_left=2700))
    b = power_page(home)["battery"]
    assert (b["percent"], b["minutes_left"], b["meter"]["tone"]) == (18, 45, "attention")
