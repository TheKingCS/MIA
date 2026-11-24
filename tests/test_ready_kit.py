"""
tests.test_ready_kit
======================

The 72-hour kit (core/ready_kit.py): Ready.gov's basic kit checked against his inventory and pantry by whole words
(a headlamp is a light; a car battery, Atlas mason jars, MAP-Pro gas and lighter fluid are nothing), its 14
basic things counted and the additional supplies said apart, water and food against three days (water whose size
can't be read said as that), what isn't in his records said as that, and what only he can check.
"""

from types import SimpleNamespace

from core import ready_kit as rk


def test_whole_words_name_the_kits_things():
    """A headlamp, duct tape, a ferro rod (an additional supply) and AA batteries count; maple syrup isn't a map."""
    got = rk.check(["Headlamp", "Duct tape", "Maple syrup", "Ferro rod", "AA batteries"], 4, 1)
    have = {k for k, _s, _n in got["have"] + got["extra_have"]}
    assert {"light", "sheeting", "fire", "batteries"} <= have and "maps" not in have
    assert got["short"] == ["food"]


def test_the_answer_counts_says_whats_not_in_his_records_and_what_only_he_can_check():
    inventory = SimpleNamespace(all_items=lambda: [SimpleNamespace(name="First aid kit", quantity=1),
                                                   SimpleNamespace(name="Weather radio", quantity=0)])
    said = rk.say(SimpleNamespace(inventory=inventory, kitchen=None, config=None), people=1)
    assert said.startswith(f"Of Ready.gov's basic emergency kit, your records hold 2 of {len(rk.KIT) + 2} things.")
    assert "Not in your inventory or pantry: a flashlight" in said and "water and food short" in said
    assert rk.ONLY_HE_CAN in said


def test_things_that_only_sound_like_the_kit_never_count():
    names = ["Car battery", "Atlas mason jars", "MAP-Pro gas cylinder", "Radio Flyer wagon", "Lighter fluid",
             "Electric can opener", "Tarp straps", "Battery bank"]
    got = rk.check(names, 0, 0)
    have = {k for k, _s, _n in got["have"] + got["extra_have"]}
    assert have == {"charger"}  # the battery bank, and only as the charger


def test_what_he_has_under_other_names_counts():
    names = ["Cable ties", "Firstaid kit", "Matchbox", "USB charger", "Vise grips"]
    got = rk.check(names, 0, 0)
    have = {k for k, _s, _n in got["have"] + got["extra_have"]}
    assert have == {"sanitation", "first_aid", "fire", "charger", "tools"}


def test_water_of_an_unread_size_is_never_said_as_none():
    kitchen = SimpleNamespace(all_pantry_items=lambda: [SimpleNamespace(
        name="Water bottles", quantity=24, unit="bottles", category="Beverages", expiration_date="", notes="")])
    said = rk.say(SimpleNamespace(inventory=None, kitchen=kitchen, config=None), people=1)
    assert "none logged" not in said.split("food")[0] and "couldn't read the size of" in said
    assert "of 14 things" in said
