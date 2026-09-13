"""
core.rewards_manager
=======================

Rewards — real lifetime stats (mower hours, workout hours, missions
completed, ...) unlocking real cosmetic/emblem rewards at thresholds,
the "Call of Duty headshots/kills/bloodthirstys" motivational-stats
system the user asked for (2026-09-14), alongside a character-
customization vision (a hat unlocked after 10 mower hours, etc.) —
real art for the character/cosmetics is deliberately deferred ("we
will work on the artwork later, for now let's build the system"); this
module is the system, using plain emoji icons as placeholders exactly
like every other not-yet-illustrated part of this app.

**Stats are derived, not tracked twice.** Each stat's value is computed
live from data that already exists elsewhere (mower hours from the
real Engine Hours readings core.maintenance_manager already logs,
workout hours from core.workout_manager's real session history,
missions completed from core.mission_manager) — same "derive it, don't
persist a second copy that can drift" philosophy this whole codebase
follows. A stat with no real data source yet (the user's own example,
"water used watering plants" — nothing in this app currently measures
that) is deliberately NOT included here rather than faking a number;
add it for real once something actually logs it.

**Unlocking IS real, persisted state** (`Profile.unlocked_reward_ids`,
see core/profile_manager.py) — unlike the stat values themselves, once
a reward is unlocked it stays unlocked even if the underlying stat
later reads lower (a data correction, a deleted log entry), the same
"a real choice/event, not a live computation" reasoning
`Profile.prestige_tier` already established.

**Prestige tiers are their own reward category** — the user's own
explicit ask ("I also want the prestige system to come with a similar
little emblem trophy thing saying Prestige 1, Prestige 2"). These
don't need their own unlock-tracking at all: `Profile.prestige_tier`
already IS the real, persisted record of how many tiers have been
reached, so `prestige_rewards_for_profile()` just derives one reward
entry per tier already reached, live, the same "derive it" stance as
everything else here.

`scan_for_new_unlocks()` is idempotent (checks `is_unlocked()` first)
and safe to call as often as convenient — both from the daily-occasion
timer (core/application.py, matching core/maintenance_insights.py's
own established cadence) and from the Skills module's own refresh (so
opening the page after crossing a threshold unlocks it right away,
not up to a day later).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.app_context import AppContext
from core.leveling import prestige_color_for_tier
from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class StatDefinition:
    stat_id: str
    name: str
    unit: str
    icon: str


@dataclass(frozen=True)
class RewardDefinition:
    reward_id: str
    name: str
    description: str
    icon: str
    stat_id: str
    threshold: float


#: Every stat here has a real, already-logged data source — see this
#: module's own docstring for why "water used watering plants" (the
#: user's own example) isn't in this list yet.
STAT_DEFINITIONS: list[StatDefinition] = [
    StatDefinition("engine_hours_logged", "Engine Hours Logged", "hrs", "🚜"),
    StatDefinition("workout_hours_logged", "Workout Hours Logged", "hrs", "💪"),
    StatDefinition("missions_completed", "Missions Completed", "", "🏆"),
]

#: v1 reward set — real thresholds against the real stats above.
#: Icons are plain emoji placeholders (real character/cosmetic art is
#: deliberately deferred, per this module's own docstring); reward_id
#: is the stable identifier persisted in Profile.unlocked_reward_ids,
#: so renaming `name`/`description`/`icon` later is safe, but
#: reward_id itself must never change once shipped.
REWARD_DEFINITIONS: list[RewardDefinition] = [
    RewardDefinition(
        reward_id="john_deere_hat",
        name="John Deere Hat",
        description="Log 10 hours on your mower/equipment.",
        icon="🧢",
        stat_id="engine_hours_logged",
        threshold=10.0,
    ),
    RewardDefinition(
        reward_id="mission_rookie",
        name="Mission Rookie",
        description="Complete 5 missions.",
        icon="🎖️",
        stat_id="missions_completed",
        threshold=5.0,
    ),
    RewardDefinition(
        reward_id="mission_veteran",
        name="Mission Veteran",
        description="Complete 25 missions.",
        icon="🏅",
        stat_id="missions_completed",
        threshold=25.0,
    ),
    RewardDefinition(
        reward_id="iron_will",
        name="Iron Will",
        description="Log 5 hours of workouts.",
        icon="🔥",
        stat_id="workout_hours_logged",
        threshold=5.0,
    ),
]


def reward_progress_fraction(value: float, threshold: float) -> float:
    """Pure logic — testable without Qt/a real manager. Clamped to
    [0, 1] for a progress bar; a zero/negative threshold reads as
    "already complete" rather than dividing by zero."""
    if threshold <= 0:
        return 1.0
    return min(max(value / threshold, 0.0), 1.0)


class RewardsManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    # ------------------------------------------------------------------
    # Stat values — each one derived live from real data elsewhere.
    # ------------------------------------------------------------------

    def stat_value(self, stat_id: str) -> float:
        if stat_id == "engine_hours_logged":
            return self._compute_engine_hours_logged()
        if stat_id == "workout_hours_logged":
            return self._compute_workout_hours_logged()
        if stat_id == "missions_completed":
            return self._compute_missions_completed()
        return 0.0

    def all_stat_values(self) -> dict[str, float]:
        return {definition.stat_id: self.stat_value(definition.stat_id) for definition in STAT_DEFINITIONS}

    def _compute_engine_hours_logged(self) -> float:
        """Sums the latest "Engine Hours" reading across every real
        Maintenance asset that tracks one — not hardcoded to a single
        mower, so a future second piece of equipment with its own
        Engine Hours task counts too."""
        if self.context.maintenance is None:
            return 0.0
        total = 0.0
        for asset in self.context.maintenance.all_assets():
            for task in self.context.maintenance.tasks_for_asset(asset.asset_id):
                if task.title != "Engine Hours":
                    continue
                readings = self.context.maintenance.readings_for_task(task.task_id)
                if readings:
                    total += readings[-1].value
        return total

    def _compute_workout_hours_logged(self) -> float:
        if self.context.workout is None:
            return 0.0
        return sum(session.duration_minutes for session in self.context.workout.all_sessions()) / 60.0

    def _compute_missions_completed(self) -> float:
        if self.context.missions is None:
            return 0.0
        return float(sum(1 for mission in self.context.missions.all_missions() if mission.status == "completed"))

    # ------------------------------------------------------------------
    # Unlocking
    # ------------------------------------------------------------------

    def is_unlocked(self, profile_id: str, reward_id: str) -> bool:
        if self.context.profiles is None:
            return False
        profile = self.context.profiles.get_profile(profile_id)
        return profile is not None and reward_id in profile.unlocked_reward_ids

    def unlocked_reward_ids(self, profile_id: str) -> list[str]:
        if self.context.profiles is None:
            return []
        profile = self.context.profiles.get_profile(profile_id)
        return list(profile.unlocked_reward_ids) if profile is not None else []

    def scan_for_new_unlocks(self, profile_id: str) -> list[RewardDefinition]:
        """Idempotent — checks every reward definition's real stat
        value against its threshold, unlocking (and notifying) any
        that just crossed it. Safe to call as often as convenient; see
        this module's own docstring for the two real call sites."""
        if self.context.profiles is None:
            return []

        newly_unlocked: list[RewardDefinition] = []
        stat_values = self.all_stat_values()
        for reward in REWARD_DEFINITIONS:
            if self.is_unlocked(profile_id, reward.reward_id):
                continue
            if stat_values.get(reward.stat_id, 0.0) < reward.threshold:
                continue
            if self.context.profiles.unlock_reward(profile_id, reward.reward_id):
                newly_unlocked.append(reward)
                if self.context.notifications is not None:
                    self.context.notifications.notify(
                        title=f"{reward.icon} Reward unlocked!",
                        message=f"You unlocked \"{reward.name}\" — {reward.description}",
                        level="info",
                        source="achievements",
                    )
        return newly_unlocked

    # ------------------------------------------------------------------
    # Prestige emblems — derived live from Profile.prestige_tier, not
    # a second unlock-tracking system (see this module's own docstring).
    # ------------------------------------------------------------------

    def prestige_rewards_for_profile(self, profile_id: str) -> list[dict]:
        """One entry per prestige tier already reached — [{"name",
        "color"}], newest first. Not a RewardDefinition (there's no
        stat/threshold to check; prestige_tier IS the real record)."""
        if self.context.profiles is None:
            return []
        profile = self.context.profiles.get_profile(profile_id)
        if profile is None or profile.prestige_tier <= 0:
            return []
        return [
            {"name": f"Prestige {tier}", "color": prestige_color_for_tier(tier)}
            for tier in range(profile.prestige_tier, 0, -1)
        ]
