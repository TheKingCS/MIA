"""The Toolbox on the web (DEC-0125, the design canvas's Toolbox, DEC-0113: core/web_toolbox.py, core/toolbox_calcs.py,
core/toolbox_actions.py and core/assistant_toolbox_actions.py): every calculator worked out in core, alarms set,
switched and deleted as actions, and the same answers by voice."""

from __future__ import annotations

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.assistant_actions import AssistantActionRegistry
from core.assistant_toolbox_actions import register_toolbox_actions
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.toolbox_actions import clock_time, repeat_word
from core.toolbox_calcs import board_feet, concrete_volume, ohms_law, si, solve
from core.unit_conversion import convert
from core.web_toolbox import calc, calculators, toolbox_page


@pytest.fixture
def home(tmp_path):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.alarms = AlarmManager(context, data_dir=tmp_path / "data")
    return context


def run(context, kind, **params):
    """Checks then runs an action kind, as the screen's approve does."""
    action = ACTION_TYPES[kind]
    return action.describe(context, params), action.execute(context, params)


def test_numbers_read_with_a_metric_prefix_and_ohms_law_takes_any_two():
    assert (si(0.0545454, "A"), si(1200, "Ω"), si(0.00047, "F"), si(0, "V"), si(12, "V")) == (
        "54.5 mA", "1.2 kΩ", "470 µF", "0 V", "12 V")
    r = ohms_law(volts=12, ohms=220)
    assert r["solved"] == "amps" and r["text"]["amps"] == "54.5 mA" and r["text"]["watts"] == "655 mW"
    assert ohms_law(amps=2, ohms=5)["volts"] == 10 and ohms_law(volts=10, amps=2)["ohms"] == 5
    for bad in ({"volts": 1}, {"volts": 1, "amps": 2, "ohms": 3}, {"volts": 5, "ohms": 0}):
        with pytest.raises(ValueError):
            ohms_law(**bad)
    assert solve("voltage", None, 2.0, 5.0) == 10.0  # the Qt calculator's solve, now in core


def test_board_feet_and_concrete_are_worked_out_with_the_extra():
    assert board_feet(2, 6, 8, 10) == {"each": 8.0, "total": 80.0, "text": "80 board feet (8 each)"}
    c = concrete_volume(10, 10, 4)
    assert (c["cubic_yd"], c["bags_80"], c["bags_60"]) == (1.36, 62, 82) and "ready-mix" in c["note"]
    with pytest.raises(ValueError):
        board_feet(2, 0, 8)
    assert round(convert("Volume", "US Gallons (gal)", "Liters (L)", 5), 3) == 18.927


def test_every_calculator_works_its_own_example_and_says_what_went_wrong():
    for c in calculators():
        answer = calc(c["id"], c["example"])
        assert "error" not in answer and answer["answer"], c["id"]
    assert calc("ohms_law", {"volts": "12", "ohms": "220"})["answer"] == "Current: 54.5 mA"
    assert calc("unit_converter", {"category": "Temperature", "value": "100", "from_unit": "Celsius (°C)",
                                   "to_unit": "Fahrenheit (°F)"})["answer"] == "100 °C = 212 °F"
    assert calc("ohms_law", {"volts": "12"}) == {"error": "Give any two of volts, current and resistance."}
    assert calc("board_feet", {"thickness_in": "two", "width_in": "6", "length_ft": "8"}) == {"error": "two isn't a number."}
    assert calc("unit_converter", {"category": "Length", "from_unit": "Celsius (°C)", "to_unit": "Feet (ft)", "value": "1"})["error"]
    assert calc("nope", {}) == {"error": "There's no calculator by that name."}


def test_a_clock_time_is_read_any_common_way():
    assert [clock_time(t) for t in ("7", "7:30", "7:30 pm", "730am", "19:05", "12 am", "12:15 p.m.")] == [
        "07:00", "07:30", "19:30", "07:30", "19:05", "00:00", "12:15"]
    for bad in ("25:00", "13 pm", "soon", "7:75"):
        with pytest.raises(ValueError):
            clock_time(bad)
    assert (repeat_word([]), repeat_word([5, 6]), repeat_word([0, 2])) == ("Once", "Weekends", "Mon, Wed")


def test_alarms_are_set_switched_and_deleted_as_actions_and_by_voice(home):
    said, done = run(home, "alarm.add", label="Wake up", time="6:30 am", repeat="Weekdays")
    assert said == "Set an alarm “Wake up” for 06:30, weekdays" and done == "Alarm “Wake up” set for 06:30."
    with pytest.raises(ActionError):
        run(home, "alarm.add", time="later")
    page = toolbox_page(home)
    alarm = page["alarms"][0]
    assert (alarm["time"], alarm["repeat"], alarm["on"], page["alarms_on"]) == ("06:30", "Weekdays", True, 1)
    registry = AssistantActionRegistry()
    register_toolbox_actions(registry)
    assert registry._actions["switch_alarm"].handler(home, {"label": "wake", "on": "no"}) == "“Wake up” is off."
    assert toolbox_page(home)["alarms_on"] == 0
    assert "80 board feet" in registry._actions["calculate_board_feet"].handler(home, {"thickness_in": 2, "width_in": 6,
                                                                                  "length_ft": 8, "count": 10})
    assert registry._actions["calculate_concrete"].handler(home, {"length_ft": 10, "width_ft": 10}).startswith("1.36 cu yd")
    run(home, "alarm.delete", alarm_id=alarm["id"])
    assert toolbox_page(home)["alarms"] == []
