"""
tests.test_no_sheet_words
===========================

"The fact sheet" never said aloud in any polished answer (core/response_composer.without_sheet_words, brainstorm
round 19's live check: a bare "why?" got "You mentioned a fact sheet, but ...").
"""

from core.response_composer import polish


def test_a_sentence_about_a_fact_sheet_goes_and_the_rest_stays():
    said = polish("You didn't say what the why is about. You mentioned a fact sheet, but it seems like you want a "
                  "reason. What's on your mind?")
    assert "fact sheet" not in said and said.startswith("You didn't say what the why is about.")
    assert polish("The fact sheet says the shed is due Friday.") == "The shed is due Friday."
    assert polish("A balance sheet lists what you own.") == "A balance sheet lists what you own."
