"""
tests.test_sweep_19
=====================

The thirteenth live sweep's fixes (2026-11-25): "we're out of milk" goes on the grocery list, never into the pantry;
"my freezer uses 150 watts" is kept as one of his loads; what's on his calendar and who he owes are never the week's
review or his assets' returns.
"""

from types import SimpleNamespace

from core import assistant_turn, question_plans
from core.assistant_domain_actions import _action_add_pantry_item


def test_out_of_milk_is_the_grocery_lists():
    added = []
    kitchen = SimpleNamespace(all_grocery_items=lambda: [], add_grocery_item=lambda n, **k: added.append(n))
    said = _action_add_pantry_item(SimpleNamespace(kitchen=kitchen), {"name": "milk", "question": "We're out of milk"})
    assert said == "Added milk to the grocery list." and added == ["milk"]


def test_a_loads_watts_are_kept():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "ok"))
    assert assistant_turn._load_watts_reply(context, "My freezer uses 150 watts") == "ok"
    assert ran[-1][0] == "set_power_load" and ran[-1][1]["load"] == "freezer" and ran[-1][1]["watts"] == 150
    assistant_turn._load_watts_reply(context, "the well pump draws 1,000 watts for 2 hours a day")
    assert ran[-1][1]["watts"] == 1000 and ran[-1][1]["hours"] == 2
    for words in ("my phone charger uses 20 watts", "the light bulb is 60 watts", "my freezer is making a noise"):
        assert assistant_turn._load_watts_reply(context, words) is None, words


def test_the_calendar_and_his_debts_are_never_the_wrong_plans():
    assert question_plans._not_for("week review", "What's on my calendar this week?")
    assert question_plans._not_for("returns", "Who do I owe money to?")
