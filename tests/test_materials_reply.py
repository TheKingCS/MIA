"""
tests.test_materials_reply
============================

A materials question with its structure and size answered in code (core/assistant_plan_actions.materials_reply;
live check, 2026-11-25: "how many fence posts for 200 feet?" reached find_plans, and once the model said "2 posts" for
100 feet): the calculators' list, never saved; with no size, the size asked for and a fence's post spacing (the model
had said "2-3 posts per 8-foot section"); never a question that isn't about materials. And "do we have plans for a
fence?" is no project picture.
"""

from core.assistant_plan_actions import materials_reply
from core.question_plans import NOT_FOR


def test_a_structure_and_its_size_get_the_calculators_list():
    assert materials_reply(None, "How many fence posts for 200 feet?").startswith(
        "200 ft fence, 6 ft tall:\n- 26 4x4 x 10 ft pressure-treated posts")
    assert materials_reply(None, "What do I need to build a 10 by 12 shed?").startswith("10 x 12 ft gable shed:")


def test_no_size_asks_for_it_with_a_fences_spacing():
    said = materials_reply(None, "How many posts should a fence have?")
    assert said.startswith("A wood fence's posts go every 8 ft, with one more at the end (so 26 for 200 ft)")
    assert "Tell me its size" in said


def test_other_questions_are_not_materials():
    for words in ("How is the fence holding up?", "Do we have plans for a fence?", "I built 200 feet of fence today"):
        assert materials_reply(None, words) is None, words
    assert NOT_FOR["project picture"].search("Do we have plans for a fence?")
