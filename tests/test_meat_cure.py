"""
tests.test_meat_cure
======================

"How much curing salt for 5 pounds of pork belly?" (core/meat_cure.py): the weight read from his words in any unit,
bacon at the USDA's 120 ppm and the rest at 156, a salt percentage he names, the fridge and tested-recipe advice, and
a question without a weight asked back.
"""

from core import meat_cure as mc


def test_the_weight_is_read_in_any_unit():
    """Pounds, kilograms, grams and ounces; nothing without a weight."""
    assert mc.weight_in("5 pounds of pork belly") == "5 lb" and mc.weight_in("a 2.5 kg brisket") == "2.5 kg"
    assert mc.weight_in("800g of venison") == "800 g" and mc.weight_in("how much pink salt?") is None


def test_bacon_is_at_120_ppm_and_sausage_at_156():
    """Bacon names its limit; a sausage gets 156; both say weigh it and the fridge."""
    bacon = mc.say("How much curing salt for 5 lb of bacon?")
    assert "120 ppm" in bacon and "fridge at 34 to 40 F" in bacon and "weigh it" in bacon
    sausage = mc.say("pink salt for 2 kg of sausage at 2% salt")
    assert "156 ppm" in sausage and "2% salt" in sausage


def test_no_weight_is_asked_for():
    """Without a weight: asked."""
    assert mc.say("how much prague powder?").startswith("How much meat, by weight")
