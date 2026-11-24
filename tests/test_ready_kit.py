"""
tests.test_ready_kit
======================

The 72-hour kit (core/ready_kit.py): Ready.gov's basic kit checked against his inventory and pantry by whole words
(a headlamp is a light; a propane torch and maple syrup are nothing), water and food against three days, what isn't
in his records said as that, and what only he can check.
"""

from types import SimpleNamespace

from core import ready_kit as rk


def test_whole_words_name_the_kits_things():
    got = rk.check(["Headlamp", "Duct tape", "Maple syrup", "Ferro rod", "AA batteries"], 4, 1)
    have = {k for k, _s, _n in got["have"]}
    assert {"light", "sheeting", "fire", "batteries"} <= have and "maps" not in have
    assert got["short"] == ["food"]


def test_the_answer_counts_says_whats_not_in_his_records_and_what_only_he_can_check():
    inventory = SimpleNamespace(all_items=lambda: [SimpleNamespace(name="First aid kit", quantity=1),
                                                   SimpleNamespace(name="Weather radio", quantity=0)])
    said = rk.say(SimpleNamespace(inventory=inventory, kitchen=None, config=None), people=1)
    assert said.startswith(f"Of Ready.gov's basic emergency kit, your records hold 2 of {len(rk.KIT) + 2} things.")
    assert "Not in your inventory or pantry: a flashlight" in said and "water and food short" in said
    assert rk.ONLY_HE_CAN in said
