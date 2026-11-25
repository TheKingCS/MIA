"""Question plans (DEC-0052 step 2a, core/question_plans.py): the right
plan for a question, lookups gathered by code onto a marked sheet, and an
answer that never states a number MIA didn't look up; and the weekend's
plan with each day's forecast, reached only by a weekend ahead; and the
winter plan with the days to the first frost; a tool's quoted example with a
number never reaches a sheet; a wet weekend day named for indoor work; and
quitting by a date he names worked out against the freedom fund; the homestead's
morning sheet; and the review's
cases (quoted names kept, estimate-only sheets worded, dates read as said, habits
and a winter gone kept out, the weekend winning a weekend for winter work).
A question a tool is built for (spending against his usual, what to make next, taxes to set aside, the coop's light,
who owes him) is never these plans'.
A thank-you is never a plan, a source label comes off, and the time plan keeps its own example."""

from datetime import date
from types import SimpleNamespace

import pytest

import core.meaning as meaning
from core import question_plans as qp
from core.llm_manager import ChatReply
from tests.test_crafting import shop  # noqa: F401  (the fixture)

TODAY = date(2026, 10, 30)


@pytest.fixture
def life(shop, monkeypatch):  # noqa: F811
    """The shop's world with the desktop's tools, and no embedding model (plans match by their own words)."""
    from tests.assistant_registry import build_desktop_registry

    shop.assistant_actions = build_desktop_registry()
    monkeypatch.setattr(meaning, "nearest", lambda *a, **k: None)  # no embedding model: the plans' own words
    return shop


class _Model:
    """A model that always says the same thing and remembers what it was asked."""
    def __init__(self, said):
        """Keeps what it will say; asked nothing yet."""
        self.said, self.asked = said, []

    def chat_with_tools(self, messages, tools):
        """Remembers the messages and answers with its line, calling no tool."""
        self.asked.append(messages)
        return ChatReply(content=self.said, tool_calls=[])


def test_only_questions_reach_a_plan(life):
    assert qp.match(life, "Which debt should I prioritize?").name == "debts"
    assert qp.match(life, "How much money came in and went out this month?").name == "money month"
    assert qp.match(life, "Add a debt called Truck Loan") is None  # a change, not a question
    assert qp.match(life, "How do I add a bill?") is None  # how-to: the help docs
    assert qp.match(life, "Thanks!") is None


def test_by_meaning_when_the_model_is_there(life, monkeypatch):
    monkeypatch.setattr(meaning, "nearest", lambda c, text, examples: ("debts", 0.79))
    assert qp.match(life, "when will I be out from under all this?").name == "debts"
    monkeypatch.setattr(meaning, "nearest", lambda c, text, examples: ("today", 0.60))  # too far: not a plan
    assert qp.match(life, "How are you?") is None


def test_debts_sheet_has_the_payoff_math(life):
    life.budget.add_debt(name="Card", balance=3000, interest_rate=20, minimum_payment=90)
    life.budget.add_debt(name="Truck", balance=8000, interest_rate=6, minimum_payment=250)
    sheet = qp.gather(life, qp.PLAN_BY_NAME["debts"], "What if I put an extra $300 toward my debts?", TODAY)
    kinds = [f.kind for f in sheet.facts]
    assert "list_debts" in sheet.looked_up and qp.CALCULATION in kinds
    text = sheet.as_text()
    assert "At the minimums" in text and "$300.00 more a month to Card first" in text


def test_money_month_counts_in_code(life):
    life.budget.add_income(amount=2000, category="Salary", description="Pay", date="2026-10-15")
    life.budget.add_expense(amount=150, category="Groceries", description="Food", date="2026-10-20")
    sheet = qp.gather(life, qp.PLAN_BY_NAME["money month"], "Where is my money going?", TODAY)
    text = sheet.as_text()
    assert "$2,000.00 came in, $150.00 went out, net $1,850.00" in text and "Groceries $150.00" in text
    assert "entered by hand" in text


def test_an_invented_number_falls_back_to_the_sheet(life):
    life.budget.add_debt(name="Card", balance=3000, interest_rate=20, minimum_payment=90)
    life.llm = _Model("Pay off Card first; it'll take 41 months and $1,234.56 of interest.")
    conversation = SimpleNamespace(messages=[], mode=None)
    said, sheet = qp.answer(life, conversation, "Which debt should I prioritize?", TODAY)
    assert said == sheet.plain() and "1234.56" not in said  # the model's made-up number never reaches the person
    system = life.llm.asked[0][0]["content"]
    assert "Fact sheet" in system and "[calculation" in system


