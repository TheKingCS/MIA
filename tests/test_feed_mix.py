"""
tests.test_feed_mix
=====================

Two feeds mixed to a target protein, the Pearson square (core/feed_mix.py): the parts and shares of each, a batch's
pounds of each, the three percentages and the batch read from what he said, and a target outside the two feeds (or
two feeds the same) refused in words.
"""

import pytest

from core import feed_mix as fm


def test_the_square_gives_parts_shares_and_a_batch():
    got = fm.mix(16, 32, 20, 100)
    assert got["parts"] == (12, 4) and got["shares"] == (75.0, 25.0) and got["amounts"] == (75.0, 25.0)


def test_what_he_said_is_read_and_answered():
    said = fm.say("how do I mix 16% layer feed and 32% supplement to get 20% for a 50 lb batch")
    assert "12 parts of the 16% feed to 4 parts of the 32%" in said and "37.5 lb of the 16%" in said


def test_a_target_outside_the_two_is_refused():
    with pytest.raises(fm.MixError):
        fm.mix(16, 18, 22)
    assert "isn't between" in fm.say("mix 16% and 18% to get 22%")
    assert fm.say("mix some feed").startswith("Give me the two feeds' protein")
