"""
tests.test_power_ready
========================

Power in "how prepared am I?" (core/power_ready.py): fuel read from his records by whole word and size (gas cans,
propane by the pound; never a gas grill or a gas bill), days of running from his generator's burn rate and hours,
what to tell her without the rate, and set_preparedness keeping only what's in range.
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
    from core import person_settings
    from core.assistant_today_actions import _action_set_preparedness

    kept = {}
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: kept.__setitem__(key, value))
    said = _action_set_preparedness(None, {"people": 2, "generator_gph": 0.6, "generator_hours": 40,
                                           "generator_fuel": "propane"})
    assert kept == {"prepared.people": 2, "prepared.generator_gph": 0.6, "prepared.generator_fuel": "propane"}
    assert "Not set: generator hours should be 1 to 24" in said
