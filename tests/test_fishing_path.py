"""
tests.test_fishing_path
=========================

Fishing basics (core/fishing_path.py, 2026-11-25): the course is registered with its stages and checks; its counted
checks read his own catch log (a catch, a species); "what size hook for bass?" and "how do I tie a palomar knot?" are
answered from its lessons, never a wall hook or the fish tank. Soldering and the meter (core/soldering_path.py)
too: its how-tos from its own lessons, never a copper pipe. The Fable check of both: never mains, a hook in a
hand, a bass guitar or a crochet hook; their own how-tos found (an iron's heat, amps, a license, where fish hold).
"""

from core import lesson_answer, paths


def test_the_course_is_registered_with_three_stages():
    program = paths.program_of(None, "fishing")
    assert program is not None and program.skill == "fishing" and len(program.stages) == 3
    sources = {c.source for s in program.stages for c in s.checks if c.how == "recorded"}
    assert sources <= set(paths.SOURCES)


def test_its_how_tos_are_answered_from_its_lessons():
    assert lesson_answer.find("what size hook for bass?") == ("fishing", "hooks")
    assert lesson_answer.find("what hook should I use for catfish") == ("fishing", "hooks")
    assert lesson_answer.find("how do I tie a palomar knot?") == ("fishing", "knots")
    assert lesson_answer.find("how do I tie on a hook") == ("fishing", "knots")
    assert lesson_answer.find("how do I set up a texas rig") == ("fishing", "rigs")
    assert lesson_answer.find("how do I fillet a crappie") == ("fishing", "cleaning")
    said = lesson_answer.reply(None, "what size hook for bass?")
    assert said.startswith('From the Fishing basics course, "Hook sizes":') and "2/0 to 4/0" in said


def test_a_wall_hook_or_the_fish_tank_is_no_fishing_lesson():
    for words in ("what size hooks for the garage wall?", "how do I clean the fish tank",
                  "how do I hook up the trailer", "how do I tie a tie"):
        found = lesson_answer.find(words)
        assert found is None or found[0] != "fishing", words


def test_its_counted_checks_read_his_catches(monkeypatch):
    from core import catch_log

    monkeypatch.setattr(catch_log, "catches", lambda c: [
        {"species": "Bass", "at": "2026-11-20T10:00:00"}, {"species": "bass", "at": "2026-11-21T10:00:00"},
        {"species": "Bluegill", "at": "2026-11-22T10:00:00"}, {"species": "Crappie", "at": "2026-10-01T10:00:00"}])
    assert paths.SOURCES["catches"].read(None, "2026-11-01") == 3
    assert paths.SOURCES["species"].read(None, "2026-11-01") == 2


def test_soldering_and_the_meter_are_their_own_course():
    """Soldering and the multimeter have their own course; a pipe's solder is plumbing's."""
    assert lesson_answer.find("how do I solder the headers on my nano?") == ("soldering", "joints")
    assert lesson_answer.find("how do I fix a solder bridge?") == ("soldering", "fixing")
    assert lesson_answer.find("how do I use a multimeter?") == ("soldering", "meter")
    assert lesson_answer.find("how do I solder copper pipe?") is None
    said = lesson_answer.reply(None, "how do I solder?")
    assert said.startswith('From the Soldering and the meter course, "Solder a joint')


def test_a_bridge_over_the_creek_is_no_soldering_lesson():
    for words in ("how do I build a bridge over the creek", "how do I fix the bridge on my guitar"):
        found = lesson_answer.find(words)
        assert found is None or found[0] != "soldering", words


def test_the_courses_never_take_what_isnt_theirs():
    """The Fable check of the courses (2026-11-25): mains, a hook in a hand, a bass guitar, a crochet hook, a gas
    line's solder and business continuity are never these lessons; their own how-tos are."""
    for words in ("how do I check the voltage at an outlet?", "how do I check the voltage in my breaker panel",
                  "how do I test the voltage on my car battery", "how do I get the hook out of my hand",
                  "how do I get the hook out of my dog's mouth", "how do I unhook the trailer",
                  "what size hook for crochet?", "what size hooks do I need to hang a 40 lb mirror?",
                  "how do I rig a bass guitar pickup", "how do I clean my bass guitar", "how do I clean my fish pond",
                  "how do I release a bass track on spotify", "how do I solder a 3/4 inch water line",
                  "how do I solder battery tabs on 18650 cells", "how do I desolder a copper fitting",
                  "how do I keep continuity in my story", "how do I clinch the deal"):
        found = lesson_answer.find(words)
        assert found is None or found[0] not in ("fishing", "soldering"), words
    for words, key in (("how hot should my soldering iron be?", ("soldering", "joints")),
                       ("how do I fix a cold joint", ("soldering", "fixing")),
                       ("how do I measure amps with a multimeter?", ("soldering", "meter")),
                       ("how do I test a resistor", ("soldering", "meter")),
                       ("how do I take the hook out of a bluegill", ("fishing", "release")),
                       ("how do I skin a catfish", ("fishing", "cleaning")),
                       ("how do I set up a bobber", ("fishing", "rigs")),
                       ("do I need a fishing license?", ("fishing", "rules")),
                       ("where should I fish for bass in the summer?", ("fishing", "reading_water"))):
        assert lesson_answer.find(words) == key, words
    assert "in series" in lesson_answer.reply(None, "how do I measure amps with a multimeter?")
