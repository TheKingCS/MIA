"""
tests.test_everyday_phrasing_routing
======================================

The everyday ways he'd ask for the tools built 2026-11-23 and 24 reach them by their trigger phrases, without the
embedding model (the phone): who owes him, his emergency kit, the jars he puts up and his canning shelf, his
generator and preparedness settings, how long the generator runs, the weather against his plans, where he left
off, money ahead, an invoice, the garden's week and year, a build's price and the flock's feed; and a plan whose words
catch a weather, garden or flock question (the evening's, the week's, what's coming up) leaves it to those tools.
"""

import pytest

from tests.assistant_registry import build_desktop_registry, demo_context, offered_tools

SAID = [
    ("who_owes_me", "Who owes me money?"), ("who_owes_me", "Has anyone not paid me yet?"),
    ("who_owes_me", "what's outstanding on my orders"), ("who_owes_me", "which customers still owe me"),
    ("emergency_kit", "check my emergency kit"), ("emergency_kit", "what am I missing for a go bag"),
    ("emergency_kit", "is my 72 hour kit complete?"), ("emergency_kit", "what should be in my bug out bag"),
    ("put_up_jars", "I put up 7 quarts of tomatoes today"), ("put_up_jars", "we canned 12 pints of salsa"),
    ("canning_shelf", "what's on my canning shelf?"), ("canning_shelf", "which canned stuff should I use first"),
    ("set_preparedness", "my generator burns half a gallon an hour"), ("set_preparedness", "plan for 3 people"),
    ("set_preparedness", "my generator uses 2 pounds of propane an hour"),
    ("how_prepared", "how many days could my generator run?"), ("how_prepared", "how prepared am I?"),
    ("weather_for_my_plans", "is it going to frost tonight?"), ("weather_for_my_plans", "do I need to cover the tomatoes"),
    ("weather_for_my_plans", "will the rain mess up the shed build tomorrow?"),
    ("where_were_we", "what was I in the middle of"), ("money_ahead", "will I be short next month?"),
    ("draft_invoice", "send Lee a bill for the bench"), ("garden_this_week", "what should I plant this week"),
    ("garden_this_week", "what seeds do I still need?"),
    ("homestead_year", "what's coming up on the homestead this spring"),
    ("price_build", "how much should I charge for a picnic table"),
    ("get_eggs", "how long will the feed last?"), ("get_eggs", "when do I need more chicken feed"),
]


@pytest.fixture(scope="module")
def registry():
    """The desktop's tool registry, built once."""
    return build_desktop_registry()


@pytest.mark.parametrize("tool,said", SAID)
def test_each_everyday_phrasing_is_offered_its_tool(registry, tool, said):
    assert tool in offered_tools(registry, said, demo_context()), said


@pytest.mark.parametrize("said", ["is it going to frost tonight?", "what should I plant this week",
                                  "what's coming up on the homestead this spring", "will I be short next month?",
                                  "when do I need more chicken feed tonight"])
def test_a_plan_leaves_a_weather_garden_or_flock_question_to_its_tool(said):
    from core import question_plans

    assert question_plans.match(demo_context(), said) is None, said


def test_the_plans_still_take_their_own_questions():
    from core import question_plans

    for said, plan in (("what's on tonight?", "tonight"), ("how was my week?", "week review"),
                       ("what's coming up?", "coming up"), ("what should I charge for the shed?", "product cost")):
        found = question_plans.match(demo_context(), said)
        assert found is not None and found.name == plan, said
