"""
tests.test_first_aid_floor_never_misses
=========================================

Every real emergency phrasing the reviews found (2026-11-25, the sixth to ninth) reaches the emergency floor
(core/first_aid_floor.detect). Narrowing its words to quiet a false alarm had twice silenced real ones ("grandma fell
off the horse and isn't breathing", "dad has collapsed", "she choked at soccer practice and can't breathe"), so a
false alarm is the accepted cost (one careful message with the number), and this list only ever grows.
"""

from core import first_aid_floor as floor

REAL = (
    # at practice, with a drill (the sixth review)
    "she choked at soccer practice and can't breathe", "he collapsed at football practice and isn't breathing",
    "kid not breathing at swim practice", "coach collapsed at practice not breathing call 911",
    "my son got stung at baseball practice and his throat is swelling", "someone collapsed during the fire drill, no pulse",
    "I cut my hand with the drill and it won't stop bleeding", "my husband got hurt with the power drill, blood everywhere",
    # right after asking for a drill (the seventh)
    "give me a choking drill, baby can't breathe", "quiz me on first aid, my son fell and is unconscious",
    "start the first aid drill, someone's unconscious", "try a choking scenario, my kid can't breathe",
    # family words, every way they're said (the seventh and ninth)
    "grandma collapsed", "mom collapsed", "dad has collapsed", "DAD HAS COLLAPSED", "mom's collapsed", "mom's passed out",
    "mom's not waking up", "grandma's fainted", "dad collapsed help", "mom collapsed please help",
    "mom collapsed what do i do", "dad collapsed 911", "grandpa collapsed outside", "mom blacked out driving",
    "grandmother collapsed", "grandfather passed out", "my stepdad collapsed", "my stepmom passed out",
    # on the homestead, an animal named beside the person (the ninth)
    "grandma fell off the horse and isn't breathing", "mom got bit by a snake while feeding the chickens",
    "dad got kicked by the horse and is bleeding badly", "mom collapsed while feeding the chickens",
    # bleeding, every way it's said (the seventh and ninth)
    "bleeding won't stop", "cut my finger off", "my arm is gushing blood", "she cut her finger off a minute ago help",
    "he cut his finger off my god", "dad cut his thumb off the saw", "he cut his hand off of the bandsaw",
    "she's pouring blood in the scene of the accident",
    "we were watching a movie and he started gushing blood from his nose",
)


def test_every_real_emergency_the_reviews_found_reaches_the_floor():
    missed = [words for words in REAL if floor.detect(words) is None]
    assert missed == []


def test_a_drill_asked_for_alone_stays_practice():
    for words in ("give me a choking drill", "quiz me on first aid", "try a choking scenario", "run the deep cut drill"):
        assert floor.detect(words) is None, words
