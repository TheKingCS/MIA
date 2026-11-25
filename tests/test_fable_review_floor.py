"""
tests.test_fable_review_floor
===============================

The Fable review of the emergency floor and teaching (2026-11-25): a figure of speech or a past clause takes out only
its own words (its real emergencies are in tests/test_first_aid_floor_never_misses.py); a follow-up naming an
emergency the floor's last reply didn't cover is answered; freezer burn, a tree's wound and a nosebleed never get
the floor's steps; the kitchen's water, a goat shelter, a margin of safety and a quote tweet aren't lessons; the bare
word "power" never starts the outage drill.
"""

from types import SimpleNamespace

from core import drills, first_aid_floor as floor, lesson_answer


def test_a_new_emergency_after_the_floors_reply_is_answered():
    first = floor.respond("dad collapsed", [])
    assert first is not None
    history = [SimpleNamespace(role="assistant", content=first)]
    later = floor.respond("he's unconscious and not breathing", history)
    assert later is not None and "start CPR: kneel beside them" in later
    assert floor.respond("dad collapsed again", history) is None  # the same one, already answered


def test_everyday_phrases_still_are_not_emergencies():
    for words in ("I'm drowning in work", "I almost had a heart attack when I saw the price",
                  "my laptop won't wake up", "the app is not responding", "I'm burning brush today",
                  "it took all day", "how strong an electric shock should my electric fence give?"):
        assert floor.detect(words) is None, words


def test_freezer_burn_a_trees_wound_and_a_nosebleed_get_no_floor_steps():
    for words in ("how do i treat freezer burn", "how do i treat razor burn",
                  "what do i do about wounds on my apple tree", "how do i stop a bleeding nose"):
        assert floor.teach(words) is None, words


def test_the_kitchen_a_goat_shelter_and_a_quote_tweet_are_no_lessons():
    for words in ("how do i boil water for pasta", "how do i clean up water in the basement",
                  "how do i treat hard water", "how do i clean the water trough",
                  "how do i build a shelter for the goats", "what's a good margin of safety for a beam",
                  "how do i do a quote tweet"):
        assert lesson_answer.find(words) is None, words


def test_the_word_power_alone_never_starts_the_outage_drill():
    for words in ("quiz me on the power rule for calculus", "quiz me on power electronics"):
        found = drills.requested(words)
        assert found is None or getattr(found, "id", found) != "power_out", words
    found = drills.requested("give me a power outage drill")
    assert found is not None
