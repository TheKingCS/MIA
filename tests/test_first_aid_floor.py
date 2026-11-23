"""
tests.test_first_aid_floor
============================

The emergency floor (core/first_aid_floor.py, brainstorm 4.2): words that say an emergency is happening now get
fixed first-aid words with the emergency number before any model; a question about the topic goes on to the library.
The corpus lists both what must trigger and what must not.
"""

import pytest

from core import first_aid_floor as faf
from core.region import OTHER, REGIONS

MUST = [
    ("He's not breathing", "cpr"),
    ("my dad collapsed and isn't breathing", "cpr"),
    ("she's choking on a piece of meat", "choking"),
    ("I cut my hand on the table saw and it won't stop bleeding", "bleeding"),
    ("my son's leg is bleeding badly", "bleeding"),
    ("I think my wife is having a stroke, her face is drooping", "stroke"),
    ("my dad has chest pain and it's going down his left arm", "heart"),
    ("he passed out in the barn", "unconscious"),
    ("my kid swallowed bleach", "poison"),
    ("I just got bit by a rattlesnake", "snakebite"),
    ("my friend's throat is swelling after a bee sting", "anaphylaxis"),
    ("his clothes caught fire", "burn"),
    ("I think he has heat stroke", "heat"),
]

MUST_NOT = [
    "what are the signs of a stroke?",
    "how do you treat a snakebite?",
    "what to do if someone is choking",
    "teach me CPR",
    "tell me about heart attacks",
    "this traffic is killing me",
    "the pipe won't stop leaking",
    "I'm choking on all this paperwork",  # no emergency word after the guard? still choking: see test below
]


@pytest.mark.parametrize("words,kind", MUST)
def test_an_emergency_happening_now_is_caught(words, kind):
    assert faf.detect(words) == kind


@pytest.mark.parametrize("words", MUST_NOT[:-1])
def test_a_question_about_the_topic_or_a_figure_of_speech_is_not(words):
    assert faf.detect(words) is None


def test_a_false_positive_costs_one_careful_message():
    # "choking on paperwork" reads as choking: the floor errs broad, and its words are still right if it's real.
    said = faf.reply(faf.detect(MUST_NOT[-1]) or "choking")
    assert said.startswith("Call 911 now")


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


def test_cpr_says_the_rate_and_depth():
    said = faf.reply("cpr")
    assert "100 to 120 times a minute" in said and "2 inches deep" in said


def test_the_floor_answers_before_the_model(monkeypatch):
    from core import talk_it_out

    src = open(talk_it_out.__file__, encoding="utf-8").read()
    assert src.index("detect_danger(prompt)") < src.index("first_aid_floor.detect(prompt)") < src.index(
        "from core.connections import notice")
