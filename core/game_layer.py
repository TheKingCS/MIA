"""
core.game_layer
=================

The game layer's screens (DEC-0028, docs/GAME_LAYER.md). Built in order:

1. `shop_page`: the Reward Shop. What you've earned, spent and have left,
   the rewards you set (what you can afford now, how far off the rest
   are), and what you've bought. Changes: core/game_actions.py.
"""

from __future__ import annotations

from typing import Optional

# Ideas to start a shop with: never personal, one tap to add, then edit.
SHOP_IDEAS = (
    ("🍿", "Movie night", 500), ("🍕", "Favorite takeout", 400), ("🎮", "Guilt-free gaming night", 500),
    ("🛌", "A slow morning, no plans", 300), ("☕", "A fancy coffee", 150), ("🎟", "A day trip", 2000),
    ("🛠", "A new tool or piece of gear", 3000),
)


def _person(context):
    from core.game_actions import _person as person

    return person(context)


def shop_page(context) -> dict:
    from core.game_actions import forms
    from core.reward_shop import balance

    shop = getattr(context, "reward_shop", None)
    if shop is None:
        return {"available": False}
    money = balance(context, _person(context))
    rewards = []
    for r in shop.all_rewards():
        bought = shop.times_bought(r.reward_id)
        open_ = shop.available(r)
        rewards.append({"id": r.reward_id, "name": r.name, "icon": r.icon, "cost": r.cost, "note": r.note,
                        "repeatable": r.repeatable, "bought": bought, "available": open_,
                        "affordable": open_ and r.cost <= money["left"], "to_go": max(0, r.cost - money["left"]),
                        "percent": min(100, round(100 * money["left"] / r.cost)) if r.cost else 100,
                        "values": {"name": r.name, "cost": r.cost, "icon": r.icon, "buy": r.buy, "note": r.note}})
    rewards.sort(key=lambda r: (not r["available"], not r["affordable"], r["cost"]))
    names = {r["name"].lower() for r in rewards}
    return {
        "available": True, "credits": money,
        "rewards": rewards,
        "bought": [{"id": p.purchase_id, "name": p.name, "icon": p.icon, "cost": p.cost, "when": p.bought_at[:10]}
                   for p in shop.purchases()[:30]],
        "ideas": [{"icon": i, "name": n, "cost": c} for i, n, c in SHOP_IDEAS if n.lower() not in names],
        "counts": {"rewards": len(rewards), "ready": sum(1 for r in rewards if r["affordable"]),
                   "bought": len(shop.purchases())},
        "forms": forms(),
    }
