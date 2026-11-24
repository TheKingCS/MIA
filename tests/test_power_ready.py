"""
tests.test_power_ready
========================

Power in "how prepared am I?" (core/power_ready.py): fuel read from his records by whole word and size (gas cans,
propane by the pound or a unit of pounds, quarts or liters; never a gas grill, a generator, a heater or diesel exhaust
fluid), none left skipped, days of running from his generator's burn rate and hours (less than a day said in hours),
fuel it can't measure never said as none, what to tell her without the rate, and set_preparedness keeping only
what's in range, with "gas" understood and a propane rate in pounds an hour turned to gallons.
"""

from types import SimpleNamespace

from core import power_ready as pr


def _item(name, quantity, unit=""):
    """A record with a name, a quantity and a unit."""
    return SimpleNamespace(name=name, quantity=quantity, unit=unit)


def test_fuel_is_read_by_word_and_size_and_nothing_else_is_fuel():
    found, unread = pr.fuel_on_hand([_item("Gas cans, 5 gal", 3), _item("Propane tank 20 lb", 2),
                                     _item("Gas grill", 1), _item("Off-road diesel", 10, "gallons"),
                                     _item("Kerosene", 2), _item("Gas mask", 1)])
    assert found == {"gasoline": 15.0, "propane": round(40 / pr.PROPANE_LB_A_GALLON, 2), "diesel": 10.0}
    assert unread == ["Kerosene"]


def test_days_of_running_come_from_his_rate_and_hours(monkeypatch):
    from core import person_settings

    kept = {"prepared.generator_gph": 0.75, "prepared.generator_hours": 6}
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: kept.get(key, default))
    inventory = SimpleNamespace(all_items=lambda: [_item("Gas cans, 5 gal", 4)])
    said = pr.say(SimpleNamespace(inventory=inventory, kitchen=None))
    assert "runs about 4.4 days on the gasoline" in said  # 20 gal / (0.75 x 6)
    kept.pop("prepared.generator_gph")
    assert "Tell me your generator's burn rate" in pr.say(SimpleNamespace(inventory=inventory, kitchen=None))


def test_set_preparedness_keeps_only_whats_in_range(monkeypatch):
    """Two people, 0.6 gallons an hour and propane are kept; 40 hours a day isn't, and is said by its name."""
    from core import person_settings
    from core.assistant_today_actions import _action_set_preparedness

    kept = {}
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: kept.__setitem__(key, value))
    said = _action_set_preparedness(None, {"people": 2, "generator_gph": 0.6, "generator_hours": 40,
                                           "generator_fuel": "propane"})
    assert kept == {"prepared.people": 2, "prepared.generator_gph": 0.6, "prepared.generator_fuel": "propane"}
    assert "Not set: generator hours a day should be 1 to 24" in said


def test_equipment_and_things_that_arent_fuel_never_count():
    names = ["Diesel exhaust fluid 2.5 gal", "Generac gas generator 6.6 gal tank", "Propane torch", "Propane heater",
             "Kerosene heater", "Gas siphon pump", "Gas line antifreeze", "Gas-powered weed eater", "K1 bulb"]
    found, unread = pr.fuel_on_hand([_item(n, 2) for n in names])
    assert found == {} and unread == []


def test_a_unit_of_pounds_quarts_or_liters_is_read_and_none_left_is_skipped():
    found, unread = pr.fuel_on_hand([_item("Propane tank", 20, "lb"), _item("Petrol", 10, "liters"),
                                     _item("Gas can 5 gal", 0)])
    assert found == {"propane": round(20 / pr.PROPANE_LB_A_GALLON, 2), "gasoline": 2.64} and unread == []


def test_a_little_fuel_is_less_than_a_day_and_unreadable_fuel_isnt_none(monkeypatch):
    from core import person_settings

    kept = {"prepared.generator_gph": 1, "prepared.generator_hours": 8}
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: kept.get(key, default))
    few = SimpleNamespace(inventory=SimpleNamespace(all_items=lambda: [_item("Gasoline", 0.5, "gallons")]), kitchen=None)
    assert "runs less than a day (about 0.5 hours of running)" in pr.say(few) and "at 1 gallon an hour" in pr.say(few)
    vague = SimpleNamespace(inventory=SimpleNamespace(all_items=lambda: [_item("Kerosene", 2)]), kitchen=None)
    said = pr.say(vague)
    assert "no amounts I can read: Kerosene" in said and "no fuel in your records" not in said


def test_gas_and_a_propane_rate_in_pounds_are_understood(monkeypatch):
    from core import person_settings
    from core.assistant_today_actions import _action_set_preparedness

    kept = {}
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: kept.__setitem__(key, value))
    assert "generator fuel gasoline" in _action_set_preparedness(None, {"generator_fuel": "gas"})
    _action_set_preparedness(None, {"generator_lb_per_hour": 2.12})
    assert kept["prepared.generator_gph"] == 0.5 and kept["prepared.generator_fuel"] == "propane"
    assert "generator gallons an hour isn't a number" in _action_set_preparedness(None, {"generator_gph": "lots"})
