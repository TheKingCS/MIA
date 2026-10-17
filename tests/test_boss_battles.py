"""
Boss battles (DEC-0028): every debt is a boss (max HP is the highest
balance seen, payments are hits, interest heals it), and any mission can
be made into one (its objectives are its HP).
"""

import pytest

from core.actions import ActionCenter, ActionError
from core.boss_battles import BossBook, bosses, months_to_defeat, phase
from core.web_progress import missions_page
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.boss_book = BossBook(context, data_dir=tmp_path / "me")
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal, done


def test_pure_bits():
    assert [phase(p) for p in (100, 60, 30, 5, 0)] == ["Full Strength", "Wounded", "Staggering", "Last Stand", "Defeated"]
    assert months_to_defeat(1200, 0, 100) == 12 and months_to_defeat(0, 20, 50) == 0
    assert months_to_defeat(10000, 24, 150) is None  # $200/month interest beats a $150 hit
    assert months_to_defeat(10000, 18, 250) == 62  # the standard loan math


def test_a_debt_is_a_boss(world):
    debt = world.budget.add_debt("Car loan", 10000, 6.0, minimum_payment=300)
    boss = bosses(world)["active"][0]
    assert (boss["name"], boss["percent"], boss["phase"], boss["hp"]) == ("Car loan", 100.0, "Full Strength", "$10,000.00")
    assert boss["heal"] == "$50.00" and boss["hits_left"] and boss["action"]["kind"] == "debt.pay"
    do(world, "debt.pay", debt_id=debt.debt_id, amount="6000")
    boss = bosses(world)["active"][0]
    assert (boss["percent"], boss["phase"], boss["max_hp"], boss["damage"]) == (40.0, "Staggering", "$10,000.00", "$6,000.00")
    do(world, "debt.pay", debt_id=debt.debt_id, amount="4000")
    page = bosses(world)
    assert page["active"] == [] and page["defeated"][0]["phase"] == "Defeated" and page["defeated"][0]["defeated_on"]
    assert BossBook(world, data_dir=world.boss_book.data_dir).peaks[f"debt:{debt.debt_id}"] == 10000


def test_a_mission_made_into_a_boss(world):
    do(world, "mission.add", name="Build the shed", reward_xp="200")
    mission = world.missions.all_missions()[-1]
    with pytest.raises(ActionError):  # no objectives yet: no HP
        world.actions.propose(world, "boss.add", {"mission_id": mission.mission_id})
    do(world, "objective.add", mission_id=mission.mission_id, description="Pour the slab", target="1")
    do(world, "objective.add", mission_id=mission.mission_id, description="Frame the walls", target="3")
    assert any(m["id"] == mission.mission_id for m in bosses(world)["missions_to_pick"])
    proposal, _ = do(world, "boss.add", mission_id=mission.mission_id)
    assert proposal.summary == "Make Build the shed a boss fight (its objectives are its HP)"
    boss = missions_page(world)["bosses"]["active"][0]
    assert (boss["hp"], boss["max_hp"], boss["reward"]) == ("4", "4", "+200 XP")
    do(world, "objective.tick", mission_id=mission.mission_id, index="0")
    assert bosses(world)["active"][0]["percent"] == 75.0
    with pytest.raises(ActionError):
        world.actions.propose(world, "boss.add", {"mission_id": mission.mission_id})
    do(world, "boss.remove", mission_id=mission.mission_id)
    assert bosses(world)["active"] == []
