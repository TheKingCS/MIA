"""
tests.test_catch_log
======================

His catch log (core/catch_log.py): a fish kept in his own history with only what he said, a personal best said the
moment it's one, what's been biting from his own catches, the Angler achievement at once, and the page and voice.
"""

from core import catch_log, progress_history
from core.actions import ACTION_TYPES, ActionCenter
from core.rewards_manager import RewardsManager
from tests.engine_world import build_world


def _world(tmp_path, monkeypatch):
    """The engine's household with rewards (the Angler chain) and unlocks kept."""
    world = build_world(tmp_path, monkeypatch)
    world.rewards = RewardsManager(world)
    progress_history.subscribe(world)
    return world


def test_a_catch_is_kept_and_a_personal_best_is_said(tmp_path, monkeypatch):
    """The first bass with a size is the one to beat; a longer one is the biggest yet; a smaller one isn't; First Fish
    unlocks at once."""
    world = _world(tmp_path, monkeypatch)
    first = catch_log.log(world, "bass", length="16", where="the pond", bait="jig")
    assert "the one to beat" in first and world.rewards.is_unlocked(world.me.profile_id, "angler_first_fish")
    assert "biggest bass yet (the last was 16 in)" in catch_log.log(world, "bass", length=18.5)
    assert "biggest" not in catch_log.log(world, "bass", length=12)
    assert catch_log.count(world) == 3


def test_whats_biting_is_read_from_his_own_catches(tmp_path, monkeypatch):
    """Counts by species, the bait and spot that did best, and the personal bests."""
    world = _world(tmp_path, monkeypatch)
    for species, length, bait, where in (("bass", 18, "jig", "the pond"), ("bass", 14, "jig", "the pond"),
                                         ("bluegill", 7, "worm", "the creek")):
        catch_log.log(world, species, length=length, bait=bait, where=where)
    said = catch_log.say(world)
    assert "You've logged 3 fish this year: 2 bass, 1 bluegill." in said
    assert "Most came on jig (2)." in said and "Your best spot: the pond (2)." in said
    assert "bass 18 in" in said and "bluegill 7 in" in said
    assert catch_log.say(build_world(tmp_path / "other", monkeypatch)).startswith("No catches logged yet")


def test_from_the_page_it_asks_first_and_undo_takes_it_back(tmp_path, monkeypatch):
    """catch.log refuses no species; approved, it's logged and on the page; undone, it's gone."""
    import pytest

    from core.actions import ActionError
    from core.web_more import _catch_card

    world = _world(tmp_path, monkeypatch)
    with pytest.raises(ActionError):
        ACTION_TYPES["catch.log"].describe(world, {"species": ""})
    center = ActionCenter()
    proposal = center.propose(world, "catch.log", {"species": "walleye", "length": 22, "where": "the river"})
    center.approve(world, proposal.proposal_id)
    card = _catch_card(world)
    assert card["count"] == 1 and card["latest"][0]["species"] == "walleye"
    center.undo(world, proposal.proposal_id)
    assert catch_log.count(world) == 0
