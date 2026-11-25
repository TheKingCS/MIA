"""
tests.test_first_aid_drills
=============================

The first-aid drills (core/drills.py: a deep cut, choking at dinner), written in the emergency floor's words
(core/first_aid_floor.py) so a drill never teaches what the floor wouldn't say; asking for one never trips the floor,
and anything that says it's real still does, even with "practice" or "drill" in it (the sixth review); and a how-to
in other words (a radiator bled, stumps burned) or for an animal is never taught as first aid.
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


def test_practice_or_a_drill_named_in_a_real_emergency_never_quiets_the_floor():
    """The sixth review's cases: an emergency at practice, during a fire drill, or with the power drill still gets the
    floor; only a drill asked for is practice."""
    for words in ("she choked at soccer practice and can't breathe",
                  "he collapsed at football practice and isn't breathing", "kid not breathing at swim practice",
                  "he stopped breathing during practice", "coach collapsed at practice not breathing call 911",
                  "my son got stung at baseball practice and his throat is swelling",
                  "my son's choking at practice", "someone collapsed during the fire drill, no pulse",
                  "I cut my hand with the drill and it won't stop bleeding",
                  "my husband got hurt with the power drill, blood everywhere",
                  "stabbed my hand with the drill bleeding bad"):
        assert floor.detect(words) is not None, words


def test_a_how_to_in_other_words_or_for_an_animal_is_never_taught_as_first_aid():
    """The sixth review's cases get no first-aid steps; a person's still do."""
    for words in ("how do I bleed a radiator", "how can I bleed maple trees for syrup", "how should I burn the stumps",
                  "how to burn a cd", "how do I choke a chainsaw", "how do you choke up on a bat",
                  "how do I wound up a spring", "how do I treat a wound on my horse", "how do I bleed the brakes"):
        assert floor.teach(words) is None, words
    for words in ("how do you use a tourniquet?", "how to treat a burn", "how do I do CPR?",
                  "how do I stop bleeding?"):
        assert floor.teach(words) is not None, words


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
