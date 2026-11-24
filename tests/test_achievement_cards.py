"""
tests.test_achievement_cards
==============================

The game layer's achievements (2026-11-24): pounds of produce, eggs and jars counted from the records
(core/life_milestones.py), structures built from Complete projects, unlocked at once when the record is logged, kept
in the log with their dates and shown once as a card (core/achievement_cards.py), and said by voice.
And the review's cases: closing a card never blocks undoing what earned it, cards are seen by id, a structure needs
a build, grams count, and a mission's trophy is in the log.
"""

from datetime import datetime, timedelta

import pytest

from core import achievement_cards, canning_shelf, life_events, life_milestones, progress_history
from core.actions import ActionCenter
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
    after it's marked seen it isn't offered again.
    Seen by its id."""
    world = _world(tmp_path, monkeypatch)
    flock = world.flock.add_flock("Layers", hens=6)
    world.flock.log(flock.flock_id, "eggs", count=12)
    me = world.me.profile_id
    assert world.rewards.is_unlocked(me, "eggs_first_dozen")
    offered = achievement_cards.unseen(world)
    assert [c["name"] for c in offered["cards"]] == ["First Dozen"]
    assert offered["cards"][0]["headline"] == "Achievement Unlocked"
    achievement_cards.mark_seen(world, [offered["cards"][0]["id"]])
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


def test_marking_seen_needs_an_id_and_each_card_is_marked_alone(tmp_path, monkeypatch):
    """No ids is refused; two unlocked in the same second are two cards, and seeing one leaves the other."""
    world = _world(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        achievement_cards.mark_seen(world, [])
    me = world.me.profile_id
    world.profiles.unlock_reward(me, "eggs_first_dozen")
    world.profiles.unlock_reward(me, "canner_first_batch")
    achievement_cards.mark_seen(world, ["eggs_first_dozen"])
    assert [c["id"] for c in achievement_cards.unseen(world)["cards"]] == ["canner_first_batch"]


def test_closing_a_card_never_stands_in_the_way_of_undoing_what_earned_it(tmp_path, monkeypatch):
    """A harvest approved, its card seen, then the harvest undone: the seen-marker is bookkeeping outside undo
    (the review's reproduction), so the harvest's Undo still works and the unlock goes with it."""
    world = _world(tmp_path, monkeypatch)
    batch = world.grow_lab.add_batch("Tomatoes")
    center = ActionCenter()
    harvest = center.propose(world, "batch.harvest", {"batch_id": batch.batch_id, "amount": 12, "unit": "lb"})
    center.approve(world, harvest.proposal_id)
    card = achievement_cards.unseen(world)["cards"][0]
    assert card["id"] == "grower_first_basket"
    achievement_cards.mark_seen(world, [card["id"]])
    center.undo(world, harvest.proposal_id)
    assert life_milestones.produce_pounds(world) == 0


def test_a_structure_needs_a_build_and_a_mention_or_a_repair_earns_nothing():
    """The review's cases: mending, a part, automation or a mention earn nothing; a build verb or the bare name
    earns exactly one structure, plurals and "-ing" forms included."""
    none = ("Greenhouse automation", "Winterize the greenhouse", "Cleaning the coop", "Painting the shed",
            "Garage door opener", "Repairing the barn", "Prune the orchard", "Weed the garden beds", "Workshop bench",
            "Join the food coop", "Solar panels for the shed", "Build the greenhouse sensor node", "Build a website")
    assert [n for n in none if life_milestones.structure_of(n)] == []
    built = {"Greenhouse": "built_greenhouse", "Build two sheds": "built_shed", "Build chicken coops":
             "built_chicken_coop", "Install solar": "built_power_station", "Digging a well": "built_well_pump",
             "Install solar panels for the shed": "built_power_station", "Plant the orchard": "built_orchard"}
    assert {n: life_milestones.structure_of(n).reward_id for n in built} == built


def test_grams_count_toward_the_pounds(tmp_path, monkeypatch):
    """Microgreens weighed in grams are counted too."""
    world = _world(tmp_path, monkeypatch)
    batch = world.grow_lab.add_batch("Microgreens")
    world.grow_lab.harvest(batch.batch_id, 454, "g")
    assert abs(life_milestones.produce_pounds(world) - 1.0) < 0.01


def test_a_missions_trophy_is_in_the_log_and_offered_as_a_card(tmp_path, monkeypatch):
    """A structure earned by a mission is a card (its kind's headline) and a row in the log, not an achievement."""
    world = _world(tmp_path, monkeypatch)
    mission = world.missions.add_mission("Raise the coop", profile_id=world.me.profile_id)
    world.missions.add_trophy(mission.mission_id, "structure", "Chicken coop")
    world.missions.update_mission(mission.mission_id, status="completed")
    card = achievement_cards.unseen(world)["cards"][-1]
    assert card["headline"] == "Structure Built" and card["name"] == "Chicken coop"
    assert card["id"].startswith("trophy:")
    assert achievement_cards.page(world)["counts"]["trophies"] == 1
