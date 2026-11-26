"""
tests.test_her_asks
=====================

His bare answer to her own last question finished in code (core/her_asks, brainstorm round 19): the generator's fuel
and burn rate, his town (only when found, never a command of his), and "is it a good day to work outside?" said in
her forecast's own words so her ask reaches him as hers.
"""

from types import SimpleNamespace

from core import assistant_turn, her_asks


def test_fuel_and_burn_rate(monkeypatch):
    from core import assistant_today_actions, homestead_sums

    monkeypatch.setattr(homestead_sums, "generator_runtime", lambda c, w: f"runtime[{w}]")
    assert her_asks.reply(SimpleNamespace(), her_asks.FUEL_ASK + ", or pounds", "5 gallons") == "runtime[5 gallons]"
    assert her_asks.reply(SimpleNamespace(), her_asks.FUEL_ASK, "a half gallon") == "runtime[half a gallon]"
    assert her_asks.reply(SimpleNamespace(), her_asks.FUEL_ASK, "remind me to buy gas") is None
    kept = []
    monkeypatch.setattr(assistant_today_actions, "_action_set_preparedness", lambda c, a: kept.append(a) or "Kept.")
    assert her_asks.reply(SimpleNamespace(), "Tell me, " + her_asks.RATE_ASK, "about .5 gallons an hour") == "Kept."
    assert her_asks.reply(SimpleNamespace(), her_asks.RATE_ASK, "half a gallon an hour") == "Kept."
    assert kept == [{"generator_gph": 0.5}, {"generator_gph": 0.5}]


def test_a_town_only_when_found_and_never_a_command():
    ran = []

    def execute(c, name, args):
        """Finds Springfield only."""
        ran.append(args["place"])
        return "The weather is for Springfield, Illinois now." if "Springfield" in args["place"] else \
            "I couldn't find a town by that name. Try adding the state or country."
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=execute))
    ask = her_asks.TOWN_ASK + '. Tell me which one, like "my town is Springfield, Illinois".'
    assert her_asks.reply(context, ask, "Springfield, Illinois") == "The weather is for Springfield, Illinois now."
    assert her_asks.reply(context, ask, "Go Bears") is None
    for said in ("undo that", "remind me to call mom", "turn off the lights", "my wife", "Home", "Yeah",
                 "my town is Springfield, Illinois", "whats for dinner", "I'm in a meeting"):
        assert her_asks.reply(context, ask, said) is None, said
    assert ran == ["Springfield, Illinois", "Go Bears"]
    assert her_asks.reply(context, ask, "I live in Springfield") == "The weather is for Springfield, Illinois now."


def test_the_work_outside_question_is_her_forecasts_words():
    pattern = next(p for n, p, _w in assistant_turn._OWN_TOOLS if n == "work_outside_wind_chill_heat_index")
    for words in ("Is it a good day to work outside?", "can I work outside tomorrow?", "is it too cold to work outside?"):
        assert pattern.match(words), words
    assert not pattern.match("is it a good day to work outside if it rains?")
