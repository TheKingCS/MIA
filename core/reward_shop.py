"""
core.reward_shop
==================

The Reward Shop (DEC-0028, the game layer's first piece; Zac 2026-10-17):
spend the credits you earn on real rewards you set yourself ("new bike
pedals = 3,000", "guilt-free gaming night = 500").

Each person has their own shop (a personal store, core/personal_data.py):
the rewards they listed and what they've bought. Credits are earned into
the profile's lifetime `total_credits` and never taken from it; what's
left to spend is that total minus what this shop has spent, so a
purchase can be undone (the store writes through atomic_write_text) and
the lifetime total stays a true record. Rewards can be one-time (gone
once bought) or for again and again.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "reward_shop.json"


def flag(value) -> bool:
    """Pure logic. "Just Once" / "no" / False -> False; anything else True."""
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "no", "once", "just once")
    return bool(value)


@dataclass
class ShopReward:
    reward_id: str
    name: str
    cost: int
    icon: str = "🎁"
    note: str = ""
    repeatable: bool = True  # False: once bought, it's done
    created_at: str = ""

    @property
    def buy(self) -> str:
        """How the form says `repeatable` (core/game_actions.py)."""
        return "Again And Again" if self.repeatable else "Just Once"


@dataclass
class Purchase:
    purchase_id: str
    reward_id: str
    name: str
    cost: int
    icon: str = "🎁"
    bought_at: str = ""


@dataclass
class _Data:
    rewards: list = field(default_factory=list)
    purchases: list = field(default_factory=list)


class RewardShop:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._rewards: list[ShopReward] = []
        self._purchases: list[Purchase] = []
        self._load()

    # ------------------------------------------------------------------ storage
    def _load(self) -> None:
        self._rewards, self._purchases = [], []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            self._rewards = [ShopReward(**{k: v for k, v in r.items() if k in ShopReward.__dataclass_fields__})
                             for r in raw.get("rewards", [])]
            self._purchases = [Purchase(**{k: v for k, v in p.items() if k in Purchase.__dataclass_fields__})
                               for p in raw.get("purchases", [])]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("reward_shop.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"rewards": [asdict(r) for r in self._rewards],
                                                  "purchases": [asdict(p) for p in self._purchases]}, indent=2))

    # ------------------------------------------------------------------ rewards
    def all_rewards(self) -> list[ShopReward]:
        return sorted(self._rewards, key=lambda r: (r.cost, r.name.lower()))

    def get_reward(self, reward_id: str) -> Optional[ShopReward]:
        return next((r for r in self._rewards if r.reward_id == reward_id), None)

    def add_reward(self, name: str, cost, icon: str = "🎁", note: str = "", repeatable=True, buy=None) -> ShopReward:
        if buy is not None:
            repeatable = buy
        name = str(name or "").strip()
        if not name:
            raise ValueError("What's the reward? Give it a name.")
        cost = int(round(float(cost or 0)))
        if cost <= 0:
            raise ValueError("A reward has to cost at least 1 credit.")
        reward = ShopReward(uuid.uuid4().hex[:10], name, cost, (icon or "🎁").strip() or "🎁", note or "",
                            flag(repeatable), datetime.now().isoformat(timespec="seconds"))
        self._rewards.append(reward)
        self._save()
        return reward

    def update_reward(self, reward_id: str, **fields) -> ShopReward:
        reward = self.get_reward(reward_id)
        if reward is None:
            raise ValueError("That reward isn't in your shop anymore.")
        for key, value in fields.items():
            if key == "cost":
                value = int(round(float(value or 0)))
                if value <= 0:
                    raise ValueError("A reward has to cost at least 1 credit.")
            if key in ("repeatable", "buy"):
                key, value = "repeatable", flag(value)
            if key in ("name", "icon", "note", "cost", "repeatable"):
                setattr(reward, key, value)
        self._save()
        return reward

    def delete_reward(self, reward_id: str) -> None:
        self._rewards = [r for r in self._rewards if r.reward_id != reward_id]
        self._save()

    # ------------------------------------------------------------------ spending
    def spent(self) -> int:
        return sum(p.cost for p in self._purchases)

    def purchases(self) -> list[Purchase]:
        return sorted(self._purchases, key=lambda p: p.bought_at, reverse=True)

    def times_bought(self, reward_id: str) -> int:
        return sum(1 for p in self._purchases if p.reward_id == reward_id)

    def available(self, reward: ShopReward) -> bool:
        return reward.repeatable or self.times_bought(reward.reward_id) == 0

    def buy(self, reward_id: str, balance: int) -> Purchase:
        """Spend `reward.cost` of `balance` (what the person has left)."""
        reward = self.get_reward(reward_id)
        if reward is None:
            raise ValueError("That reward isn't in your shop anymore.")
        if not self.available(reward):
            raise ValueError(f"You already claimed {reward.name}.")
        if reward.cost > balance:
            raise ValueError(f"{reward.name} costs {reward.cost:,} credits; you have {balance:,}. "
                             f"{reward.cost - balance:,} to go.")
        purchase = Purchase(uuid.uuid4().hex[:10], reward.reward_id, reward.name, reward.cost, reward.icon,
                            datetime.now().isoformat(timespec="seconds"))
        self._purchases.append(purchase)
        self._save()
        return purchase


def balance(context, profile=None) -> dict:
    """Earned (lifetime), spent here, and left to spend."""
    if profile is None:
        profiles = getattr(context, "profiles", None)
        profile = profiles.get_active_profile() if profiles is not None else None
    earned = int(getattr(profile, "total_credits", 0) or 0) if profile is not None else 0
    shop = getattr(context, "reward_shop", None)
    spent = shop.spent() if shop is not None else 0
    return {"earned": earned, "spent": spent, "left": max(0, earned - spent)}
