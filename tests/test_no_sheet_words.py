"""
tests.test_no_sheet_words
===========================

"The fact sheet" never said aloud in the model's answers (core/response_composer.without_sheet_words, brainstorm
round 19's live check: a bare "why?" got "You mentioned a fact sheet, but ..."); his own quoted words, a list's
items and code stay, and a code answer is never touched.
"""

from core.response_composer import polish, without_sheet_words


def test_a_sentence_about_a_fact_sheet_goes_and_the_rest_stays():
    said = without_sheet_words("You didn't say what the why is about. You mentioned a fact sheet, but it seems like you want a "
                  "reason. What's on your mind?")
    assert "fact sheet" not in said and said.startswith("You didn't say what the why is about.")
    assert without_sheet_words("The fact sheet says the shed is due Friday.") == "The shed is due Friday."
    note = 'Your note says: "print the OSHA fact sheet for ladders". It\'s due Friday.'
    assert without_sheet_words(note) == note and polish(note) == note
    items = "You have 3 items:\n1. Fact sheet binder\n2. Drill\n3. Saw"
    assert without_sheet_words(items) == items
    code = "```\n# parse the fact sheet\n```"
    assert without_sheet_words(code) == code
    assert polish("A balance sheet lists what you own.") == "A balance sheet lists what you own."
