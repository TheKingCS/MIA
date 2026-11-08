"""Living Worlds on the web (DEC-0134 Phases 1 and 2): the screen, its world.* actions (playing a turn too) and the
voice tools, all fiction."""

from types import SimpleNamespace

import pytest

import core.web_worlds as ww
from core.actions import ACTION_TYPES, ActionError
from core.living_worlds import LivingWorldsBook


@pytest.fixture
def person(tmp_path):
    """A person with an empty Living Worlds store."""
    ctx = SimpleNamespace()
    ctx.living_worlds = LivingWorldsBook(ctx, data_dir=tmp_path)
    return ctx


def act(ctx, kind, **params):
    """Runs an action as the approval flow would."""
    ACTION_TYPES[kind].describe(ctx, params)
    return ACTION_TYPES[kind].execute(ctx, params)


def test_an_empty_store_shows_no_worlds_no_character_and_the_play_note(person):
    page = ww.screen(person)
    assert page["available"] and page["worlds"] == [] and page["character"] is None and page["campaign"] is None
    assert "dice decide" in page["phase_note"] and set(page["forms"]) == {"universe", "campaign", "character", "version", "quest"}


def test_a_world_a_campaign_a_character_and_their_version_are_made_through_actions(person):
    act(person, "world.universe_add", name="Emberfall", genre="fantasy", premise="Salt towns.")
    uid = person.living_worlds.universes[0].universe_id
    act(person, "world.campaign_add", universe_id=uid, name="The Salt Road")
    cid = person.living_worlds.campaigns[0].campaign_id
    with pytest.raises(ActionError, match="character first"):
        ACTION_TYPES["world.version_add"].describe(person, {"campaign_id": cid, "name": "Wren"})
    act(person, "world.character_add", name="Wren")
    with pytest.raises(ActionError, match="already have Wren"):
        ACTION_TYPES["world.character_add"].describe(person, {"name": "Other"})
    act(person, "world.version_add", campaign_id=cid, name="Wren of the Marsh", origin="Gullmarsh")
    with pytest.raises(ActionError, match="already plays"):
        ACTION_TYPES["world.version_add"].describe(person, {"campaign_id": cid, "name": "Again"})
    page = ww.screen(person)
    assert page["campaign"]["name"] == "The Salt Road" and page["campaign"]["players"][0]["name"] == "Wren of the Marsh"
    assert page["character"]["versions"] == [{"name": "Wren of the Marsh", "world": "Emberfall"}]
    with pytest.raises(ActionError, match="isn't one of yours"):
        ACTION_TYPES["world.campaign_add"].describe(person, {"universe_id": "nope", "name": "X"})


def test_quests_are_set_by_the_player_finished_once_and_campaigns_pause_resume_and_end(person):
    act(person, "world.universe_add", name="Vanta Reach")
    act(person, "world.campaign_add", universe_id=person.living_worlds.universes[0].universe_id, name="Dead Signal")
    cid = person.living_worlds.campaigns[0].campaign_id
    assert "no real XP" in act(person, "world.quest_add", campaign_id=cid, name="Find the beacon")
    qid = person.living_worlds.quests[0].quest_id
    assert ww.screen(person)["campaign"]["quests"][0]["by"] == "You"
    act(person, "world.quest_done", quest_id=qid)
    with pytest.raises(ActionError, match="already finished"):
        ACTION_TYPES["world.quest_done"].describe(person, {"quest_id": qid})
    act(person, "world.campaign_status", campaign_id=cid, status="paused")
    assert ww.screen(person)["worlds"][0]["campaigns"][0]["status_word"] == "Paused"
    with pytest.raises(ActionError, match="already paused"):
        ACTION_TYPES["world.campaign_status"].describe(person, {"campaign_id": cid, "status": "paused"})
    act(person, "world.campaign_status", campaign_id=cid, status="active")
    act(person, "world.campaign_status", campaign_id=cid, status="ended")
    assert person.living_worlds.get_campaign(cid).status == "ended"


def test_the_voice_tools_make_and_find_by_name(person):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_world_actions import register_world_actions

    reg = AssistantActionRegistry()
    register_world_actions(reg)
    run = lambda tool, **args: reg._actions[tool].handler(person, args)  # noqa: E731
    assert "haven't made a world" in run("list_worlds")
    assert "exists now" in run("make_world", name="Emberfall", genre="fantasy")
    assert "Which world" in run("start_campaign", world="Narnia", name="X")
    assert "has begun" in run("start_campaign", world="emberfall", name="The Salt Road")
    assert "is set" in run("add_world_quest", name="Find the lost cartographer")  # the last played campaign
    assert "Emberfall, fantasy: The Salt Road (in play, 1 open quests)" in run("list_worlds")
    assert "finished" in run("finish_world_quest", quest="cartographer")
    assert "paused" in run("set_campaign_status", campaign="salt road", status="pause it")


