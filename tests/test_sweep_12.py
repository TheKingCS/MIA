"""
tests.test_sweep_12
=====================

The sixth live sweep's fixes (2026-11-25): "remind me tomorrow at 9 to call the vet" goes on his calendar like
"remind me to call the vet tomorrow at 9"; a tool call written out with a doubled quote before its key is caught;
what he spent on a category and "am I over budget?" are from his own records; a crop's dates and the 72-hour kit are hers.
"""

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
        "Nothing logged under Transportation last month."
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
