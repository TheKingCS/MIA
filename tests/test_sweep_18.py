"""
tests.test_sweep_18
=====================

The twelfth live sweep's fixes (2026-11-25): the time, the date, days until a holiday, a floor's square footage, a
walk logged and an egg price from his feed cost are worked out in code; the library's note to the model is never
said; a grocery list written as JSON is its items, and nothing goes on it unless he asked; what's on the grocery list
is never the day's plan. The Fable review of it: the guard reaches the tool and stops only what isn't a list; each
everyday route takes only its own; his own product is found by its name's words.
"""

from types import SimpleNamespace

from core import assistant_turn, question_plans
from core.assistant_domain_actions import _action_add_grocery_item


def test_the_small_everyday_answers():
    assert assistant_turn._everyday_reply(None, "What time is it?").startswith("It's ")
    assert assistant_turn._everyday_reply(None, "what's the date today?").startswith("It's ")
    assert "days until Christmas" in assistant_turn._everyday_reply(None, "How many days until Christmas?") or \
        assistant_turn._everyday_reply(None, "How many days until Christmas?") == "Christmas is today."
    assert assistant_turn._everyday_reply(None, "What's the square footage of a 12 by 16 shed?") == \
        "12 by 16 feet is 192 square feet."
    assert assistant_turn._everyday_reply(None, "how many days until my dentist appointment?") is None
    assert assistant_turn._everyday_reply(None, "what's the time difference to London") is None
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "ok"))
    assert assistant_turn._everyday_reply(context, "Log a 30 minute walk") == "ok"
    assert ran[-1][0] == "log_workout" and ran[-1][1]["duration_minutes"] == 30
    said = assistant_turn._everyday_reply(SimpleNamespace(flock=None), "How much should I charge per dozen eggs?")
    assert said.startswith("Log your feed and eggs") and "permit" in said


def test_groceries_only_when_asked_and_never_brackets():
    added = []
    kitchen = SimpleNamespace(all_grocery_items=lambda: [], add_grocery_item=lambda n, **k: added.append(n))
    context = SimpleNamespace(kitchen=kitchen)
    assert _action_add_grocery_item(context, {"items": '["milk", "eggs"]'}) == "Added milk, eggs to the grocery list."
    assert _action_add_grocery_item(context, {"items": "eggs", "question": "I want to start selling eggs"}) == \
        "Should I add eggs to the grocery list?"
    assert added == ["milk", "eggs"]


def test_the_grocery_list_is_never_the_days_plan():
    assert question_plans._not_for("today", "What's on my grocery list?")


def test_the_fable_review_of_sweep_18():
    """The guard reaches the grocery tool and only stops a sentence that isn't a list; the everyday routes take only
    their own; his own product is found by its name's words."""
    from core import outage_plan, tool_loop
    from core.llm_manager import ToolCall

    registry = SimpleNamespace(_actions={"add_grocery_item": SimpleNamespace(prompt_arg="question", description="d")})
    called = tool_loop.his_words(registry, ToolCall("add_grocery_item", {"items": ["eggs"]}), "I want to start selling eggs")
    assert called["question"] == "I want to start selling eggs"
    added = []
    kitchen = SimpleNamespace(all_grocery_items=lambda: [], add_grocery_item=lambda n, **k: added.append(n))
    for words in ("milk", "milk too", "don't forget the milk", "yes", "I'm outta milk"):
        assert _action_add_grocery_item(SimpleNamespace(kitchen=kitchen), {"items": "milk", "question": words}).startswith(
            "Added"), words
        added.clear()
    assert assistant_turn._everyday_reply(None, "what's today?").startswith("It's ") and "," in \
        assistant_turn._everyday_reply(None, "what's today?")
    for words in ("what price are eggs at walmart?", "how do I price a dozen cupcakes?", "can you ask mom for a dozen eggs?",
                  "how much did I sell eggs for last week?", "area code 212 by 4", "what's the area rug size, 5 by 8?",
                  "square footage of a 12 ft 6 by 10 room", "area of 10 by 12 meters",
                  "how many days before easter should i order the ham",
                  "how many days until the day after thanksgiving"):
        assert assistant_turn._everyday_reply(None, words) is None, words
    assert assistant_turn._everyday_reply(None, "square footage: 1,200 by 3") == "1200 by 3 feet is 3,600 square feet."
    for words in ("what do I do when the power is out right now", "what can I do for more power in my truck",
                  "if I lose power in my legs", "what do I need for a grid tie inverter"):
        assert outage_plan.reply(None, words) is None, words
