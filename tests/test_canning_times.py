"""
tests.test_canning_times
==========================

"How long do I process quarts of green beans?" (core/canning_times.py): the USDA's pressure-canning minutes with the
pressure for his altitude (weighted 10 or 15 lb, a dial gauge by thousands of feet), the boiling-water minutes by each
food's own altitude column, his altitude from his words or his town's elevation, and a food not in the table never
given a time.
"""

from core import canning_times as ct
from core import weather


def test_the_pressure_by_altitude_and_the_water_bath_columns():
    """Weighted 10 lb to 1,000 ft then 15; dial 11 to 2,000, 12 to 4,000; water-bath bands at each boundary; chicken
    stock is stock, never chicken; a follow-up's food, named first, is the one read; a bare number is feet."""
    assert ct.pressure_for(800) == (10, 11) and ct.pressure_for(1500) == (15, 11)
    assert ct.pressure_for(3500) == (15, 12) and ct.pressure_for(9000) == (15, None)
    assert [ct.band(f) for f in (1000, 1001, 3000, 3001, 6000, 6001)] == [0, 1, 1, 2, 2, 3]
    assert ct.feet_in("we're at 1,200 feet") == 1200 and round(ct.feet_in("800 m")) == 2625
    assert ct.feet_in("chicken, pints, 1500") == 1500 and ct.feet_in("7 quarts of beans") is None
    assert ct.feet_in("process 90 minutes") is None
    assert ct.food_in("pints of chicken stock") == ("pressure", "stock")
    assert ct.food_in("And what about corn? (after: How long for quarts of green beans?)") == ("pressure", "corn")
    assert ct.food_in("quarts of chicken") == ("pressure", "chicken")


def test_green_beans_at_his_towns_elevation(monkeypatch):
    """Quarts of green beans at a town 180 m up (590 ft): 25 minutes at 10 lb weighted or 11 lb dial."""
    monkeypatch.setattr(weather, "card", lambda context: {"elevation": 180, "place": "Springfield"})
    said = ct.say(None, "how long do I process quarts of green beans?")
    assert "25 minutes for quarts and 20 for pints" in said
    assert "10 lb on a weighted gauge, or 11 lb on a dial gauge" in said
    assert "Springfield's elevation" in said and "Vent the canner 10 minutes" in said


def test_tomatoes_by_the_altitude_said_and_fish_pints_only(monkeypatch):
    """Crushed tomatoes at 2,500 ft: 50 minutes for quarts, then pints' 40; trout in quarts: not tested; no altitude:
    the pressures; catfish, a lean fish the USDA hasn't tested, gets no time."""
    monkeypatch.setattr(weather, "card", lambda context: {})
    said = ct.say(None, "water bath time for quarts of crushed tomatoes at 2500 feet")
    assert said.index("50 minutes for quarts") < said.index("40 minutes for pints") and "1,001 to 3,000 ft" in said
    fish = ct.say(None, "how long to pressure can quarts of trout")
    assert "pints only" in fish and "Tell me your elevation" in fish
    assert "never guess a time" in ct.say(None, "how long do I pressure can catfish?")  # lean fish: not tested


def test_a_food_not_in_the_table_is_never_given_a_time(monkeypatch):
    """Salsa: pointed to a tested recipe, no minutes said."""
    monkeypatch.setattr(weather, "card", lambda context: {})
    said = ct.say(None, "how long do I process salsa?")
    assert "never guess a time" in said and "minutes" not in said
