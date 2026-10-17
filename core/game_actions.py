"""
core.game_actions
===================

The game layer's changes (DEC-0028, docs/GAME_LAYER.md), on the action
contract in core/actions.py.

- Reward Shop: `shop_reward.add/edit/delete` (the rewards you set) and
  `shop.buy` (spend credits on one). Undo gives the credits back.
- Boss battles: `boss.add` makes a mission a boss fight, `boss.remove`
  turns it back into a plain mission (debts are bosses on their own).

A person's own credits and shop: these are child-safe.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_form, record_kinds

ONCE, AGAIN = "Just Once", "Again And Again"

SHOP_REWARD = Record("shop_reward", "reward", "reward_id", "get_reward", "add_reward", "update_reward", "delete_reward",
                     store="reward_shop", fields=(
                         Field("name", "Reward", "text", True),
                         Field("cost", "Cost (credits)", "int", True, say="cost"),
                         Field("icon", "Icon (an emoji)", "text", default="🎁", say="icon", quiet_default=True),
                         Field("buy", "Can you buy it", "choice", options=(AGAIN, ONCE), default=AGAIN,
                               say="buy it", quiet_default=True),
                         Field("note", "Note", "textarea"),
                     ))


def forms() -> dict:
    return {"shop_reward": record_form(SHOP_REWARD)}


def _person(context):
    profiles = getattr(context, "profiles", None)
    profile_id = getattr(context, "profile_id", None)
    try:
        return (profiles.get_profile(profile_id) if profile_id else None) or profiles.get_active_profile()
    except Exception:
        return None


def _reward(context, params):
    reward = _need(context, "reward_shop").get_reward(str(params.get("reward_id") or ""))
    if reward is None:
        raise ActionError("That reward isn't in your shop anymore.")
    return reward


def _describe_buy(context, params) -> str:
    from core.reward_shop import balance

    reward = _reward(context, params)
    shop = context.reward_shop
    left = balance(context, _person(context))["left"]
    if not shop.available(reward):
        raise ActionError(f"You already claimed {reward.name}.")
    if reward.cost > left:
        raise ActionError(f"{reward.name} costs {reward.cost:,} credits; you have {left:,}. {reward.cost - left:,} to go.")
    return f"Spend {reward.cost:,} credits on {reward.icon} {reward.name} ({left:,} → {left - reward.cost:,} left)"


def _buy(context, params) -> str:
    from core.reward_shop import balance

    reward = _reward(context, params)
    try:
        context.reward_shop.buy(reward.reward_id, balance(context, _person(context))["left"])
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"{reward.icon} {reward.name} is yours. Enjoy it."


def _priced(describe):
    """A reward costs at least 1 credit: said when it's proposed."""
    def checked(context, params):
        if "cost" in params:
            try:
                ok = float(str(params.get("cost")).replace(",", "")) >= 1
            except ValueError:
                ok = False
            if not ok:
                raise ActionError("A reward has to cost at least 1 credit.")
        return describe(context, params)
    return checked


def _boss_mission(context, params, want: bool):
    mission = _need(context, "missions").get_mission(str(params.get("mission_id") or ""))
    if mission is None:
        raise ActionError("That mission isn't there anymore.")
    book = _need(context, "boss_book")
    if want and mission.mission_id in book.missions:
        raise ActionError(f"{mission.name} is already a boss fight.")
    if not want and mission.mission_id not in book.missions:
        raise ActionError(f"{mission.name} isn't a boss fight.")
    if want and not mission.objectives:
        raise ActionError("Give it objectives first: they're the boss's HP.")
    return mission


def _boss_add(context, params) -> str:
    mission = _boss_mission(context, params, True)
    context.boss_book.add_mission(mission.mission_id)
    return f"{mission.name} is a boss fight. Every objective is a hit."


def _boss_remove(context, params) -> str:
    mission = _boss_mission(context, params, False)
    context.boss_book.remove_mission(mission.mission_id)
    return f"{mission.name} is a plain mission again."


def _register() -> None:
    from dataclasses import replace

    kinds = [replace(k, describe=_priced(k.describe)) if k.kind != "shop_reward.delete" else k
             for k in record_kinds(SHOP_REWARD, child_ok=True)] + [
        ActionType("shop.buy", "Buy", {"reward_id": "the reward"}, _describe_buy, _buy, True),
        ActionType("boss.add", "Make It A Boss Fight", {"mission_id": "the mission"},
                   lambda c, p: f"Make {_boss_mission(c, p, True).name} a boss fight (its objectives are its HP)", _boss_add, True),
        ActionType("boss.remove", "Not A Boss", {"mission_id": "the mission"},
                   lambda c, p: f"Make {_boss_mission(c, p, False).name} a plain mission again", _boss_remove, True),
    ]
    for kind in kinds:
        ACTION_TYPES[kind.kind] = kind


_register()
