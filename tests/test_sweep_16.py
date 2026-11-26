"""
tests.test_sweep_16
=====================

The tenth live sweep's fixes (2026-11-25): a unit conversion and a holiday's date are worked out in code (the model
had said "The conversion is complete." and "I don't have that information"); "I don't know what that means" before
a real answer goes; "do you remember what I told you yesterday?" is his past conversations, never one person. The
coming week's holidays, which the morning briefing names. The Fable review's: each route takes only its own; and
Fable's check of that narrowing: what it had refused is answered again. Pricing a thing he hasn't recorded
gets the way to price it, never his plywood.
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


def test_the_coming_weeks_holidays():
    """The holidays in the next days, his country's only, one name a day."""
    assert holidays.coming("US", date(2026, 11, 25), 3) == [("Thanksgiving", date(2026, 11, 26))]
    assert holidays.coming("CA", date(2026, 11, 25), 3) == []
    assert holidays.coming("US", date(2026, 12, 23), 3)[:2] == [("Christmas Eve", date(2026, 12, 24)),
                                                                 ("Christmas", date(2026, 12, 25))]
    assert holidays.coming_line(None, date(2026, 11, 25), 3) == "Thanksgiving is tomorrow."


def test_the_fable_reviews_routes_take_only_their_own(monkeypatch):
    """Holidays only the holiday itself, conversions right, home trouble only a water pipe happening now."""
    from core import holidays, home_trouble

    today = date(2026, 11, 25)
    assert holidays.reply(None, "when is new year's eve", today=today).startswith("New Year's Eve is Thursday")
    assert holidays.reply(None, "When is Thanksgiving in Canada?", today=today).startswith(
        "Thanksgiving is Monday, October 11, 2027")
    for words in ("when is easter monday", "when is orthodox easter", "when is the christmas concert",
                  "when is my labor day party", "when does the halloween store open",
                  "when should i start the easter ham", "when did we last talk about christmas"):
        assert holidays.reply(None, words, today=today) is None, words
    assert holidays.reply(None, "when was easter this year", today=today).startswith("Easter was")
    for words in ("a power line is broken in my yard", "my brake line broke", "the house is flooded with light",
                  "how much does it cost to fix a burst pipe", "the pipe is frozen yogurt",
                  "remind me to call the plumber about the burst pipe"):
        assert home_trouble.reply(words) is None, words
    assert home_trouble.reply("the basements full of water").startswith("If water")
    for words in ("whens the best time to fish for compliments", "add note: best time to fish is dawn",
                  "what is the best time to go fishing in florida"):
        assert assistant_turn._fish_when_reply(None, words) is None, words
    assert assistant_turn._mains_reply(None, "read me the current breaker list") is None
    assert assistant_turn._monthly_reminder_reply(None, "remind me that the meeting is monthly") is None


def test_fable_checks_the_narrowings_losses_are_back():
    """What 855b6b57's narrowing had refused, answered again; and a division by zero said plainly."""
    from core import holidays, home_trouble
    from core.assistant_tools import AssistantTools

    today = date(2026, 11, 25)
    for words in ("what day of the week is christmas?", "when is thanksgiving day", "when exactly is thanksgiving",
                  "when is thanksgiving again?", "when is memorial day weekend"):
        assert holidays.reply(None, words, today=today), words
    assert holidays.reply(None, "when was labor day", today=today).startswith("Labor Day was Monday, September 7, 2026")
    for words in ("water is coming through the ceiling", "the washing machine hose burst", "the well line broke",
                  "the kitchen line is frozen", "my water heater burst", "the toilet is overflowing",
                  "water is leaking through the ceiling",
                  "a pipe burst and the water is pouring out, what does a plumber cost"):
        assert home_trouble.reply(words), words
    for words in ("how do I check for power at the outlet", "how do I measure voltage at the breaker",
                  "how do I check voltage at the panel", "check power at the socket with a multimeter"):
        assert assistant_turn._mains_reply(None, words) == assistant_turn.MAINS_REPLY, words
    assert assistant_turn._mains_reply(None, "check the voltage on my solar panel") is None
    said = AssistantTools._action_convert_units(None, {"value": 0, "from_unit": "mpg", "to_unit": "L/100km"})
    assert "divides by zero" in said or "=" in said


def test_pricing_a_thing_he_hasnt_recorded_never_lists_his_plywood():
    """"How do I price my firewood?": the way to price it, never the workshop's materials."""
    ran = []
    context = SimpleNamespace(products=SimpleNamespace(all_products=lambda: [SimpleNamespace(name="Cutting Board")]),
                              assistant_actions=SimpleNamespace(_actions={"list_products": 1, "get_build_costs": 1,
                                                                         "list_materials": 1},
                                                                execute=lambda c, n, a: ran.append(n) or ""))
    sheet = question_plans.Sheet("product cost", "What one thing costs to make")
    question_plans._product_cost(context, sheet, "How do I price my firewood?", date.today())
    assert "list_materials" not in ran and "How to price one" in sheet.as_text()
    ran.clear()
    question_plans._product_cost(context, sheet, "how much does it cost me to make a cutting board?", date.today())
    assert "list_materials" in ran
