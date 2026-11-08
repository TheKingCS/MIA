"""How MIA answers (DEC-0138): offering an answer two ways, the facts checked, the picks and the screen, and the voice
tools that run the same style.* actions."""

from datetime import date
from types import SimpleNamespace

import pytest

import core.answer_compare as ac
from core.actions import ACTION_TYPES, ActionError
from core.response_style import StyleBook

REPLY = ("Your truck's oil change is due in 300 miles, and the tires were rotated on March 4. "
         "The air filter is fine for another 2,000 miles, so only the oil needs booking this week.")


@pytest.fixture
def person(tmp_path, monkeypatch):
    """A person with an empty style store; settings kept in a dict."""
    import core.person_settings as ps

    store = {}
    monkeypatch.setattr(ps, "get", lambda context, key, default=None: store.get(key, default))
    monkeypatch.setattr(ps, "put", lambda context, key, value: store.__setitem__(key, value))
    ctx = SimpleNamespace(settings=store)
    ctx.response_style = StyleBook(ctx, data_dir=tmp_path)
    return ctx


def act(ctx, kind, **params):
    """Runs an action as the approval flow would."""
    ACTION_TYPES[kind].describe(ctx, params)
    return ACTION_TYPES[kind].execute(ctx, params)


def test_a_rephrasing_that_changes_or_invents_a_number_is_never_shown():
    assert ac.same_facts(REPLY, "Oil change due in 300 miles; tires rotated March 4; air filter good for 2,000 more.")
    assert not ac.same_facts(REPLY, "Oil change due in 500 miles.")
    assert not ac.same_facts(REPLY, "")
    assert not ac.same_facts(REPLY, "  " + REPLY + " ")


def test_an_offer_comes_at_most_once_a_day_and_never_when_private_short_or_turned_off(person):
    today = date(2026, 11, 8)
    assert ac.plan(person, "Sure.", today) is None
    assert ac.plan(person, REPLY, today, private=True) is None
    experiment = ac.plan(person, REPLY, today)
    assert experiment["dimension"] in ("length", "format", "tone", "lead") and experiment["a"] != experiment["b"]
    offer = ac.keep(person, experiment, REPLY, "Oil: 300 miles. Tires: done March 4. Filter: 2,000 miles left.", today)
    assert {w["value"] for w in offer["ways"]} == {experiment["a"], experiment["b"]} and offer["question"]
    assert ac.plan(person, REPLY, today) is None  # already offered today
    assert ac.plan(person, REPLY, date(2026, 11, 9)) is not None
    act(person, "style.compare", on=False)
    assert ac.plan(person, REPLY, date(2026, 11, 10)) is None


def test_restyle_asks_the_model_once_and_drops_a_reply_that_changed_a_fact(person):
    asked = []
    ok = ac.restyle(lambda p: asked.append(p) or "Oil in 300 miles; tires March 4; filter 2,000.", REPLY, "length", "brief")
    assert ok and "one or two sentences" in asked[0] and REPLY in asked[0]
    assert ac.restyle(lambda p: "Oil in 250 miles.", REPLY, "length", "brief") == ""
    assert ac.restyle(lambda p: (_ for _ in ()).throw(RuntimeError("down")), REPLY, "length", "brief") == ""


def test_picking_one_records_it_over_the_other_and_closes_the_offer(person):
    today = date(2026, 11, 8)
    experiment = ac.plan(person, REPLY, today)
    offer = ac.keep(person, experiment, REPLY, "Oil: 300 miles. Tires: March 4. Filter: 2,000 miles.", today)
    act(person, "style.pick", chosen=experiment["b"], offer_id=offer["id"])
    [pick] = person.response_style.picks
    assert (pick.dimension, pick.chosen, pick.rejected) == (experiment["dimension"], experiment["b"], experiment["a"])
    with pytest.raises(ActionError, match="already been made"):
        ACTION_TYPES["style.pick"].describe(person, {"chosen": experiment["a"], "offer_id": offer["id"],
                                                     "dimension": experiment["dimension"]})


def test_choosing_outright_wins_at_once_and_forget_clears_everything(person):
    for _ in range(3):
        person.response_style.record_pick("length", "detailed", "brief")
    act(person, "style.set", dimension="length", value="brief")
    assert person.response_style.preferred("length") == "brief"
    page = ac.screen(person)
    length = next(d for d in page["dimensions"] if d["id"] == "length")
    assert length["preferred"] == "brief" and length["picks"] == 1 and "short" in page["instruction"]
    with pytest.raises(ActionError):
        ACTION_TYPES["style.set"].describe(person, {"dimension": "length", "value": "huge"})
    act(person, "style.reset")
    assert person.response_style.picks == [] and ac.screen(person)["instruction"] == ""
    with pytest.raises(ActionError, match="nothing learned"):
        ACTION_TYPES["style.reset"].describe(person, {})


def test_the_voice_tools_map_the_persons_words_in_code(person):
    from core.assistant_answer_style_actions import register_answer_style_actions, wanted
    from core.assistant_actions import AssistantActionRegistry

    assert wanted("keep your answers short") == ("length", "brief")
    assert wanted("no bullets please") == ("format", "prose")
    assert wanted("use bullet points") == ("format", "bulleted")
    assert wanted("lead with the answer") == ("lead", "answer_first")
    assert wanted("sing it") is None
    reg = AssistantActionRegistry()
    register_answer_style_actions(reg)
    run = lambda name, **args: reg._actions[name].handler(person, args)  # noqa: E731
    assert "haven't learned" in run("get_answer_style")
    assert "from now on" in run("set_answer_style", how="be more direct")
    assert "tone: direct" in run("get_answer_style")
    assert "won't ask" in run("answer_two_ways", on=False)
    assert "Which would you like" in run("set_answer_style", how="sing it")
