"""
The Reward Shop (DEC-0028, Zac 2026-10-17): spend credits on rewards you
set. Each person's own shop; spending never lowers the lifetime credits
or the level; undo gives the credits back.
"""

import pytest

from core.actions import ActionCenter, ActionError
from core.game_layer import shop_page
from core.reward_shop import RewardShop, flag
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.reward_shop = RewardShop(context, data_dir=tmp_path / "me")
    me = context.profiles.get_active_profile()
    context.profiles.add_credits(me.profile_id, 700)
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal, done


def test_flag():
    assert flag("Just Once") is False and flag("Again And Again") is True and flag(False) is False


def test_set_rewards_buy_and_undo(world):
    page = shop_page(world)
    assert page["credits"] == {"earned": 700, "spent": 0, "left": 700} and page["rewards"] == []
    assert any(i["name"] == "Movie night" for i in page["ideas"])
    proposal, _ = do(world, "shop_reward.add", name="Movie night", cost="500", icon="🍿")
    assert proposal.summary == "Add the reward Movie night: cost 500, icon 🍿"
    do(world, "shop_reward.add", name="New pedals", cost="3000", buy="Just Once")
    page = shop_page(world)
    movie, pedals = page["rewards"]
    assert (movie["name"], movie["affordable"], pedals["affordable"], pedals["to_go"]) == ("Movie night", True, False, 2300)
    assert pedals["percent"] == 23 and not any(i["name"] == "Movie night" for i in page["ideas"])
    proposal, bought = do(world, "shop.buy", reward_id=movie["id"])
    assert proposal.summary == "Spend 500 credits on 🍿 Movie night (700 → 200 left)"
    page = shop_page(world)
    assert page["credits"] == {"earned": 700, "spent": 500, "left": 200}
    assert page["bought"][0]["name"] == "Movie night"
    assert world.profiles.get_active_profile().total_credits == 700  # lifetime total untouched
    with pytest.raises(ActionError):  # 500 > 200 left
        world.actions.propose(world, "shop.buy", {"reward_id": movie["id"]})
    world.actions.undo(world, bought.proposal_id)
    assert shop_page(world)["credits"]["left"] == 700


def test_once_only_and_edits(world):
    world.profiles.add_credits(world.profiles.get_active_profile().profile_id, 5000)
    do(world, "shop_reward.add", name="New pedals", cost="3000", buy="Just Once")
    pedals = shop_page(world)["rewards"][0]
    proposal, _ = do(world, "shop_reward.edit", reward_id=pedals["id"], **{**pedals["values"], "cost": "2500"})
    assert proposal.summary == "Change New pedals: cost 3000 → 2500"
    do(world, "shop.buy", reward_id=pedals["id"])
    pedals = shop_page(world)["rewards"][0]
    assert not pedals["available"] and pedals["bought"] == 1
    with pytest.raises(ActionError):
        world.actions.propose(world, "shop.buy", {"reward_id": pedals["id"]})
    with pytest.raises(ActionError):
        world.actions.propose(world, "shop_reward.add", {"name": "Free", "cost": "0"})
