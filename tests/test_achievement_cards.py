"""
tests.test_achievement_cards
==============================

The game layer's achievements (2026-11-24): pounds of produce, eggs and jars counted from the records
(core/life_milestones.py), structures built from Complete projects, unlocked at once when the record is logged, kept
in the log with their dates and shown once as a card (core/achievement_cards.py), and said by voice.
"""

from datetime import datetime, timedelta

import pytest

from core import achievement_cards, canning_shelf, life_events, life_milestones, progress_history
from core.actions import ACTION_TYPES, ActionError
from core.flock import FlockBook
from core.grow_lab import GrowLab
from core.rewards_manager import RewardsManager
from tests.engine_world import build_world


def _world(tmp_path, monkeypatch):
    """The engine's small household plus a grow lab, a flock book and rewards, with unlocks kept in the history."""
    world = build_world(tmp_path, monkeypatch)
    world.grow_lab = GrowLab(world, data_dir=world.home_dir)
    world.flock = FlockBook(world, data_dir=world.home_dir)
    world.rewards = RewardsManager(world)
    progress_history.subscribe(world)
    return world


def test_harvests_count_only_their_weight_and_convert_ounces_and_kilograms(tmp_path, monkeypatch):
    """Pounds, ounces and kilograms add up in pounds; heads and bunches have no weight and are left out."""
    world = _world(tmp_path, monkeypatch)
    batch = world.grow_lab.add_batch("Tomatoes")
    world.grow_lab.harvest(batch.batch_id, 10, "lbs")
    world.grow_lab.harvest(batch.batch_id, 32, "oz")
    world.grow_lab.harvest(batch.batch_id, 1, "kg")
    world.grow_lab.harvest(batch.batch_id, 4, "heads")
    assert abs(life_milestones.produce_pounds(world) - (10 + 2 + 2.20462)) < 0.01


def test_eggs_and_jars_add_up_and_an_undone_batch_of_jars_stops_counting(tmp_path, monkeypatch):
    """Every egg logged counts; every jar put up counts after it's eaten, and an undone batch doesn't."""
    world = _world(tmp_path, monkeypatch)
    flock = world.flock.add_flock("Layers", hens=6)
    world.flock.log(flock.flock_id, "eggs", count=5)
    world.flock.log(flock.flock_id, "eggs", count=7)
    world.flock.log(flock.flock_id, "feed", pounds=50)
    assert life_milestones.eggs_collected(world) == 12
    canning_shelf.put_up(world.kitchen, "tomatoes", 7, "quarts")
    item = canning_shelf.put_up(world.kitchen, "peaches", 4, "pints")
    world.kitchen.delete_pantry_item(item.item_id)  # eaten: still canned
    assert life_milestones.jars_canned(world) == 11
    canned = [e for e in life_events.events_for(world, types=("canned",)) if e.payload.get("food") == "peaches"]
    life_events.record(world.kitchen, "undone", "Undid the peaches", payload={"reverses": [canned[0].event_id]})
    assert life_milestones.jars_canned(world) == 7


def test_logging_crosses_a_tier_at_once_and_its_card_shows_once(tmp_path, monkeypatch):
    """A dozen eggs unlocks First Dozen when it's logged (no wait for the daily scan); the card is offered once, and
    after it's marked seen it isn't offered again."""
    world = _world(tmp_path, monkeypatch)
    flock = world.flock.add_flock("Layers", hens=6)
    world.flock.log(flock.flock_id, "eggs", count=12)
    me = world.me.profile_id
    assert world.rewards.is_unlocked(me, "eggs_first_dozen")
    offered = achievement_cards.unseen(world)
    assert [c["name"] for c in offered["cards"]] == ["First Dozen"]
    assert offered["cards"][0]["headline"] == "Achievement Unlocked" and offered["upto"]
    ACTION_TYPES["achievement.seen"].execute(world, {"upto": offered["upto"]})
    assert achievement_cards.unseen(world)["cards"] == []
    assert achievement_cards.log(world)[0]["name"] == "First Dozen"


def test_a_completed_project_naming_a_structure_is_its_milestone_and_a_repair_is_not(tmp_path, monkeypatch):
    """"Build the chicken coop" marked Complete unlocks Rule the Roost; "Repair the shed roof" builds no shed; a
    project still in progress builds nothing."""
    world = _world(tmp_path, monkeypatch)
    me = world.me.profile_id
    coop = world.projects.add_project("Build the chicken coop")
    world.projects.add_project("Greenhouse")
    shed = world.projects.add_project("Repair the shed roof")
    world.projects.update_project(shed.project_id, status="Complete")
    world.projects.update_project(coop.project_id, status="Complete")
    assert world.rewards.is_unlocked(me, "built_chicken_coop")  # heard at once (activity.logged)
    assert not life_milestones.built(world, "built_greenhouse")
    assert not life_milestones.built(world, "built_shed")
    assert "Rule the Roost" in [c["name"] for c in achievement_cards.unseen(world)["cards"]]


def test_only_the_last_day_is_shown_the_first_time_and_three_cards_at_most(tmp_path, monkeypatch):
    """Before he has ever seen a card, an unlock from last week isn't popped up; of five new ones, three cards come
    with "two more"."""
    world = _world(tmp_path, monkeypatch)
    me = world.me.profile_id
    world.profiles.unlock_reward(me, "missions_rookie")
    later = datetime.now() + timedelta(days=8)
    assert achievement_cards.unseen(world, now=later)["cards"] == []
    for rid in ("eggs_first_dozen", "canner_first_batch", "grower_first_basket", "fitness_getting_started"):
        world.profiles.unlock_reward(me, rid)
    offered = achievement_cards.unseen(world)
    assert len(offered["cards"]) == 3 and offered["more"] == 2


def test_the_page_never_lists_a_locked_hidden_achievement_and_the_voice_twin_says_the_closest(tmp_path, monkeypatch):
    """The total counts hidden achievements only once found; my_achievements names the next tier nearest done."""
    world = _world(tmp_path, monkeypatch)
    batch = world.grow_lab.add_batch("Squash")
    world.grow_lab.harvest(batch.batch_id, 80, "lb")
    found = achievement_cards.page(world)
    hidden = {c["id"] for c in achievement_cards.catalog().values() if c["kind"] == "hidden"}
    assert found["counts"]["total"] == len(achievement_cards.catalog()) - len(hidden)
    said = achievement_cards.say(world)
    assert "Kitchen Gardener, 80 lb of 100 lb" in said and "First Basket" in said


def test_a_bad_time_is_refused_before_anything_changes(tmp_path, monkeypatch):
    """achievement.seen with something that isn't a time is refused in its description."""
    world = _world(tmp_path, monkeypatch)
    with pytest.raises(ActionError):
        ACTION_TYPES["achievement.seen"].describe(world, {"upto": "soon"})
