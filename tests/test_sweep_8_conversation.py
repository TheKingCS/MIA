"""
tests.test_sweep_8_conversation
=================================

The third live sweep's conversation fixes (2026-11-25): an expense's date is a real date or today (the model sent
"null", and no month counted it), feed has its own category, the tone examples are other people's and never this
conversation (the model brought up "that marathon you're running next week" after "thanks"), a pleasantry gets no
joke and a warm line with no bill tacked on, and a humor example copied loosely goes.
"""

from core import personality
from core.budget_manager import EXPENSE_CATEGORIES, _entry_date


def test_an_entrys_date_is_a_real_date_or_today():
    from datetime import date

    today = date.today().isoformat()
    assert _entry_date("null") == today and _entry_date(None) == today and _entry_date("2024-13-40") == today
    assert _entry_date("2026-11-03") == "2026-11-03" and _entry_date("2026-11-03T10:00") == "2026-11-03"
    assert "Animals & Feed" in EXPENSE_CATEGORIES


def test_the_tone_examples_are_never_this_conversation():
    assert "Them:" not in personality.EXAMPLES and "marathon" not in personality.EXAMPLES
    assert "never mention them" in personality.EXAMPLES


def test_a_pleasantry_gets_no_joke_and_no_bill():
    for words in ("thanks", "you're the best", "Thanks, that's helpful", "hey", "good morning MIA"):
        assert not personality.light_moment(words), words
        assert personality.pleasantry_line(words) == personality.JUST_PLEASANTRY, words
    assert personality.light_moment("my coffee went cold") and personality.pleasantry_line("how's the garden?") == ""


def test_a_humor_example_copied_loosely_goes_unless_he_brought_it_up():
    reply = "It's not a cord any more, it's a tangled mess. Glad it helped!"
    assert personality.without_copied_example(reply, "Thanks, that's helpful") == "Glad it helped!"
    assert personality.without_copied_example("That cord is a mess. Try a cable tie.", "how do I fix a tangled cord?") \
        == "That cord is a mess. Try a cable tie."
