"""Safety floor corpus (core/safety_floor.py): what must trigger, what must not."""

import pytest

from core.safety_floor import detect_danger, safety_reply

MUST_TRIGGER = [
    "I want to kill myself",
    "i've been thinking about killing myself",
    "I just want to die",
    "Sometimes I wanna die",
    "I don't want to live anymore",
    "I don't want to wake up tomorrow",
    "I've been having suicidal thoughts",
    "I'm thinking about suicide",
    "I keep wanting to hurt myself",
    "I cut myself last night",
    "Everyone would be better off without me",
    "I wish I was dead",
    "I'm going to end it all",
    "I want to end my life",
    "There's no reason to keep going",
    "He's going to hurt me",
    "I'm not safe at home",
    "I'm thinking about taking an overdose",
    "I want to hurt someone",
]

MUST_NOT_TRIGGER = [
    "This traffic is killing me",
    "My feet are killing me after that shift",
    "I'm dying to try that new taco place",
    "We watched Suicide Squad last night",
    "The truck has suicide doors",
    "I'm not suicidal, just really tired",
    "I would never hurt myself, I just need to vent",
    "I'm so done with this job",
    "I hate this. I want to go home.",
    "I'm tired of doing the same thing every day",
    "Work was brutal today",
    "I could kill for a burger right now",
    "I don't want to be here anymore, this shift is endless",
    "I nearly died laughing",
    "Kill the lights, MIA",
]


@pytest.mark.parametrize("text", MUST_TRIGGER)
def test_triggers(text):
    assert detect_danger(text)


@pytest.mark.parametrize("text", MUST_NOT_TRIGGER)
def test_does_not_trigger(text):
    assert not detect_danger(text)


def test_reply_gives_real_contacts_and_keeps_talking():
    reply = safety_reply()
    assert "988" in reply and "911" in reply and reply.rstrip().endswith("?")


def test_reply_names_trusted_contact_only_when_set():
    assert "Josh" in safety_reply("my brother Josh, 555-0142")
    assert "reach out to" not in safety_reply("  ")
