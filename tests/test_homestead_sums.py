"""
tests.test_homestead_sums
===========================

Three homestead sums worked out in code (core/homestead_sums.py; live sweep, 2026-11-25, each had been answered from
memory): water to store at a gallon a person a day for the days and people said (or his settings), a generator's
hours on the fuel said at his burn rate (or how to tell MIA his rate, never a typical figure as his), and the hens
for the eggs wanted, with the breeds' range and the winter allowance. Each is read only, takes his own words and is
said as it is.
"""

from core import homestead_sums as sums
from core.main_thread import changes_records
from core.tool_loop import SAID_AS_IS


def test_the_words_are_read_for_days_people_fuel_and_eggs():
    assert sums.days_in("for two weeks") == 14 and sums.days_in("3 days") == 3 and sums.days_in("a month") == 30
    assert sums.days_in("how much water?") is None
    assert sums.people_in("a family of 5") == 5 and sums.people_in("for 4 people") == 4
    assert sums.fuel_in("5 gallons")[0] == 5 and round(sums.fuel_in("20 lb of propane")[0], 2) == 4.72
    assert sums.eggs_wanted("a dozen eggs a week") == 12 and sums.eggs_wanted("2 eggs a day") == 14
    assert sums.eggs_wanted("two dozen eggs a week") == 24


def test_water_is_a_gallon_a_person_a_day():
    said = sums.water_to_store(None, "How much water for a family of 4 for 3 days?")
    assert said.startswith("Store 12 gallons: a gallon a person a day, for 4 people, for 3 days.")
    assert sums.water_to_store(None, "How much water should I store for two weeks?").startswith("Store 14 gallons")


def test_a_generator_without_its_burn_rate_is_asked_for_never_guessed(monkeypatch):
    said = sums.generator_runtime(None, "How long will my generator run on 5 gallons?")
    assert "I need your generator's burn rate" in said and "hours" not in said.split(":")[0]
    rates = {"prepared.generator_gph": 0.5, "prepared.generator_hours": 8}
    monkeypatch.setattr(sums, "_setting", lambda context, key, default: rates.get(key, default))
    assert sums.generator_runtime(None, "5 gallons").startswith("About 10.0 hours on 5 gallons")


def test_hens_for_a_dozen_a_week_with_the_breeds_range():
    said = sums.hens_for_eggs(None, "How many chickens do I need for a dozen eggs a week?")
    assert said.startswith("For 12 eggs a week, about 3 hens") and "winter" in said


def test_each_is_a_read_only_tool_said_as_it_is():
    for name in ("water_to_store", "generator_runtime", "hens_for_eggs"):
        assert not changes_records(name) and name in SAID_AS_IS