def test_numbers_and_the_sheet_in_plain_words():
    assert qp.numbers_in("$1,200.00 and 3.50") == {"1200", "3.5"}
    assert qp.invented_numbers("You have 3 bills: $45.10.", "- [fact] Electric $45.10", "") == set()
    assert qp.invented_numbers("About $99 left.", "- [fact] Electric $45.10", "") == {"99"}
    assert qp._amount_in("my next $1,000") == 1000 and qp._amount_in("an extra 200 dollars") == 200
    sheet = qp.Sheet("x", "X")
    sheet.add(qp.FACT, "Electric is due Friday.")
    sheet.add(qp.MISSING, "No pay rate in the Dungeon.")
    assert sheet.plain() == "Electric is due Friday. Not recorded yet: No pay rate in the Dungeon."


def test_every_plan_gathers_without_failing(life):
    for plan in qp.PLANS:
        sheet = qp.gather(life, plan, plan.examples[0], TODAY)
        assert sheet.facts, plan.name  # something, even if it's "missing"


def test_personal_modes_stay_a_conversation(life):
    talk = SimpleNamespace(messages=[], mode="listen")
    assert qp.request(life, talk, "Which debt should I prioritize?") is None


def test_what_we_decided_also_looks_in_her_own_decision_record_and_says_whose_it_is(life, monkeypatch):
    looked = []
    monkeypatch.setattr(qp, "_look", lambda context, sheet, tool, source, said_as="", **kept:
                        looked.append((tool, said_as)) or "")
    qp._recall(life, qp.Sheet("recall", "Recall"), "What did we decide about eggs?", TODAY)
    assert any(tool == "get_mia_docs" and "your own decision record" in said for tool, said in looked)
    looked.clear()
    qp._recall(life, qp.Sheet("recall", "Recall"), "What did I decide about the truck?", TODAY)
    assert not any(tool == "get_mia_docs" for tool, _ in looked)


def test_the_weekend_is_this_saturday_and_sunday_or_what_is_left_of_it_or_next_or_one_day_named():
    assert qp.weekend_days(date(2026, 11, 24)) == [date(2026, 11, 28), date(2026, 11, 29)]  # a Tuesday
    assert qp.weekend_days(date(2026, 11, 28)) == [date(2026, 11, 28), date(2026, 11, 29)]  # Saturday
    assert qp.weekend_days(date(2026, 11, 29)) == [date(2026, 11, 29)]  # Sunday
    assert qp.weekend_days(date(2026, 11, 24), "next weekend?") == [date(2026, 12, 5), date(2026, 12, 6)]
    assert qp.weekend_days(date(2026, 11, 28), "what about next weekend") == [date(2026, 12, 5), date(2026, 12, 6)]
    assert qp.weekend_days(date(2026, 11, 29), "how should I spend Saturday?") == [date(2026, 12, 5)]


@pytest.mark.parametrize("said, plan", [
    ("how was my weekend?", None), ("how did the weekend go?", None), ("what did I do this weekend?", None),
    ("is the store open on sunday?", None), ("what's for dinner on sunday?", None),
    ("what should I do saturday?", "weekend"), ("what are my plans saturday?", "weekend"),
    ("what should I do next weekend?", "weekend"), ("how should I spend Sunday?", "weekend"),
])
def test_only_a_weekend_ahead_reaches_its_plan(life, said, plan):
    found = qp.match(life, said)
    assert (found.name if found else None) in ((plan,) if plan else (None, "week review", "recall", "discussed")), said
    if plan is None:
        assert found is None or found.name != "weekend", said


def test_asking_about_the_weekend_reaches_its_plan_with_each_days_forecast_and_one_day_compares_nothing(life, monkeypatch):
    from core import weather

    assert qp.match(life, "What should I do this weekend?").name == "weekend"
    assert qp.match(life, "How did my week go?").name == "week review"
    monkeypatch.setattr(weather, "card", lambda c: {"place": "Town", "unit": "°F", "days": [
        {"date": "2026-11-28", "high": 52, "low": 31, "words": "Clear", "rain": 5}]})
    text = qp.gather(life, qp.PLAN_BY_NAME["weekend"], "What should I do this weekend?", date(2026, 11, 24)).as_text()
    assert "Saturday: Clear, high 52°F, low 31°F, 5% chance of rain." in text
    assert "No forecast for Sunday yet." in text and "suits the drier" not in text  # one day: nothing to compare


def test_a_forecast_carries_each_whole_day_by_its_date():
    from core.weather import read

    raw = {"current": {"temperature_2m": 50, "weather_code": 0},
           "daily": {"time": ["2026-11-24", "2026-11-25", "2026-11-26"], "temperature_2m_max": [55, 57, None],
                     "temperature_2m_min": [40, 41, 39], "weather_code": [0, 3, 61],
                     "precipitation_probability_max": [0, 10, 80]}}
    days = read(raw, "fahrenheit")["days"]
    assert [d["date"] for d in days] == ["2026-11-24", "2026-11-25"]  # the gap day left out
    assert days[1]["rain"] == 10


