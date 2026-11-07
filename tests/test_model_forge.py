"""
tests.test_model_forge
========================

MIA's model forge (core/model_forge.py, DEC-0106): the features, a router
that learns from its tools' own words and is scored honestly on requests it
never saw, its card, and saving and loading it.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from core import model_forge as mf


def _tool(name, description, phrases=(), subjects=()):
    """A stand-in for an AssistantAction: just the words the router learns from."""
    return SimpleNamespace(name=name, description=description, trigger_phrases=phrases, subjects=subjects)


TOOLS = [
    _tool("log_eggs", "Log eggs collected from the flock.", ("collected eggs", "got eggs"), ("egg", "hen")),
    _tool("get_weather", "The weather forecast for today and the week.", ("weather", "will it rain"),
          ("rain", "forecast")),
    _tool("add_expense", "Record money spent.", ("i spent", "i paid", "log a purchase"), ("expense", "spent")),
]
HELD_OUT = [mf.Example("I got twelve eggs from the hens", "log_eggs"),
            mf.Example("Is it going to rain tomorrow?", "get_weather"),
            mf.Example("I paid 40 for gas", "add_expense"),
            mf.Example("What's the forecast this week?", "get_weather"),
            mf.Example("Water the tomatoes", "water_plants")]  # a tool it never learned


def test_features_are_stems_and_pairs():
    """Little words go, stems meet ("logged" and "logs"), and neighbouring words pair up."""
    assert mf.features("I logged the eggs") == ["logg", "egg", "logg_egg"]
    assert mf.features("logs")[0] == mf.features("log")[0] == "log"
    assert mf.features("") == []


def test_the_router_learns_from_the_tools_words_only():
    """Nothing a person said is in the training set; it still picks the right tool for new words."""
    training = mf.examples_from_actions(TOOLS)
    assert {e.text for e in training} >= {"log eggs", "Log eggs collected from the flock.", "will it rain", "hen"}
    model = mf.Router().train(training, epochs=300)
    assert model.scores("I got twelve eggs from the hens")[0][0] == "log_eggs"
    assert model.scores("will it rain tomorrow", top=2)[0][0] == "get_weather"
    assert mf.Router().train(training, epochs=300).scores("eggs") == model.scores("eggs")  # same data, same model
    scored = mf.evaluate(model, HELD_OUT)
    assert scored["tested"] == 4 and scored["unknown_tools"] == 1 and scored["top5"] == 1.0


def test_forging_keeps_a_card_scored_on_the_half_that_chose_nothing(tmp_path):
    """Settings are chosen on one half of the held-out requests and the card's score comes from the other half;
    the model is saved, loads the same, and isn't in use."""
    choose, report = mf.split(HELD_OUT)
    assert choose == HELD_OUT[0::2] and report == HELD_OUT[1::2] and not set(map(id, choose)) & set(map(id, report))
    card = mf.forge_router(TOOLS, HELD_OUT, name="tiny", folder=tmp_path, baseline=1.0,
                           settings=((50, 4.0, 1e-4), (300, 4.0, 1e-4)))
    assert card["tested_on"]["examples"] == 2 and card["settings"]["chosen_on"] == 3  # the unknown tool fell in this half
    assert card["in_use"] is False and card["keyword_router"]["offers_the_tool"] == 1.0
    assert json.loads((tmp_path / "tiny" / "card.json").read_text(encoding="utf-8"))["name"] == "tiny"
    again = mf.Router.load(tmp_path / "tiny")
    assert again.scores("got eggs") == mf.Router().train(mf.examples_from_actions(TOOLS), *map(
        lambda k: card["settings"][k], ("epochs", "rate", "l2"))).scores("got eggs")
    assert [c["name"] for c in mf.cards(tmp_path)] == ["tiny"]
    assert mf.cards(tmp_path / "none") == []


def test_an_empty_training_set_is_refused():
    """With nothing to learn from, it says so."""
    import pytest

    with pytest.raises(ValueError):
        mf.Router().train([])


def test_every_specialist_in_the_playbook_serves_real_loops():
    """The playbook names loops that exist (a renamed loop would leave a specialist serving nothing), and the router
    is the one kind the forge can make today."""
    from core.loops import LOOPS

    ids = {l.id for l in LOOPS}
    assert not [(s.kind, x) for s in mf.PLAYBOOK for x in s.serves if x not in ids]
    assert [s.kind for s in mf.PLAYBOOK if s.built] == ["router"]
    assert mf.specialists_for("inbox.reading")[0].kind in ("classifier", "extractor")
    assert mf.specialists_for("answers.no_tool")[0].kind == "router"  # built ones first
    assert mf.specialists_for("pc.disk") == []  # no model frees disk space


def test_opportunities_are_slipping_loops_a_model_could_move(tmp_path):
    """Only loops below their floor or sliding, only those a kind of model serves, below the floor first, with the
    models already assigned to each."""
    mf.forge_router(TOOLS, HELD_OUT, name="tiny", folder=tmp_path, settings=((50, 4.0, 1e-4),),
                    serves=("loop:answers.no_tool", "project:P-0001"))
    rows = [{"id": "answers.no_tool", "what": "no tool", "state": "slid", "why": "up"},
            {"id": "inbox.reading", "what": "fields corrected", "state": "below", "why": "over"},
            {"id": "answers.thumbs", "what": "rated", "state": "ok"},
            {"id": "pc.disk", "what": "free space", "state": "below"}]
    found = mf.opportunities(rows, tmp_path)
    assert [o["loop"] for o in found] == ["inbox.reading", "answers.no_tool"]
    assert found[1]["assigned"] == ["tiny"] and found[0]["assigned"] == []
    assert [c["name"] for c in mf.assigned_to("project:P-0001", tmp_path)] == ["tiny"]


def test_the_shadow_notes_the_routers_picks_and_never_gets_in_the_way(tmp_path):
    """With a router saved, shadow_picks names its top tools (using the domains the request names); with none, or
    when anything fails, it's empty. shadow_record scores it only on turns where a tool was called."""
    mf.forge_router(TOOLS, HELD_OUT, name="router", folder=tmp_path, settings=((300, 4.0, 1e-4),))
    named = SimpleNamespace(named_domains=lambda prompt, context: set())
    context = SimpleNamespace(assistant_actions=named)
    picks = mf.shadow_picks(context, "I got eggs from the hens", folder=tmp_path / "router")
    assert picks[0] == "log_eggs" and len(picks) == 3
    assert mf.shadow_router(tmp_path / "router") is mf.shadow_router(tmp_path / "router")  # loaded once
    assert mf.shadow_picks(context, "eggs", folder=tmp_path / "none") == []
    broken = SimpleNamespace(assistant_actions=SimpleNamespace(named_domains=None))  # calling it fails
    assert mf.shadow_picks(broken, "eggs", folder=tmp_path / "router") == []
    traces = [{"shadow": ["log_eggs", "add_expense"], "tools_called": ["log_eggs"]},
              {"shadow": ["add_expense", "log_eggs"], "tools_called": ["log_eggs"]},
              {"shadow": ["get_weather"], "tools_called": ["add_expense"]},
              {"shadow": ["get_weather"], "tools_called": []},  # no tool called: not judged
              {"tools_called": ["log_eggs"]}]  # before the router: not judged
    assert mf.shadow_record(traces) == {"turns": 3, "top1": 0.333, "top5": 0.667}
    assert mf.shadow_record([]) == {"turns": 0, "top1": None, "top5": None}