def _ready(person):
    """Emberfall, The Salt Road in play, Wren in it as Wren of the Marsh with a quest; returns the campaign id."""
    act(person, "world.universe_add", name="Emberfall")
    uid = person.living_worlds.universes[0].universe_id
    act(person, "world.campaign_add", universe_id=uid, name="The Salt Road")
    cid = person.living_worlds.campaigns[0].campaign_id
    act(person, "world.character_add", name="Wren")
    act(person, "world.version_add", campaign_id=cid, name="Wren of the Marsh")
    act(person, "world.quest_add", campaign_id=cid, name="Find the cartographer")
    return cid


def test_a_turn_is_played_with_the_model_proposing_and_the_code_deciding(person, monkeypatch):
    import core.dungeon_master as dm

    cid = _ready(person)
    quest = person.living_worlds.quests[0]
    proposal = {"narration": "The lock gives; inside, a map under a knife.",
                "intents": [{"kind": "gain_item", "params": {"item": "a half-finished map"}},
                            {"kind": "complete_quest", "params": {"quest_id": quest.quest_id}, "check": 20}]}
    monkeypatch.setattr(dm, "model_proposer", lambda context: (lambda state, action: proposal))
    monkeypatch.setattr(dm.random, "random", lambda: 0.0)  # a 1 on the die: the contested quest fails
    assert ACTION_TYPES["world.turn"].describe(person, {"campaign_id": cid, "action": "I pick the lock"}) == \
        "Wren of the Marsh, in The Salt Road: I pick the lock"
    said = ACTION_TYPES["world.turn"].execute(person, {"campaign_id": cid, "action": "I pick the lock"}).split("\n")
    assert said == ["The lock gives; inside, a map under a knife.", "Gained: a half-finished map",
                    "Tried, but the dice said no: complete quest"]
    version = person.living_worlds.versions_in(cid)[0]
    assert version.inventory == ["a half-finished map"] and person.living_worlds.get_quest(quest.quest_id).status == "open"
    page = ww.screen(person, cid)
    assert page["campaign"]["players"][0]["inventory"] == ["a half-finished map"]
    assert page["campaign"]["story"][-1] == {"said": "I pick the lock", "lines": said}  # the book keeps the story


def test_a_turn_needs_a_campaign_in_play_a_character_in_it_and_something_done(person, monkeypatch):
    import core.dungeon_master as dm

    cid = _ready(person)
    with pytest.raises(ActionError, match="What do you do"):
        ACTION_TYPES["world.turn"].describe(person, {"campaign_id": cid, "action": "  "})
    act(person, "world.campaign_status", campaign_id=cid, status="paused")
    with pytest.raises(ActionError, match="pick it back up"):
        ACTION_TYPES["world.turn"].describe(person, {"campaign_id": cid, "action": "I wait"})
    uid = person.living_worlds.universes[0].universe_id
    act(person, "world.campaign_add", universe_id=uid, name="The Long Tide")
    other = [c for c in person.living_worlds.campaigns if c.name == "The Long Tide"][0].campaign_id
    with pytest.raises(ActionError, match="Bring your character"):
        ACTION_TYPES["world.turn"].describe(person, {"campaign_id": other, "action": "I wait"})
    act(person, "world.campaign_status", campaign_id=cid, status="active")
    monkeypatch.setattr(dm, "model_proposer", lambda context: (lambda state, action: {}))
    assert ACTION_TYPES["world.turn"].execute(person, {"campaign_id": cid, "action": "I wait"}).startswith(
        "MIA has no model running")


def test_playing_by_voice_runs_the_same_turn_in_the_last_played_campaign(person, monkeypatch):
    import core.dungeon_master as dm
    from core.assistant_world_actions import _action_play

    _ready(person)
    monkeypatch.setattr(dm, "model_proposer", lambda context: (lambda state, action: {"narration": "The ferryman nods."}))
    assert _action_play(person, {"action": "I ask the ferryman"}) == "The ferryman nods."
    monkeypatch.setattr(dm, "model_proposer", lambda context: (lambda state, action: {}))
    assert "no model running" in _action_play(person, {"action": "I wait", "campaign": "Salt Road"})
