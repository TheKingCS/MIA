"""
tests.test_preparedness
======================

How ready he is (core/preparedness.py, brainstorm 4.3): days of drinking water from his pantry at a gallon a person a
day against his target (the ways water is really stored: sized bottles, gallon jugs, ounces; never coconut water
or a filter), days of food from the staples by weight and their calories (whole words; nothing wet, canned or a drink), what expires soon, and what
isn't counted, said plainly.
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
    """Water against the target, what to use soon, food asked for when none is logged, and power asks for fuel when
    none is in his records."""
    monkeypatch.setattr(rd, "_setting", lambda context, key, default: default)
    kitchen = SimpleNamespace(all_pantry_items=lambda: [_item("Water", 5, "gallons"),
                                                        _item("Milk", 1, expires="2026-11-25")])
    said = rd.say(SimpleNamespace(kitchen=kitchen), TODAY)
    assert "about 5 days" in said and "9 days short of your 14-day target" in said and "Milk (Nov 25)" in said
    assert "Food: no staples logged by weight" in said and "Power: no fuel in your records" in said


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


def test_days_of_food_come_from_staples_by_weight_and_their_calories():
    items = [_item("White rice", 20, "lb"), _item("Pinto beans", 10, "lb"), _item("Flour", 2, "kg"),
             _item("Canned corn", 12, "cans"), _item("Mystery jar", 1, "lb"), _item("Water", 10, "gallons")]
    days, counted, uncounted = rd.food_days(items, 1)
    # (20 x 1656 + 10 x 1574 + 2 x 2.20462 x 1651) / 2000
    assert days == round((20 * 1656 + 10 * 1574 + 2 * 2.20462 * 1651) / 2000, 1)
    assert counted == ["White rice", "Pinto beans", "Flour"] and uncounted == ["Canned corn", "Mystery jar"]
    assert rd.food_days(items, 2)[0] == round((20 * 1656 + 10 * 1574 + 2 * 2.20462 * 1651) / 4000, 1)


def test_say_counts_the_food_and_names_what_it_couldnt(monkeypatch):
    monkeypatch.setattr(rd, "_setting", lambda context, key, default: default)
    kitchen = SimpleNamespace(all_pantry_items=lambda: [_item("Rice", 25, "lb"), _item("Canned soup", 6, "cans")])
    said = rd.say(SimpleNamespace(kitchen=kitchen), TODAY)
    assert "Food: about 20.7 days for you" in said and "Not counted: Canned soup" in said


def test_only_dry_staples_count_never_what_shares_a_word_with_one():
    for name in ("Collard greens", "Goat cheese", "Float", "Bean sprouts", "Green beans", "Oat milk", "Rice vinegar",
                 "Pasta sauce", "Chicken noodle soup", "Honeydew melon", "Sugar snap peas", "Coffee beans"):
        assert rd.food_days([_item(name, 1, "lb")], 1)[1] == [], name
    assert rd.food_days([_item("Rolled oats", 1, "lb"), _item("Rice flour", 1, "lb")], 1)[1] == \
        ["Rolled oats", "Rice flour"]
