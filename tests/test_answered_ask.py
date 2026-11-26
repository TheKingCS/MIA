"""
tests.test_answered_ask
=========================

His bare answer to her own last question made whole (core/conversation_state.answered_ask, brainstorm round 19):
"5 gallons" after "How much fuel?", "half a gallon an hour" after her burn-rate ask, his town after "I don't know
your town yet"; never when she didn't ask it, never a no or a question.
"""

from types import SimpleNamespace

from core.conversation_state import answered_ask


def _after(said):
    """A conversation whose last message is hers."""
    return SimpleNamespace(messages=[SimpleNamespace(role="user", content="q"), SimpleNamespace(role="assistant",
                                                                                             content=said)])


def test_the_bare_answers_made_whole():
    fuel = _after('How much fuel? Say it in gallons, or pounds of propane, like "5 gallons".')
    assert answered_ask(fuel, "5 gallons") == "How long would the generator run on 5 gallons?"
    assert answered_ask(fuel, "about 20 lbs of propane") == "How long would the generator run on 20 lbs of propane?"
    rate = _after('Tell me, like "my generator burns half a gallon an hour", and I\'ll keep it.')
    assert answered_ask(rate, "about 0.6 gallons an hour") == "My generator burns 0.6 gallons an hour"
    town = _after('I don\'t know your town yet. Tell me which one, like "my town is Springfield, Illinois".')
    assert answered_ask(town, "Springfield, Illinois") == "My town is Springfield, Illinois"
    assert answered_ask(town, "I live in Bowling Green") == "My town is Bowling Green"


def test_never_without_her_ask_or_for_a_no():
    town = _after("I don't know your town yet.")
    for said in ("no thanks", "why do you need it?", "forget it", "I'd rather not say where I live right now"):
        assert answered_ask(town, said) is None, said
    assert answered_ask(_after("Done."), "5 gallons") is None


def test_the_work_outside_question_is_her_forecasts_words():
    from core import assistant_turn

    pattern = next(p for n, p, _w in assistant_turn._OWN_TOOLS if n == "work_outside_wind_chill_heat_index")
    for words in ("Is it a good day to work outside?", "can I work outside tomorrow?", "is it too cold to work outside?"):
        assert pattern.match(words), words
    assert not pattern.match("is it a good day to work outside if it rains?")
