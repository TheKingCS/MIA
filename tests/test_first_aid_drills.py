"""
tests.test_first_aid_drills
=============================

The first-aid drills (core/drills.py: a deep cut, choking at dinner), written in the emergency floor's words
(core/first_aid_floor.py) so a drill never teaches what the floor wouldn't say; asking for one never trips the floor,
and anything that says it's real still does.
"""

from types import SimpleNamespace

from core import drills
from core import first_aid_floor as floor

EMPTY = SimpleNamespace(messages=[])


def test_asking_for_a_first_aid_drill_starts_one_and_never_trips_the_floor():
    for words, title in (("give me a choking drill", "Choking at dinner"), ("run the deep cut drill", "A deep cut"),
                         ("drill me on bleeding", "A deep cut"), ("help me practice the choking drill",
                                                                  "Choking at dinner")):
        assert floor.detect(words) is None, words
        assert drills.reply(None, EMPTY, words).startswith(f"Drill: {title}."), words
    assert drills.reply(None, EMPTY, "give me a first aid drill").startswith("Drill: ")


def test_words_that_say_it_is_real_still_get_the_floor():
    for words, kind in (("he is choking this is not a drill", "choking"), ("my son is choking, not a drill", "choking"),
                        ("help, she is choking", "choking"), ("my dad is bleeding badly", "bleeding"),
                        ("choking drill? no, she's choking for real", "choking")):
        assert floor.detect(words) == kind, words
    assert drills.reply(None, EMPTY, "I cut my finger, it's bleeding a lot") is None


def test_each_question_has_one_best_and_the_drills_say_what_the_floor_says():
    cut, choking = drills.by_id("deep_cut"), drills.by_id("choking")
    for drill in (cut, choking):
        assert drill.program == "bushcraft" and "the emergency number" in drill.situation
        for question in drill.questions:
            assert [c.verdict for c in question.choices].count("best") == 1, question.ask
    said = dict((kind, do) for kind, _words, do in floor.KINDS)
    assert "2 to 3 inches above the wound" in said["bleeding"] and "2 to 3 inches above the wound" in \
        drills.judge(cut, 3, 0)["best"]
    assert "5 firm back blows" in said["choking"] and "5 firm back blows" in drills.judge(choking, 2, 0)["best"]
    every = " ".join(c.why + c.text for d in (cut, choking) for q in d.questions for c in q.choices).lower()
    assert " mg" not in every and "dose" not in every  # no medicine doses: those are the emergency operator's
