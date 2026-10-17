"""
Party and guild (DEC-0028): household raids share their jobs out and
their reward; the leaderboard only shows people who joined, counting wins.
"""

import pytest

from core.actions import ActionCenter, ActionError
from core.party import party_page, share_out
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal, done


def test_share_out():
    assert share_out(["a", "b", "c"], ["X", "Y"]) == [("a", "X"), ("b", "Y"), ("c", "X")]
    assert share_out(["a"], []) == []


def test_a_raid_with_the_household(world):
    me = world.profiles.get_active_profile()
    kid = world.profiles.create_profile("Sam", make_active=False)
    if world.households is not None:
        world.households._set_household(kid.profile_id, world.households.household_of(me.profile_id))
    prop, _done = do(world, "raid.start", raid_id="garage", people=f"{me.profile_id},{kid.profile_id}")
    assert "Sam" in prop.summary and "Garage Raid" in prop.summary
    page = party_page(world)
    raid = page["raids"][0]
    assert raid["total"] == 4 and [c["total"] for c in raid["crew"]] == [2, 2]
    assert [o["mine"] for o in raid["objectives"]] == [True, False, True, False]
    for o in raid["objectives"]:
        world.missions.increment_tally(raid["id"], o["index"])
    assert party_page(world)["raids"][0]["ready"]
    xp_before = world.profiles.get_profile(kid.profile_id).total_xp
    do(world, "mission.complete", mission_id=raid["id"])
    assert world.profiles.get_profile(kid.profile_id).total_xp == xp_before + 100  # the reward is shared


def test_your_own_raid_needs_two_jobs(world):
    with pytest.raises(ActionError):
        world.actions.propose(world, "raid.add", {"name": "Tiny", "objectives": "one"})
    do(world, "raid.add", name="Car Wash", objectives="Wash\nDry\nVacuum")
    assert party_page(world)["raids"][0]["total"] == 3


def test_leaderboard_is_opt_in_and_counts_wins(world):
    page = party_page(world)
    assert not page["leaderboard"]["on"] and page["leaderboard"]["rows"] == []
    do(world, "party.leaderboard", on=True)
    m = world.missions.add_mission("Fix the fence", reward_xp=10)
    world.missions.update_mission(m.mission_id, status="completed")
    rows = party_page(world)["leaderboard"]["rows"]
    assert len(rows) == 1 and rows[0]["me"] and rows[0]["wins"] >= 1
    do(world, "party.leaderboard", on=False)
    assert party_page(world)["leaderboard"]["rows"] == []