def test_am_i_ready_for_winter_gathers_the_frost_firewood_preparedness_and_the_rest(life):
    life.config.set("garden.first_frost", "October 20")
    assert qp.match(life, "Am I ready for winter?").name == "winter"
    assert qp.match(life, "What's left to winterize?").name == "winter"
    sheet = qp.gather(life, qp.PLAN_BY_NAME["winter"], "Am I ready for winter?", date(2026, 9, 30))
    text = sheet.as_text()
    assert "first fall frost is about October 20, 20 days from today" in text
    assert {"firewood_check", "how_prepared", "emergency_kit"} <= set(sheet.looked_up)
    assert "drain and store hoses" in text
    messages, _ = qp.request(life, None, "Am I ready for winter?", date(2026, 9, 30))
    assert messages[0]["content"].rstrip().endswith(qp.HOW["winter"])


def test_a_quoted_example_with_a_number_never_reaches_a_sheet_as_his_record():
    said = qp.without_examples('How many cords does a winter take you? Tell me yours ("I burn 4 cords a winter") and '
                               "I'll keep count. Log water like \"water, 10 gallons\". Say \"let's plan it\".")
    assert "4 cords" not in said and "10 gallons" not in said
    assert "Tell me yours and I'll keep count." in said and "Say \"let's plan it\"." in said  # no number: kept


def test_a_wet_weekend_day_is_named_for_indoor_work(life, monkeypatch):
    from core import weather

    assert qp.is_wet({"rain": 70, "words": "Overcast"}) and qp.is_wet({"rain": None, "words": "Light rain"})
    assert not qp.is_wet({"rain": 20, "words": "Partly cloudy"})
    monkeypatch.setattr(weather, "card", lambda c: {"place": "Town", "unit": "°F", "days": [
        {"date": "2026-11-28", "high": 52, "low": 31, "words": "Clear", "rain": 5},
        {"date": "2026-11-29", "high": 45, "low": 38, "words": "Rain", "rain": 80}]})
    text = qp.gather(life, qp.PLAN_BY_NAME["weekend"], "What should I do this weekend?", date(2026, 11, 24)).as_text()
    assert "Sunday looks wet: a day for indoor work." in text and "A wet day suits" in text


def test_a_quit_date_is_read_from_how_he_says_it():
    from core.freedom import quit_date

    today = date(2026, 11, 24)
    assert quit_date("what if I quit at the end of next year?", today) == date(2027, 12, 31)
    assert quit_date("could I leave my job in 18 months", today) == date(2028, 5, 24)
    assert quit_date("quit by June", today) == date(2027, 6, 30)
    assert quit_date("quit by June 2028", today) == date(2028, 6, 30)
    assert quit_date("can I quit?", today) is None


def test_quitting_by_a_date_says_the_shortfall_what_more_a_month_closes_it_and_how_long_it_lasts_builds_aside():
    from core.freedom import Inputs, quit_by

    r = quit_by(Inputs(needs=3000, homestead=1000, saved=5000, pace=500, cushion_months=6, builds_left=2000),
                date(2027, 11, 24), date(2026, 11, 24))
    assert r["gap"] == 2000 and r["goal"] == 14000 and 10_900 < r["by_then"] < 11_100
    assert 2900 < r["short"] < 3100 and 240 < r["more_a_month"] < 260 and 4 < r["lasts_months"] < 5  # builds aside


def test_what_if_i_quit_at_the_end_of_next_year_reaches_its_plan(life):
    assert qp.match(life, "What if I quit at the end of next year?").name == "quit by"


def test_a_sheet_with_only_whats_missing_is_said_as_it_is_never_filled_in_by_the_model():
    sheet = qp.Sheet("quit by", "Quitting by a date")
    sheet.add(qp.MISSING, "The freedom fund couldn't be read.", "Freedom")
    said = qp.finish("You'll have saved about 2 months' worth, carrying you 2 to 3 months.", sheet, "what if I quit?")
    assert "2 months" not in said and "freedom fund couldn't be read" in said


def test_review_quoted_names_and_prices_stay_and_only_led_in_examples_go():
    assert qp.without_examples('Your order "Sign 2" is due.') == 'Your order "Sign 2" is due.'
    assert qp.without_examples('Priced at "$45" each.') == 'Priced at "$45" each.'
    assert "4 cords" not in qp.without_examples('Tell me yours ("I burn 4 cords a winter").')


