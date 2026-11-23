"""
tests.test_first_aid_floor
============================

The emergency floor (core/first_aid_floor.py, brainstorm 4.2): words that say an emergency is happening now get fixed
first-aid words with the emergency number before any model; a question about the topic, a past one or a figure of
speech goes on as usual. The corpus lists both what must trigger (the review of 2026-11-23 added the panicked,
pronoun-less and missing kinds) and what must not.
"""

from types import SimpleNamespace

import pytest

from core import first_aid_floor as faf
from core.region import OTHER, REGIONS

MUST = [
    ("He's not breathing", "cpr"),
    ("baby not breathing", "cpr"),
    ("help dad not breathing", "cpr"),
    ("not breathing!", "cpr"),
    ("my dad collapsed and isn't breathing", "cpr"),
    ("she's choking on a piece of meat", "choking"),
    ("she's choking and can't breathe", "choking"),
    ("what to do if my baby is choking right now", "choking"),
    ("how do you do the heimlich, she's choking", "choking"),
    ("I cut my hand on the table saw and it won't stop bleeding", "bleeding"),
    ("my son's leg is bleeding badly", "bleeding"),
    ("he's bleeding", "bleeding"),
    ("my hand is bleeding really bad", "bleeding"),
    ("I have a deep cut on my leg", "bleeding"),
    ("I've been shot", "bleeding"),
    ("he's been stabbed", "bleeding"),
    ("I think my wife is having a stroke, her face is drooping", "stroke"),
    ("his speech is slurred", "stroke"),
    ("my dad has chest pain and it's going down his left arm", "heart"),
    ("crushing pain in my chest", "heart"),
    ("he passed out in the barn", "unconscious"),
    ("she's not responding", "unconscious"),
    ("he fainted", "unconscious"),
    ("he blacked out", "unconscious"),
    ("my kid swallowed bleach", "poison"),
    ("my kid swallowed some pills", "poison"),
    ("he took too many pills", "poison"),
    ("my son swallowed a button battery", "poison"),
    ("I just got bit by a rattlesnake", "snakebite"),
    ("a snake bit me", "snakebite"),
    ("a copperhead bit him", "snakebite"),
    ("my friend's throat is swelling after a bee sting", "anaphylaxis"),
    ("allergic reaction and he can't breathe", "anaphylaxis"),
    ("my throat is swelling I can't breathe", "anaphylaxis"),
    ("his clothes caught fire", "burn"),
    ("I burned my hand badly", "burn"),
    ("I think he has heat stroke", "heat"),
    ("he has heat-stroke", "heat"),
    ("he's having a seizure", "seizure"),
    ("my son is drowning", "drowning"),
    ("I'm having an asthma attack", "breathing"),
    ("he got electrocuted", "shock"),
    ("he got kicked by the horse and is not responding", "unconscious"),
    ("he cut his hand bad with the chainsaw", "bleeding"),
    ("the dog bit me and I'm bleeding a lot", "bleeding"),
    ("the baby fell in the pond", "drowning"),
]

MUST_NOT = [
    "what are the signs of a stroke?",
    "how do you treat a snakebite?",
    "what to do if someone is choking",
    "teach me CPR",
    "tell me about heart attacks",
    "this traffic is killing me",
    "the pipe won't stop leaking",
    "I'm choking on all this paperwork",
    "the power got cut off at my place",
    "my cut off date is friday",
    "my 2-stroke chainsaw won't start",
    "I had a stroke of luck",
    "my laptop won't wake up",
    "we knocked out three tasks today",
    "my tomato plants collapsed in the heat",
    "I'm on fire today",
    "my hydrangeas are turning blue",
    "my heart stopped when I saw the bill",
    "my dad had a heart attack in 2019",
    "I'm drowning in work",
    "I'm bleeding the brakes on the truck",
    "the engine is seizing up",
    "the brush pile caught fire",
    "I almost had a heart attack when I saw the price",
    "I can't breathe through my nose this week",
    "my dog is choking",
    "my chickens are choking",
    "the app is not responding",
    "my laptop is not responding",
]


@pytest.mark.parametrize("words,kind", MUST)
def test_an_emergency_happening_now_is_caught(words, kind):
    assert faf.detect(words) == kind


@pytest.mark.parametrize("words", MUST_NOT)
def test_a_question_about_the_topic_a_past_one_or_a_figure_of_speech_is_not(words):
    assert faf.detect(words) is None


def test_the_number_follows_his_country_and_never_guesses():
    assert faf.reply("cpr", REGIONS["GB"]).startswith("Call 999 now")
    assert faf.reply("cpr", REGIONS["AU"]).startswith("Call 000 now")
    assert "112 works" in faf.reply("cpr", OTHER)


def test_every_kind_has_steps_and_no_medicine_dose():
    import re

    for kind, _words, steps in faf.KINDS:
        said = faf.reply(kind)
        assert "Tell me what's happening" in said and steps in said
        assert not re.search(r"\b\d+\s*(?:mg|milligrams?|ml)\b", said, re.I), kind


def test_cpr_says_the_rate_and_depth_for_adults_and_babies():
    said = faf.reply("cpr")
    assert "100 to 120 times a minute" in said and "2 inches deep" in said and "1.5 inches" in said


def test_choking_comes_before_cpr_and_both_are_said():
    found = faf.kinds("she's choking and not breathing")
    assert found[:2] == ["choking", "cpr"]
    said = faf.reply(found)
    assert said.index("back blows") < said.index("100 to 120")


def test_a_kind_whose_steps_dont_say_when_to_start_cpr_gets_that_line():
    assert faf._CPR_SHORT in faf.reply("anaphylaxis") and faf._CPR_SHORT in faf.reply("bleeding")
    assert faf._CPR_SHORT not in faf.reply("choking")


def test_the_same_emergency_next_goes_on_to_the_model_a_new_one_gets_the_floor():
    first = faf.respond("he's not breathing", [])
    assert first and faf.floor_kind_of(first) == "cpr"
    history = [SimpleNamespace(role="user", content="he's not breathing"), SimpleNamespace(role="assistant", content=first)]
    assert faf.respond("he's still not breathing, I'm doing compressions", history) is None
    assert faf.respond("now my wife is choking", history).startswith("Call 911 now")


def test_the_floor_answers_before_the_model_and_without_one():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    src = (root / "core" / "talk_it_out.py").read_text(encoding="utf-8")
    assert src.index("detect_danger(prompt)") < src.index("first_aid_floor.respond(") < src.index(
        "from core.connections import notice")
    for gui in ("gui/character_panel.py", "gui/home_dashboard.py", "modules/assistant/module.py"):
        assert "and not emergency_now(prompt)" in (root / gui).read_text(encoding="utf-8"), gui
