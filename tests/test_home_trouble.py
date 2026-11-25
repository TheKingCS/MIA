"""
tests.test_home_trouble
=========================

The house's trouble in fixed words (core/home_trouble.py, 2026-11-25): a burst pipe starts with the main shutoff, a
frozen one with the faucet open and never a flame, a flooded basement with the power; a question about the topic, or
a pipe that isn't his house's, is never one.
"""

from core import home_trouble


def test_each_trouble_starts_with_its_first_thing():
    assert home_trouble.reply("a pipe burst in the basement").startswith("Shut off the water at the main valve")
    assert home_trouble.reply("water's pouring through the ceiling!").startswith("Shut off the water")
    said = home_trouble.reply("my pipes are frozen")
    assert said.startswith("Open the faucet") and "Never an open flame" in said
    assert home_trouble.reply("the basement is flooding").startswith("If water is near outlets")
    assert home_trouble.reply("the sump pump stopped working and there's water coming in").startswith("If water")


def test_a_question_or_another_pipe_is_never_one():
    for words in ("how do I keep my pipes from freezing?", "how do I prevent a burst pipe", "what causes frozen pipes",
                  "the stock market is flooded with sellers", "my pipe tobacco is gone", "the ice cream is frozen"):
        assert home_trouble.reply(words) is None, words