def test_review_an_estimate_only_sheet_keeps_the_models_answer():
    sheet = qp.Sheet("winter", "Ready for winter")
    sheet.add(qp.ESTIMATE, "Most homesteads want about 3 cords.", "general guidance")
    sheet.add(qp.MISSING, "No firewood logged.", "firewood")
    assert qp.finish("About 3 cords is usual; log yours.", sheet, "how much firewood?") == "About 3 cords is usual; log yours."


def test_review_quit_dates_read_as_said():
    from core.freedom import quit_date

    today = date(2026, 11, 24)
    assert quit_date("quit by november", today) == date(2026, 11, 30)
    assert quit_date("quit by the end of the year", today) == date(2026, 12, 31)
    assert quit_date("quit by june next year", date(2026, 3, 1)) == date(2027, 6, 30)


@pytest.mark.parametrize("said", ["should I quit smoking by next year?", "I want to quit my gym by June?",
                                  "can I quit drinking before Christmas?", "should I quit the band next month?",
                                  "how did we get through the winter last year?"])
def test_review_quitting_a_habit_or_a_winter_gone_isnt_those_plans(life, said):
    found = qp.match(life, said)
    assert found is None or found.name not in ("quit by", "winter"), said


def test_review_a_weekend_for_winter_work_is_the_weekends_and_a_dry_chance_isnt_wet(life):
    assert qp.match(life, "what should I get done this weekend to get ready for winter?").name == "weekend"
    assert not qp.is_wet({"rain": 10, "words": "Slight chance of rain"})
    assert qp.match(life, "I'm planning to build a greenhouse, how's that affect my water?").name == "project picture"


def test_hows_the_homestead_gathers_every_part_and_says_the_greenhouse_unwatched(life):
    assert qp.match(life, "How's the homestead?").name == "homestead"
    sheet = qp.gather(life, qp.PLAN_BY_NAME["homestead"], "How's the homestead?", date(2026, 11, 24))
    assert "isn't watching the greenhouse yet" in sheet.as_text()
    assert {"garden_this_week", "orchard_this_month", "water_budget", "power_picture"} <= set(sheet.looked_up)
    messages, _ = qp.request(life, None, "How's the homestead?", date(2026, 11, 24))
    assert messages[0]["content"].rstrip().endswith(qp.HOW["homestead"])



@pytest.mark.parametrize("said,plan", [("Am I spending more than usual?", "time"),
                                       ("What should I make next for the shop?", "progress"),
                                       ("How much should I set aside for taxes?", "next dollar"),
                                       ("Should I add a light in the coop?", "project picture"),
                                       ("Who owes me money?", "debts"),
                                       ("How prepared am I for an emergency?", "coming up"),
                                       ("How much rent did I collect this month?", "money month"),
                                       ("What's still unpaid?", "open loops"),
                                       ("What can you help me with on the homestead?", "homestead"),
                                       ("What's my water budget?", "money month"),
                                       ("What should I practice on guitar today?", "today"),
                                       ("How much firewood do I need for winter?", "winter"),
                                       ("What's coming up on the truck?", "discussed")])
def test_a_question_a_tool_is_built_for_isnt_these_plans(said, plan):
    """Each went to the plan by meaning in the live check; its words now give it to its tool (a tax refund stays the
    next dollar's)."""
    assert qp._not_for(plan, said), said

    assert not qp._not_for("next dollar", "where should my tax refund go?")



def test_the_time_plans_own_example_is_still_its():
    """"What am I spending too much time on?" is the time plan's (review 2026-11-24), "am I spending more than usual?"
    isn't."""
    assert not qp._not_for("time", "What am I spending too much time on?")
    assert qp._not_for("time", "Am I spending more than usual?")



def test_a_thank_you_is_never_a_plan_and_a_source_label_comes_off_an_answer():
    """"Thanks, that's good to know" reaches no plan; "Dungeon. I don't have..." loses its label; an answer that
    only begins with a word like it keeps it."""
    assert qp.match_scored(None, "Thanks, that's good to know") is None
    sheet = qp.Sheet("x", "x")
    sheet.add(qp.FACT, "No pay rate.", "the Dungeon (their job)")
    assert qp.without_source_label("Dungeon. I don't have your income.", sheet) == "I don't have your income."
    assert qp.without_source_label("Dungeon\nYou're welcome.", sheet) == "You're welcome."
    assert qp.without_source_label("Dungeons are fun.", sheet) == "Dungeons are fun."
    assert qp.without_source_label("Dungeon\nThe fact sheet...", qp.Sheet("x", "x")) == "The fact sheet..."
    assert qp._not_for("project picture", "How many solar panels would I need? We use 900 kWh a month")
