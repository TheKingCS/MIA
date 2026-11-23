"""
tests.test_preparedness
======================

How ready he is (core/preparedness.py, brainstorm 4.3): days of drinking water from his pantry at a gallon a person a
day against his target (the ways water is really stored: sized bottles, gallon jugs, ounces; never coconut water
or a filter), what expires soon, and what isn't counted yet, said plainly.
"""

from datetime import date
from types import SimpleNamespace

from core import preparedness as rd

TODAY = date(2026, 11, 23)


def _item(name, qty, unit="", expires=""):
    return SimpleNamespace(name=name, quantity=qty, unit=unit, expiration_date=expires)


def test_water_is_read_in_gallons_liters_and_sized_bottles():
    assert rd.gallons_of(_item("Water", 10, "gallons")) == 10
    assert round(rd.gallons_of(_item("Drinking water", 20, "liters")), 2) == 5.28
    assert round(rd.gallons_of(_item("Water, 16.9 oz bottles", 24, "bottles")), 2) == 3.17
    assert rd.gallons_of(_item("Water", 24, "bottles")) is None  # no size: can't be counted
    assert rd.gallons_of(_item("Water chestnuts", 3, "cans")) is None
    assert rd.gallons_of(_item("Rice", 20, "lb")) is None


def test_days_are_for_the_people_he_says():
    days, unread = rd.water_days([_item("Water", 28, "gallons"), _item("Water", 6, "bottles")], 2)
    assert days == 14 and unread == ["Water"]


def test_what_expires_soon_comes_soonest_first():
    items = [_item("Milk", 1, expires="2026-11-25"), _item("Beans", 4, expires="2027-06-01"),
             _item("Yogurt", 2, expires="2026-11-24"), _item("Old", 1, expires="2026-11-01")]
    assert rd.rotate(items, TODAY) == [("Yogurt", date(2026, 11, 24)), ("Milk", date(2026, 11, 25))]


def test_say_gives_the_shortfall_and_what_isnt_counted(monkeypatch):
    monkeypatch.setattr(rd, "_setting", lambda context, key, default: default)
    kitchen = SimpleNamespace(all_pantry_items=lambda: [_item("Water", 5, "gallons"),
                                                        _item("Milk", 1, expires="2026-11-25")])
    said = rd.say(SimpleNamespace(kitchen=kitchen), TODAY)
    assert "about 5 days" in said and "9 days short of your 14-day target" in said and "Milk (Nov 25)" in said
    assert "Not counted yet: days of food" in said


def test_with_no_water_logged_she_says_how_much_the_target_takes(monkeypatch):
    monkeypatch.setattr(rd, "_setting", lambda context, key, default: default)
    said = rd.say(SimpleNamespace(kitchen=None), TODAY)
    assert "none logged" in said and "14 gallons" in said


def test_the_ways_water_is_really_stored_are_counted():
    assert round(rd.gallons_of(_item("Water", 24, "16.9 fl oz bottles")), 2) == 3.17
    assert rd.gallons_of(_item("Water", 4, "5-gallon jugs")) == 20
    assert rd.gallons_of(_item("Water 5 gal jug", 3, "")) == 15
    assert rd.gallons_of(_item("Water", 128, "oz")) == 1
    assert rd.gallons_of(_item("Water", 2, "gal.")) == 2


def test_water_that_isnt_for_drinking_is_left_out_and_never_asked_about():
    for name in ("Coconut water", "Tonic water", "Rose water", "Water filter cartridges", "Water bath canner"):
        assert rd.gallons_of(_item(name, 4, "liters")) is None, name
    days, unread = rd.water_days([_item("Water filter cartridges", 3, "packs"), _item("Water", 6, "bottles")], 1)
    assert unread == ["Water"]
