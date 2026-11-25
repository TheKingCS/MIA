"""
tests.test_solar_size
=======================

"How many solar panels would I need?" (core/solar_size.py): from the kWh a month he says, else his meter's months,
else he's asked for the kWh; the essentials off-grid with two days of battery, typical ones said as typical; his sun
hours and panel size used, else 4 hours said as an assumption.
"""

from types import SimpleNamespace

from core import power_picture, solar_size, utility_bills


def test_the_house_from_his_kwh_or_asked_for_it(monkeypatch):
    """900 kWh a month at 5 sun hours with 350 W panels; nothing said and no meter: asked; a bare 900 kWh is a month."""
    monkeypatch.setattr(utility_bills, "kwh_used", lambda context, month: None)
    said = solar_size.say(SimpleNamespace(), "house", "we use 900 kWh a month, we get 5 peak sun hours, 350 watt panels")
    assert said.startswith("From the 900 kWh a month you said, at the 5 peak sun hours you gave:")
    assert "panels of 350 W" in said
    assert solar_size.say(SimpleNamespace(), "house").startswith("How much power does the house use?")
    assert solar_size.say(SimpleNamespace(), "house", "900 kWh").startswith("From the 900 kWh a month you said")


def test_the_meter_months_and_the_essentials(monkeypatch):
    """Three metered months of 912 kWh: 30 kWh a day; the essentials: two days of battery, typical said as typical."""
    monkeypatch.setattr(utility_bills, "kwh_used", lambda context, month: 912.0)
    assert solar_size.house_kwh_day(SimpleNamespace()) == (30.0, 3)
    said = solar_size.say(SimpleNamespace(), "house")
    assert "your meter's last 3 months" in said and "4 peak sun hours, an assumption" in said
    monkeypatch.setattr(power_picture, "loads", lambda context: (
        [{"name": "well pump", "watts": 1000, "hours": 1, "kwh_day": 1.0},
         {"name": "freezer", "watts": 80, "hours": 24, "kwh_day": 1.92}], False))
    backup = solar_size.say(SimpleNamespace(), "essentials")
    assert "typical homestead essentials (2.92 kWh a day" in backup and "For 2 days without sun" in backup



def test_whether_his_solar_is_enough_is_the_power_pictures_answer(monkeypatch):
    """"Do I have enough solar for the essentials?" brought here is answered by the power picture."""
    monkeypatch.setattr(power_picture, "say", lambda context: "the power picture")
    assert solar_size.say(SimpleNamespace(), "essentials", "Do I have enough solar for the essentials?") == \
        "the power picture"
    assert solar_size.say(SimpleNamespace(), "", "is my solar enough") == "the power picture"
    assert solar_size.say(SimpleNamespace(), "", "do I have enough panels for the freezer?") == "the power picture"
