"""
tests.test_bleach_for_water
=============================

How much bleach makes water safe to drink, by voice (bleach_for_water): the EPA's dose worked out in code
(core/eng_calcs.py), the water read in gallons, liters or quarts, the strength when he says it, both common strengths
when he doesn't, a strength that isn't for drinking water refused, and "how much water?" asked when he gives none.
"""

from core.assistant_today_actions import _action_bleach_for_water as bleach


def test_a_said_strength_gets_its_own_dose():
    said = bleach(None, {"question": "how much 8.25% bleach to purify 5 gallons of water"})
    assert "30 drops of 8.25% unscented bleach" in said and "EPA" in said


def test_no_strength_says_both_common_ones_to_check_the_label():
    said = bleach(None, {"question": "how much bleach for 2 gallons"})
    assert said.startswith("Check the label for the bleach's strength: for 6% it's 16 drops, for 8.25% it's 12.")


def test_quarts_and_liters_are_read():
    assert "for 6% it's 2 drops" in bleach(None, {"question": "how much bleach in 1 quart of water"})
    assert "drops" in bleach(None, {"question": "how much bleach for 10 liters"})


def test_no_water_is_asked_and_a_wrong_strength_is_refused():
    assert bleach(None, {"question": "how much bleach do I need"}) == "How much water: how many gallons or liters?"
    assert "4% to 8.25%" in bleach(None, {"question": "how much 12% bleach for 5 gallons"})
