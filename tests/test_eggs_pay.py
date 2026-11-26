"""
tests.test_eggs_pay
=====================

"Are the eggs paying for the feed?" is the flock's own numbers (get_eggs, the egg conversation check 2026-11-26: the
spending pace had said "I need two months of your spending").
"""

from core import assistant_turn


def test_the_words_reach_the_flocks_numbers():
    patterns = [p for n, p, _w in assistant_turn._OWN_TOOLS if n == "get_eggs"]
    for words in ("are the eggs paying for the feed?", "do the hens pay for themselves?",
                  "what do the eggs cost me a dozen?"):
        assert any(p.match(words) for p in patterns), words
    assert not any(p.match("are the eggs in the fridge?") for p in patterns)
    pay = patterns[-1]
    for words in ("are the eggs paying for the feed this month?", "do the eggs cover the feed if I sell more?",
                  "do the eggs pay for my keep?"):
        assert not pay.match(words), words
