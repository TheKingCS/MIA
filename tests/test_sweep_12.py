"""
tests.test_sweep_12
=====================

The sixth live sweep's fixes (2026-11-25): "remind me tomorrow at 9 to call the vet" goes on his calendar like
"remind me to call the vet tomorrow at 9"; a tool call written out with a doubled quote before its key is caught;
what he spent on a category and "am I over budget?" are from his own records; a crop's dates and the 72-hour kit are hers.
The eighteenth review's: the day said first is the day, "at 3" the afternoon; a period it can't read, two things or
a verb after "start" are the model's; the animals' food is Animals & Feed.
The nineteenth's: morning in the task is no morning, a pet project no animal, spring peas a crop.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from core import assistant_turn
from core.llm_manager import _looks_like_malformed_tool_call


def test_the_day_said_first_is_still_a_reminder():
    added = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: added.append(a) or "ok"))
    assert assistant_turn._reminder_reply(context, "Remind me tomorrow at 9 to call the vet") == "ok"
    assert added[-1]["title"] == "Call the vet" and added[-1]["time"] == "09:00"
    assert assistant_turn._reminder_reply(context, "remind me tonight at 8, to take the trash out") == "ok"
    assert added[-1]["title"] == "Take the trash out" and added[-1]["time"] == "20:00"
    assert assistant_turn._reminder_reply(context, "remind me to call the vet") is None


def test_a_call_with_a_doubled_quote_is_caught():
    text = '{"name":"add_alarm",""parameters":{"label":"Call the vet", "time":"09:00"}}'
    assert _looks_like_malformed_tool_call(text)
    assert assistant_turn._garbled(text, SimpleNamespace(assistant_actions=SimpleNamespace(_actions={"add_alarm": 1})))


def test_what_he_spent_on_a_category_is_from_his_expenses():
    asked = []

    def totals(start, end):
        """This month's totals by category."""
        asked.append((start, end))
        return {"Groceries": 182.5}

    context = SimpleNamespace(budget=SimpleNamespace(total_expenses_by_category=totals))
    said = assistant_turn._spent_on_reply(context, "How much did I spend on groceries this month?")
    assert "182.50 on Groceries this month" in said
    assert assistant_turn._spent_on_reply(context, "how much have I spent on gas last month?") == \
        "Nothing logged under Transportation last month (" + (date.today().replace(day=1) - timedelta(days=1)).strftime("%B") + ")."
    assert asked[-1][1] < asked[0][0]  # last month ends before this month starts
    assert assistant_turn._spent_on_reply(context, "how much did I spend on my vacation?") is None


def test_over_budget_is_never_where_his_time_goes():
    from core import question_plans

    plan = question_plans.match(None, "Am I over budget anywhere?")
    assert plan is None or plan.name != "time"


def test_am_i_over_budget_is_his_budgets():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(n) or "Groceries: ..."))
    assert assistant_turn._spent_on_reply(context, "Am I over budget anywhere?") == "Groceries: ..."
    assert ran == ["budget_left"]
    assert assistant_turn._spent_on_reply(context, "am I over thinking this budget thing?") is None


def test_a_crops_dates_and_the_kit_are_hers(monkeypatch):
    from core import planting_now, ready_kit

    monkeypatch.setattr(planting_now, "say_crop", lambda c, said: f"dates for {said.strip()}")
    monkeypatch.setattr(ready_kit, "say", lambda c: "the kit")
    assert assistant_turn._garden_kit_reply(None, "When should I start my tomato seeds?") == "dates for my tomato seeds"
    assert assistant_turn._garden_kit_reply(None, "What should be in a 72 hour bag?") == "the kit"
    assert assistant_turn._garden_kit_reply(None, "check my go bag") == "the kit"
    for words in ("when should I start my workout?", "when should I start the business?", "what's in my bag?",
                  "the emergency kit is in the truck"):
        assert assistant_turn._garden_kit_reply(None, words) is None, words



def test_the_day_said_first_is_the_day_and_three_is_the_afternoon():
    from datetime import date, timedelta

    added = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: added.append(a) or "ok"))
    assistant_turn._reminder_reply(context, "remind me tonight to set an alarm for tomorrow")
    assert added[-1]["date"] == date.today().isoformat() and added[-1]["title"] == "Set an alarm for tomorrow"
    assistant_turn._reminder_reply(context, "remind me tomorrow at 3 to pick up the feed")
    assert added[-1]["date"] == (date.today() + timedelta(days=1)).isoformat() and added[-1]["time"] == "15:00"
    assistant_turn._reminder_reply(context, "remind me tomorrow morning at 5 to feed the hens")
    assert added[-1]["time"] == "05:00"


def test_spending_it_cant_read_is_the_models():
    """Two things at once are the model's; any period core/money_periods reads is answered (2026-11-26: "last week",
    "in October" and "yesterday" had been the model's)."""
    context = SimpleNamespace(budget=SimpleNamespace(total_expenses_by_category=lambda s, e: {"Animals & Feed": 30.0}))
    assert assistant_turn._spent_on_reply(context, "how much did I spend on gas and groceries?") is None
    for words in ("how much did I spend on gas last week?", "how much did I spend on gas in October?",
                  "how much did I spend on groceries yesterday?"):
        assert assistant_turn._spent_on_reply(context, words).startswith("Nothing logged under"), words
    for words in ("how much did I spend on chicken food?", "how much did I spend on food for the dogs?"):
        assert "Animals & Feed" in assistant_turn._spent_on_reply(context, words), words
    assert "so far" in assistant_turn._spent_on_reply(context, "how much have we spent on feed so far?")


def test_a_crop_word_or_a_kit_word_alone_is_no_garden_or_kit_question(monkeypatch):
    from core import planting_now, ready_kit

    monkeypatch.setattr(planting_now, "say_crop", lambda c, said: "dates")
    monkeypatch.setattr(ready_kit, "say", lambda c: "the kit")
    for words in ("when should I start selling tomatoes?", "when do I start canning tomatoes?",
                  "when can I start eating my lettuce?", "what should I name my emergency kit business",
                  "what should I do with my old emergency kit?", "what goes in a first aid kit?"):
        assert assistant_turn._garden_kit_reply(None, words) is None, words
    assert assistant_turn._garden_kit_reply(None, "when should I plant potatoes?") == "dates"
    assert assistant_turn._garden_kit_reply(None, "what should I pack in my go bag?") == "the kit"
    assert assistant_turn._garden_kit_reply(None, "what goes in a bug out bag?") == "the kit"


def test_the_nineteenth_reviews_three():
    """Morning in the task is no morning; a pet project is no animal; spring peas are a crop."""
    added = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: added.append(a) or "ok"))
    assistant_turn._reminder_reply(context, "remind me to check the morning glories saturday at 4")
    assert added[-1]["time"] == "16:00"
    book = SimpleNamespace(total_expenses_by_category=lambda s, e: {"Animals & Feed": 3.0})
    assert assistant_turn._spent_on_reply(SimpleNamespace(budget=book), "how much did I spend on my pet project?") is None
    assert assistant_turn._PLANT_WHEN.match("when should I start spring peas")
    import re
    assert not re.match(r"\s*(?!spring\b|string\b)\w+ing\b", " spring peas")
