"""
tests.test_everyday_phrasing_routing
======================================

The everyday ways he'd ask for the tools built 2026-11-23 and 24 reach them by their trigger phrases, without the
embedding model (the phone): who owes him, his emergency kit, the jars he puts up and his canning shelf, his
generator and preparedness settings, everyday money questions (bills due, the budget, subscriptions, a tax
refund, where the money went), how long the generator runs, the weather against his plans, where he left
off, money ahead, an invoice, the garden's week and year, a build's price, the flock's feed and his learning
programs (woodworking, gardening, fitness, bushcraft), her offline library for how-to questions about the world
("how do I purify creek water?", never held to her own help pages); and a plan whose words
catch a weather, garden, flock or bills question (the evening's, the week's, what's coming up, the month's money) leaves it to those tools.
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
    ("anything_unusual", "have I been spending more than normal?"), ("evening_wrap", "what's first tomorrow"),
    ("start_learning", "I want to get into woodworking"), ("start_learning", "start the bushcraft program"),
    ("start_learning", "help me get fit"), ("start_learning", "teach me gardening"),
    ("learning_lesson", "what's my next woodworking lesson?"), ("learning_lesson", "what should I practice in the shop"),
    ("learning_lesson", "what's my bushcraft homework this week"), ("learning_lesson", "what's next in my fitness plan"),
    ("log_practice", "spent an hour in the shop today"), ("log_practice", "worked on fire starting for half an hour"),
    ("learning_check", "I cut a dovetail joint today"), ("learning_check", "I started a fire with a ferro rod"),
    ("learning_progress", "how's my woodworking coming along?"), ("learning_progress", "how's my fitness going"),
    ("learning_progress", "what stage am I on in gardening"),
    ("look_up_offline", "how do I purify creek water?"), ("look_up_offline", "how do I start a fire without matches"),
    ("look_up_offline", "how do I tie a bowline"), ("look_up_offline", "how do I butcher a chicken"),
    ("look_up_offline", "what wild plants are edible here"), ("look_up_offline", "how do I build a lean-to shelter"),
    ("bleach_for_water", "how much bleach to purify 5 gallons of water"),
    ("bleach_for_water", "how many drops of bleach per gallon"),
    ("list_bills", "what bills are due this week?"), ("add_expense", "spent $120 at the feed store"),
    ("get_budget_summary", "how's my budget looking"), ("list_unchecked_subscriptions", "what subscriptions am I paying for?"),
    ("money_ahead", "will I have enough for rent next month?"),
    ("list_inventory", "where did I put the post hole digger"), ("garden_this_week", "what needs doing in the garden"),
    ("add_expense", "I bought 3 bags of chicken feed"), ("complete_maintenance_task", "I changed the oil in the truck today"),
    ("log_maintenance_reading", "the mower has 212 hours on it"), ("add_alarm", "remind me to fix the fence saturday"),
    ("get_project_missions", "how's the shed build coming along?"),
    ("get_project_missions", "how far along is the chicken coop project"),
    ("make_quote", "make a quote for a cedar chest for Dana"), ("accept_quote", "Dana accepted the quote"),
    ("list_quotes", "what quotes are still out?"), ("order_paid", "Lee paid the deposit on the bench"),
    ("add_customer", "add a new customer named Sam Ortiz"), ("get_customer_details", "what's my customer's phone number for Sam"),
    ("list_orders", "what orders are due this week?"),
    ("log_workout", "I ran 3 miles this morning"), ("log_workout", "did 45 minutes on the bike"),
    ("log_workout", "I benched 185 for 5"), ("plan_meal", "what's for dinner this week"),
    ("get_net_worth", "what's my net worth?"), ("get_net_worth", "how much am I worth"),
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
                                  "when do I need more chicken feed tonight", "have I been spending more than normal?",
                                  "what's first tomorrow", "what's my bushcraft homework this week"])
def test_a_plan_leaves_a_weather_garden_or_flock_question_to_its_tool(said):
    from core import question_plans

    assert question_plans.match(demo_context(), said) is None, said


def test_the_plans_still_take_their_own_questions():
    from core import question_plans

    for said, plan in (("what's on tonight?", "tonight"), ("how was my week?", "week review"),
                       ("what's coming up?", "coming up"), ("what should I charge for the shed?", "product cost")):
        found = question_plans.match(demo_context(), said)
        assert found is not None and found.name == plan, said


def test_money_questions_reach_their_plans_by_word():
    from core import question_plans

    for said, plan in (("where should my tax refund go?", "next dollar"),
                       ("where did my money go this month?", "money month")):
        found = question_plans.match(demo_context(), said)
        assert found is not None and found.name == plan, said
    for said in ("what bills are due this week?", "will I have enough for rent next month?"):
        assert question_plans.match(demo_context(), said) is None, said  # their tools answer them
