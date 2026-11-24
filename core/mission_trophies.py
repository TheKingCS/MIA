"""
core.mission_trophies
=======================

What a mission rewards besides XP and credits, and missions that count themselves from his records (the game layer,
step 2, docs/future/GAME_LAYER_PLAN.md; Zac 2026-11-24: "Some times the mission reward is a crafted item and xp,
sometimes its a structure built for the homestead, sometimes its a song unlocked on the guitar, sometimes its a
knowledge the user has shown mastery of, sometimes its a kitchen recipe, sometimes its a skill like canning").

**Trophies** (`KINDS`, `trophy`, `award`): a mission carries a list of them (`Mission.trophies`), each {kind, name,
ref}: an item crafted, a structure built, a song unlocked, knowledge mastered, a recipe, or a skill learned. They're
shown on the mission before it's done and earned once, with its other rewards, when it completes: each is a
`trophy_earned` life event for whoever the rewards go to, so the achievements log (core/achievement_cards.py) lists it
with its date and its card pops up. A recipe whose ref is a Kitchen recipe id is unlocked there too
(`KitchenManager.unlock_recipe`, as `recipe_unlocks` does); a skill whose ref is a skill id gets `SKILL_XP` in it.

**Counted from records** (`STATS`, `stat_now`): an objective of the metric `records` reads a lifetime stat
(core/rewards_manager.py's: produce grown, eggs, jars canned, meals cooked, workout hours, projects done...) and
counts what's been added since the objective was set (its `baseline`), so "put up 20 jars this summer" finishes from
the jars he logs, never from a tap. When every objective of such a mission is met, he's told it's ready to claim
(`ready_to_claim`); claiming it stays his press, as every mission's completion is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

SKILL_XP = 25  # a skill learned as a mission's reward: this much XP in it


@dataclass(frozen=True)
class Kind:
    """A kind of trophy: its id, the card's headline, its icon, and the rarity its card shows (0 Common to 4
    Legendary)."""
    kind: str
    headline: str
    icon: str
    rarity_index: int


KINDS: dict[str, Kind] = {k.kind: k for k in (
    Kind("item", "Item Crafted", "🧰", 1),
    Kind("structure", "Structure Built", "🏗️", 3),
    Kind("song", "Song Unlocked", "🎸", 2),
    Kind("knowledge", "Knowledge Mastered", "📜", 2),
    Kind("recipe", "Recipe Unlocked", "🍲", 1),
    Kind("skill", "Skill Learned", "⭐", 2),
)}

# The lifetime stats an objective can count from: (its id, what one of it is called, said after the number).
STATS: dict[str, str] = {
    "produce_pounds": "lb of produce", "eggs_collected": "eggs", "jars_canned": "jars put up",
    "meals_cooked": "meals cooked", "workout_hours_logged": "hours of workouts", "projects_completed": "projects done",
    "missions_completed": "missions done", "engine_hours_logged": "engine hours", "vehicle_miles_logged": "miles",
    "songs_learned": "songs learned",
}


def trophy(kind: str, name: str, ref: str = "") -> dict:
    """Pure logic. A trophy as a mission keeps it; ValueError for a kind not in `KINDS` or no name."""
    kind = str(kind or "").strip().lower()
    name = " ".join(str(name or "").split())
    if kind not in KINDS:
        raise ValueError(f"A reward is one of: {', '.join(KINDS)}.")
    if not name:
        raise ValueError("What's the reward called?")
    return {"kind": kind, "name": name[:80], "ref": str(ref or "").strip()[:60]}


def said(t: dict) -> str:
    """Pure logic. A trophy in words: "Structure: Chicken coop"."""
    kind = KINDS.get(t.get("kind", ""))
    return f"{kind.headline.split()[0] if kind else 'Reward'}: {t.get('name', '')}"


def award(context, mission, profile_ids: list[str]) -> list[dict]:
    """Earns a completed mission's trophies (once: the caller guards with `rewards_credited`): a `trophy_earned` life
    event in each person's own history, a Kitchen recipe unlocked, a skill's XP. Returns the trophies earned."""
    from core import life_events

    earned = []
    for t in getattr(mission, "trophies", None) or []:
        kind = KINDS.get(t.get("kind", ""))
        if kind is None or not t.get("name"):
            continue
        ref = t.get("ref", "")
        if t["kind"] == "recipe" and ref and getattr(context, "kitchen", None) is not None:
            try:
                context.kitchen.unlock_recipe(ref)
            except Exception:  # noqa: BLE001 - a recipe that's gone still leaves the trophy
                log.exception("Couldn't unlock the recipe %s", ref)
        for pid in profile_ids or [None]:
            if t["kind"] == "skill" and ref and pid and getattr(context, "skills", None) is not None:
                context.skills.add_skill_xp(pid, ref, SKILL_XP)
            profile = context.profiles.get_profile(pid) if pid and getattr(context, "profiles", None) else None
            life_events.record(profile if profile is not None else context.missions, "trophy_earned",
                               f"{kind.headline}: {t['name']}", [f"mission:{mission.mission_id}"],
                               {"kind": t["kind"], "name": t["name"], "ref": ref, "mission": mission.name},
                               profile_id=pid)
        earned.append(t)
    return earned


def stat_now(context, stat_id: str, profile_id: Optional[str]) -> float:
    """A lifetime stat's value now for a person (core/rewards_manager.py), 0 without rewards or a person."""
    rewards = getattr(context, "rewards", None)
    if rewards is None or stat_id not in STATS:
        return 0.0
    if not profile_id and getattr(context, "profiles", None) is not None:
        active = context.profiles.get_active_profile()
        profile_id = active.profile_id if active is not None else None
    return float(rewards.stat_value(stat_id, profile_id)) if profile_id else 0.0


def ready_to_claim(context) -> list:
    """The active missions counted from records whose every objective is now met and that haven't been said ready:
    each is marked said (so it's said once) and he's told it's ready to claim. Returns those missions."""
    missions = getattr(context, "missions", None)
    if missions is None:
        return []
    ready = []
    for mission in missions.all_missions():
        if mission.status != "active" or getattr(mission, "ready_said", False):
            continue
        if not any(o.metric_type == "records" for o in mission.objectives):
            continue
        if all(missions.is_objective_complete(mission.mission_id, i) for i in range(len(mission.objectives))):
            missions.mark_ready_said(mission.mission_id)
            ready.append(mission)
    return ready
