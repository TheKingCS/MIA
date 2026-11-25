"""
tests.test_water_on_hand
==========================

"How many days of water do I have?" is answered both ways it can mean (core/assistant_turn._water_on_hand_reply;
live check, 2026-11-25: three tools matched and the model asked for the catchment roof): the pantry's drinking water
against his target (core/preparedness.water_lines, the same words "how prepared am I?" begins with), then the
property's stored water; a question about use alone, or anything else, isn't it.
"""

from types import SimpleNamespace

from core import assistant_turn, preparedness, water_budget


def test_days_of_water_says_the_drinking_water_then_the_propertys(monkeypatch):
    monkeypatch.setattr(water_budget, "say", lambda context: "No tank levels logged.")
    context = SimpleNamespace(kitchen=None)
    for words in ("How many days of water do I have?", "how long will our water last?",
                  "How much drinking water do we have?"):
        said = assistant_turn._water_on_hand_reply(context, words)
        assert said.startswith("Drinking water: none logged in the pantry.") and said.endswith(
            "For the whole property: No tank levels logged."), words
    assert assistant_turn._water_on_hand_reply(context, "How much water do we use a day?") is None
    assert assistant_turn._water_on_hand_reply(context, "water the tomatoes") is None


def test_the_preparedness_answer_still_begins_with_the_same_water_line():
    context = SimpleNamespace(kitchen=None)
    assert preparedness.say(context).startswith(" ".join(preparedness.water_lines(context, [])))
