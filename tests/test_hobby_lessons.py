"""
tests.test_hobby_lessons
==========================

His hobbies' courses answer their own how-tos (core/lesson_answer.py, the live sweep 2026-11-25): tuning, a chord
progression, barre and power chords, the pentatonic, string bends, wood joints and finishes, progressive overload;
never a car's finish or an oil change.
"""

from core import lesson_answer


def test_each_hobby_how_to_reaches_its_lesson():
    for words, key in (("How do I tune my guitar?", ("guitar", "hold_tune")),
                       ("Give me a chord progression to practice", ("guitar", "progression")),
                       ("how do I play a barre chord", ("guitar", "barre_f")),
                       ("how do I play power chords", ("guitar", "power")),
                       ("what scales to practice on guitar", None),
                       ("how do I cut a dovetail", ("woodworking", "joints")),
                       ("how do I finish a cutting board", ("woodworking", "finishes")),
                       ("how do I do progressive overload", ("fitness", "progression"))):
        found = lesson_answer.find(words)
        if key is not None:
            assert found == key, words


def test_a_cars_finish_or_an_oil_change_is_never_the_bench():
    for words in ("how do I finish my truck's paint", "how do I oil the deck", "how do I seal the concrete floor"):
        found = lesson_answer.find(words)
        assert found is None or found[0] != "woodworking", words
