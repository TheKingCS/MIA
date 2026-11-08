"""
tests.test_dungeon_master
===========================

Living Worlds Phase 2 (core/dungeon_master.py, DEC-0134): a playable turn where the model proposes and code
validates/commits. The model's intents only change state when they pass their check; a quest, item or skill is
committed to the store; the turn records a fictional event (DEC-0137), never real XP; the model can never write
state itself; and each turn is kept as the story so far, the last few fed back to the DM for continuity.
"""

import json

import pytest

from core.dungeon_master import Intent, TurnResult, take_turn, validate
from core.living_worlds import LivingWorldsBook


@pytest.fixture
def game(tmp_path):
    """A campaign ready to play: a high-fantasy universe, its campaign, and Kael's version in it; returns the book, the campaign, the version and the folder."""
    book = LivingWorldsBook(data_dir=tmp_path)
    u = book.create_universe("Aethelgard", genre="high fantasy")
    c = book.create_campaign(u.universe_id, "The Shattered Crown")
    hero = book.create_character("Kael")
    v = book.create_version(hero.character_id, u.universe_id, c.campaign_id, "Kael the Warden",
                            skills=["lockpicking"], attributes={"agility": 3})
    return book, c, v, tmp_path


def _propose(narration, intents):
    """A stub model that always proposes the same thing."""
    return lambda state, action: {"narration": narration, "intents": intents}


def test_an_uncontested_intent_commits_and_the_turn_narrates(game):
    book, c, v, _ = game
    propose = _propose("You pocket the gleaming key.", [{"kind": "gain_item", "params": {"item": "brass key"}}])
    result = take_turn(book, c.campaign_id, v.version_id, "I take the key", propose, roll=lambda: 0.5)
    assert isinstance(result, TurnResult) and result.narration.startswith("You pocket")
    assert result.committed == ["Gained: brass key"]
    assert "brass key" in book.get_version(v.version_id).inventory


def test_a_contested_intent_needs_the_dice(game):
    book, c, v, _ = game
    propose = _propose("You try the lock.", [{"kind": "learn_skill", "params": {"skill": "safecracking"}, "check": 18}])
    fail = take_turn(book, c.campaign_id, v.version_id, "crack it", propose, roll=lambda: 0.1)  # d20 ~3, +0 edge
    assert fail.committed == [] and fail.failed and "safecracking" not in book.get_version(v.version_id).skills
    win = take_turn(book, c.campaign_id, v.version_id, "crack it", propose, roll=lambda: 0.99)  # d20 ~20
    assert win.committed == ["Learned: safecracking"]


def test_the_edge_from_an_attribute_and_skill_helps_the_check(game):
    book, c, v, _ = game
    # agility 3 + has "lockpicking" = +4; a middling roll then clears a moderate check
    picking = Intent(kind="narrate", params={"attribute": "agility", "skill": "lockpicking"}, check=15)
    assert validate(picking, book.get_version(v.version_id), roll=0.6) is True   # d20 ~13 + 4 = 17 >= 15
    assert validate(Intent("narrate", check=15), book.get_version(v.version_id), roll=0.6) is False  # 13 + 0 < 15
    assert validate(Intent("narrate", check=None), book.get_version(v.version_id), roll=0.0) is True  # no check


def test_a_quest_is_completed_through_the_turn(game):
    book, c, v, _ = game
    q = book.assign_quest(c.campaign_id, "Recover the Sunstone")
    propose = _propose("The Sunstone is yours.", [{"kind": "complete_quest", "params": {"quest_id": q.quest_id}}])
    result = take_turn(book, c.campaign_id, v.version_id, "grab it", propose, roll=lambda: 0.5)
    assert result.committed == ["Quest complete: Recover the Sunstone"]
    assert book.get_quest(q.quest_id).status == "done"


def test_the_turn_records_a_fictional_event_and_never_real_state(game):
    book, c, v, tmp_path = game
    propose = _propose("A quiet moment.", [{"kind": "narrate"}])
    take_turn(book, c.campaign_id, v.version_id, "look around", propose, roll=lambda: 0.5)
    events = [json.loads(x) for x in (tmp_path / "life_events.jsonl").read_text(encoding="utf-8").splitlines() if x]
    turn_events = [e for e in events if e["type"] == "campaign_turn"]
    assert turn_events and all(e.get("environment") == "fictional" for e in turn_events)


def test_an_unknown_campaign_is_refused(game):
    book, c, v, _ = game
    with pytest.raises(ValueError):
        take_turn(book, "nope", v.version_id, "x", _propose("", []))


def test_the_model_reply_parser_extracts_intents_or_falls_back_to_narration():
    from core.dungeon_master import _parse

    good = _parse('blah {"narration": "You open the door.", "intents": [{"kind": "gain_item", "params": {"item": "lamp"}}]} end')
    assert good["narration"] == "You open the door." and good["intents"][0]["kind"] == "gain_item"
    plain = _parse("just a sentence, no json")
    assert plain["narration"] == "just a sentence, no json" and plain["intents"] == []
    assert _parse("{bad json") ["intents"] == []


def test_each_turn_is_kept_as_the_story_so_far_and_fed_back_for_continuity(game):
    book, c, v, _ = game
    seen = []

    def propose(state, action):
        seen.append(state["recent_turns"])
        return {"narration": f"You {action}.", "intents": [{"kind": "gain_item", "params": {"item": "torch"}}]}

    take_turn(book, c.campaign_id, v.version_id, "light the torch", propose, roll=lambda: 0.5)
    take_turn(book, c.campaign_id, v.version_id, "walk on", propose, roll=lambda: 0.5)
    assert seen[0] == [] and seen[1] == [{"action": "light the torch", "narration": "You light the torch."}]
    story = book.turns_in(c.campaign_id)
    assert [t["action"] for t in story] == ["light the torch", "walk on"] and story[0]["committed"] == ["Gained: torch"]
    assert [t["action"] for t in LivingWorldsBook(data_dir=book.data_dir).turns_in(c.campaign_id)] == \
        ["light the torch", "walk on"]  # survives a restart


def test_the_story_keeps_only_the_newest_turns(game, monkeypatch):
    import core.living_worlds as lw

    book, c, v, _ = game
    monkeypatch.setattr(lw, "TURNS_KEPT", 3)
    for i in range(5):
        book.record_turn(c.campaign_id, v.version_id, f"step {i}", "")
    assert [t["action"] for t in book.turns_in(c.campaign_id)] == ["step 2", "step 3", "step 4"]
    assert [t["action"] for t in book.turns_in(c.campaign_id, limit=1)] == ["step 4"]
    with pytest.raises(ValueError):
        book.record_turn("nope", v.version_id, "x", "")
