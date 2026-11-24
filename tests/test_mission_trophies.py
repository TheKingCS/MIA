"""
tests.test_mission_trophies
=============================

A mission's rewards beyond XP and its objectives counted from records (core/mission_trophies.py, the game layer's
step 2): a structure, song or skill earned once on completion and kept in the history, a recipe unlocked, and "put
up 20 jars" counted from the jars logged after it was set, said ready to claim once, never completed for him.
"""

import pytest

from core import canning_shelf, life_events, mission_trophies, progress_history
from core.actions import ACTION_TYPES, ActionError
from core.rewards_manager import RewardsManager
from tests.engine_world import build_world


def _world(tmp_path, monkeypatch):
    """The engine's small household with rewards (the stats an objective counts) and unlocks kept in the history."""
    world = build_world(tmp_path, monkeypatch)
    world.rewards = RewardsManager(world)
    progress_history.subscribe(world)
    return world


def _trophies(world):
    """The trophy_earned events in the signed-in person's history, as (summary, kind)."""
    return [(e.summary, e.payload.get("kind")) for e in life_events.events_for(world, types=("trophy_earned",))]


def test_a_missions_trophies_are_earned_once_when_it_completes(tmp_path, monkeypatch):
    """A structure and a song on a mission are earned when it's completed, in the person's own history, and setting
    it back to active and completing it again earns nothing twice."""
    world = _world(tmp_path, monkeypatch)
    mission = world.missions.add_mission("Raise the coop", profile_id=world.me.profile_id)
    world.missions.add_trophy(mission.mission_id, "structure", "Chicken coop")
    world.missions.add_trophy(mission.mission_id, "song", "Wagon Wheel")
    assert _trophies(world) == []
    world.missions.update_mission(mission.mission_id, status="completed")
    assert sorted(_trophies(world)) == [("Song Unlocked: Wagon Wheel", "song"),
                                        ("Structure Built: Chicken coop", "structure")]
    world.missions.update_mission(mission.mission_id, status="active")
    world.missions.update_mission(mission.mission_id, status="completed")
    assert len(_trophies(world)) == 2


def test_a_bad_kind_or_a_finished_mission_is_refused(tmp_path, monkeypatch):
    """Only the six kinds, with a name, on a mission that isn't done."""
    world = _world(tmp_path, monkeypatch)
    mission = world.missions.add_mission("Learn to can", profile_id=world.me.profile_id)
    with pytest.raises(ValueError):
        world.missions.add_trophy(mission.mission_id, "trophy", "Gold cup")
    with pytest.raises(ValueError):
        world.missions.add_trophy(mission.mission_id, "skill", "  ")
    world.missions.update_mission(mission.mission_id, status="completed")
    with pytest.raises(ValueError):
        world.missions.add_trophy(mission.mission_id, "skill", "Canning")


def test_a_recipe_trophy_unlocks_its_kitchen_recipe(tmp_path, monkeypatch):
    """A recipe trophy whose ref is a Kitchen recipe unlocks it when the mission completes."""
    world = _world(tmp_path, monkeypatch)
    recipe = world.kitchen.add_recipe("Grandma's salsa")
    world.kitchen.update_recipe(recipe.recipe_id, locked=True)
    mission = world.missions.add_mission("Salsa season", profile_id=world.me.profile_id)
    world.missions.add_trophy(mission.mission_id, "recipe", "Grandma's salsa", recipe.recipe_id)
    world.missions.update_mission(mission.mission_id, status="completed")
    assert world.kitchen.get_recipe(recipe.recipe_id).locked is False


def test_an_objective_counted_from_records_counts_only_what_is_logged_after_it(tmp_path, monkeypatch):
    """Seven jars put up before "put up 10 jars" don't count; ten after it meet it, he's told once it's ready to
    claim, and the mission waits for his press."""
    world = _world(tmp_path, monkeypatch)
    canning_shelf.put_up(world.kitchen, "tomatoes", 7, "quarts")
    mission = world.missions.add_mission("Fill the shelf", profile_id=world.me.profile_id)
    world.missions.add_objective(mission.mission_id, "10 jars put up", "records", 10, stat_id="jars_canned")
    assert world.missions.objective_progress(mission.mission_id, 0) == 0
    canning_shelf.put_up(world.kitchen, "peaches", 6, "pints")
    assert world.missions.objective_progress(mission.mission_id, 0) == 6
    assert not world.missions.get_mission(mission.mission_id).ready_said
    canning_shelf.put_up(world.kitchen, "pickles", 4, "pints")
    again = world.missions.get_mission(mission.mission_id)
    assert again.ready_said and again.status == "active"
    assert mission_trophies.ready_to_claim(world) == []  # said once


def test_the_actions_add_a_reward_and_a_counted_objective_and_refuse_nonsense(tmp_path, monkeypatch):
    """mission.trophy and objective.count from the screen; an unknown stat or a target of 0 is refused before
    anything changes; "jars" is understood as jars put up."""
    world = _world(tmp_path, monkeypatch)
    mission = world.missions.add_mission("Canning season", profile_id=world.me.profile_id)
    params = {"mission_id": mission.mission_id, "kind": "skill", "name": "Canning"}
    assert "Skill: Canning" in ACTION_TYPES["mission.trophy"].describe(world, params)
    ACTION_TYPES["mission.trophy"].execute(world, params)
    count = {"mission_id": mission.mission_id, "stat": "jars", "target": 20}
    assert "20 jars put up" in ACTION_TYPES["objective.count"].describe(world, count)
    ACTION_TYPES["objective.count"].execute(world, count)
    kept = world.missions.get_mission(mission.mission_id)
    assert kept.trophies == [{"kind": "skill", "name": "Canning", "ref": ""}]
    assert kept.objectives[0].metric_type == "records" and kept.objectives[0].stat_id == "jars_canned"
    with pytest.raises(ActionError):
        ACTION_TYPES["objective.count"].describe(world, {**count, "stat": "sunshine"})
    with pytest.raises(ActionError):
        ACTION_TYPES["objective.count"].describe(world, {**count, "target": 0})


def test_a_tally_tick_is_refused_on_an_objective_that_counts_from_records(tmp_path, monkeypatch):
    """Tapping +1 can't inflate an objective his records count."""
    world = _world(tmp_path, monkeypatch)
    mission = world.missions.add_mission("Eggs", profile_id=world.me.profile_id)
    world.missions.add_objective(mission.mission_id, "5 dozen eggs", "records", 60, stat_id="eggs_collected")
    with pytest.raises(ActionError):
        ACTION_TYPES["objective.tick"].describe(world, {"mission_id": mission.mission_id, "index": 0})
