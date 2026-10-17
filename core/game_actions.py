"""
core.game_actions
===================

The game layer's changes (DEC-0028, docs/GAME_LAYER.md), on the action
contract in core/actions.py.

- Reward Shop: `shop_reward.add/edit/delete` (the rewards you set) and
  `shop.buy` (spend credits on one). Undo gives the credits back.

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


def _register() -> None:
    from dataclasses import replace

    kinds = [replace(k, describe=_priced(k.describe)) if k.kind != "shop_reward.delete" else k
             for k in record_kinds(SHOP_REWARD, child_ok=True)] + [
        ActionType("shop.buy", "Buy", {"reward_id": "the reward"}, _describe_buy, _buy, True),
    ]
    for kind in kinds:
        ACTION_TYPES[kind.kind] = kind


_register()
