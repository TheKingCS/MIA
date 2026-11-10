"""
tests.test_progress_history
=============================

A prestige reached or a reward unlocked is kept in that person's history (core/progress_history.py, 2026-11-09):
heard on the bus, recorded in their own folder, the reward named from its tier, and nothing for a profile that's gone.
"""

from core import life_events, progress_history
from core.rewards_manager import all_tiers
from tests.engine_world import build_world


def test_a_reward_unlocked_and_a_prestige_are_lines_in_that_person_s_history(tmp_path, monkeypatch):
    """Both events, published for the signed-in person, become named lines in their own life-event log; a profile
    that's gone records nothing."""
    world = build_world(tmp_path, monkeypatch)
    progress_history.subscribe(world)
    tier = all_tiers()[0]
    me = world.me.profile_id
    world.events.publish("profile.reward_unlocked", profile_id=me, reward_id=tier.reward_id)
    world.events.publish("profile.prestiged", profile_id=me, new_tier=2)
    world.events.publish("profile.prestiged", profile_id="gone", new_tier=9)
    log = life_events.LifeEventLog(world, data_dir=world.me.data_dir)
    summaries = [e.summary for e in log.all_events() if e.type in ("reward_unlocked", "prestiged")]
    assert sorted(summaries) == sorted([f"Unlocked {tier.name}", "Reached prestige tier 2"])


def test_an_unknown_reward_is_still_noted_without_a_name():
    """reward_name gives "" for an id no tier or achievement has."""
    assert progress_history.reward_name("no-such-reward") == ""
