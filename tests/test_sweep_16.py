"""
tests.test_sweep_16
=====================

The tenth live sweep's fixes (2026-11-25): a unit conversion and a holiday's date are worked out in code (the model
had said "The conversion is complete." and "I don't have that information"); "I don't know what that means" before
a real answer goes; "do you remember what I told you yesterday?" is his past conversations, never one person.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, holidays, question_plans
from core.response_composer import polish


def test_holidays_fall_on_their_days():
    assert holidays.day_of("Thanksgiving (US)", 2026) == date(2026, 11, 26)
    assert holidays.day_of("Thanksgiving (US)", 2027) == date(2027, 11, 25)
    assert holidays.day_of("Thanksgiving (Canada)", 2026) == date(2026, 10, 12)
    assert holidays.day_of("Easter", 2026) == date(2026, 4, 5)
    assert holidays.day_of("Easter", 2027) == date(2027, 3, 28)
    assert holidays.day_of("Memorial Day", 2026) == date(2026, 5, 25)
    assert holidays.day_of("Labor Day", 2026) == date(2026, 9, 7)
    assert holidays.day_of("Mother's Day", 2026) == date(2026, 5, 10)
    said = holidays.reply(None, "What day is Thanksgiving this year?", today=date(2026, 11, 25))
    assert said == "Thanksgiving is Thursday, November 26, 2026 (tomorrow)."
    assert holidays.reply(None, "when is christmas eve", today=date(2026, 11, 25)).startswith("Christmas Eve is Thursday")
    assert holidays.reply(None, "when is my dentist appointment?") is None


def test_a_conversion_is_worked_out():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(
        execute=lambda c, n, a: ran.append(a) or "5 gallons = 18.93 liters"))
    assert assistant_turn._convert_reply(context, "Convert 5 gallons to liters") == "5 gallons = 18.93 liters"
    assert ran[-1] == {"value": 5.0, "from_unit": "gallons", "to_unit": "liters"}
    assistant_turn._convert_reply(context, "how many cups in a gallon?")
    assert ran[-1] == {"value": 1.0, "from_unit": "gallon", "to_unit": "cups"}
    assert assistant_turn._convert_reply(context, "convert my garage into a workshop") is None


def test_i_dont_know_before_an_answer_goes():
    said = polish("Honestly, I don't know what that means. But making a good first impression is about being prepared "
                  "and showing genuine interest.")
    assert said.startswith("Making a good first impression")
    assert polish("I don't know what that means.") == "I don't know what that means."


def test_what_he_told_her_before_is_never_one_person():
    assert question_plans._not_for("person", "Do you remember what I told you yesterday?")
