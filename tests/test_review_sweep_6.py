"""
tests.test_review_sweep_6
===========================

The sixth review's findings (2026-11-25), each kept fixed: a model's own argument for a tool other than the four
calculators is never replaced by the prompt; the materials route never answers something done or paid, a count of
posts, a perimeter, posts for a deck or a fence the calculator doesn't build; days of water only for a question; a
lesson never for a fire pit, the tank's water or a seed company; the homestead sums read one person, groups added up,
hours, cans and a dozen with no time; and the plans' new exclusions leave their own questions alone.
"""

from types import SimpleNamespace

from core import assistant_turn, homestead_sums as sums, water_budget
from core.assistant_plan_actions import materials_reply
from core.lesson_answer import find
from core.question_plans import NOT_FOR
from core.tool_loop import HIS_WORDS_TOOLS, his_words


def test_another_tools_argument_is_never_the_prompt():
    registry = SimpleNamespace(_actions={"describe_app": SimpleNamespace(prompt_arg="app", description="An app.")})
    call = SimpleNamespace(name="describe_app", arguments={"app": "flock"})
    assert "describe_app" not in HIS_WORDS_TOOLS
    assert his_words(registry, call, "is the flock app working, and the power app?") == {"app": "flock"}


def test_the_materials_route_takes_only_a_question_it_can_answer():
    for words in ("I built 200 feet of fence today, how many posts did that take",
                  "how many bags of concrete for 26 fence posts", "how many posts for a fence around the 100 by 200 garden",
                  "how many posts for a barbed wire fence 1000 feet", "how many posts for the deck, it's 12 by 16",
                  "how many posts did the fence guy charge me for, it was 200 feet"):
        assert materials_reply(None, words) is None, words
    assert materials_reply(None, "How many fence posts for 200 feet?").startswith("200 ft fence")


def test_days_of_water_only_for_a_question(monkeypatch):
    monkeypatch.setattr(water_budget, "say", lambda context: "No tank levels logged.")
    context = SimpleNamespace(kitchen=None)
    for words in ("remind me to buy 14 days of water", "set my water target to 30 days of water",
                  "I lost 2 days of water when the tank leaked", "how long would the water last in a hot car?"):
        assert assistant_turn._water_on_hand_reply(context, words) is None, words
    assert assistant_turn._water_on_hand_reply(context, "How many days of water do I have?")


def test_a_lesson_never_for_what_it_doesnt_teach():
    for words in ("how do I build a fire pit", "how do I get fire insurance for the barn", "how do I clean the water tank",
                  "how do I filter the aquaponics water", "how do I start the seed company website"):
        assert find(words) is None, words


def test_the_sums_read_what_people_say():
    assert sums.people_in("for 1 person") == 1 and sums.people_in("2 adults and 2 kids") == 4
    assert sums.days_in("72 hours") == 3
    assert sums.fuel_in("two 5-gallon cans")[0] == 10 and sums.fuel_in("2 x 5 gallon cans")[0] == 10
    assert sums.eggs_wanted("18 eggs weekly") == 18 and sums.eggs_wanted("a dozen eggs every week") == 12
    assert sums.eggs_wanted("how many hens for a dozen eggs") == 12 and sums.eggs_wanted("I got 5 eggs") is None


def test_the_plans_own_questions_stay_theirs():
    for words in ("what are my first projects due?", "any good news on my projects?"):
        assert not NOT_FOR["projects"].search(words), words
    for words in ("how is the fire pit project going?", "the run-in shelter project", "the creek crossing project"):
        assert not NOT_FOR["project picture"].search(words), words
    assert NOT_FOR["projects"].search("What's a good beginner woodworking project?")
    assert NOT_FOR["project picture"].search("What's the best way to start a fire in the rain?")
