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

**Challenge chains + rarity (2026-09-14, second pass)** — the user's
own follow-up design handoff (see the
[[project_mia_prestige_rarity_vision]] memory) asked for escalating
tiers per stat (Rookie -> Ranger -> Groundskeeper -> Master, the exact
mowing example) with Borderlands-style rarity, not flat one-shot
rewards. A `ChallengeChain` is one stat's ladder of `ChallengeTier`s in
ascending threshold order; each tier carries a `rarity_index` (0-4,
Common..Legendary — see `core.rarity`) instead of a separate color
field, so rarity name/color both derive from the one index. Nothing
real had been unlocked yet under the old flat `RewardDefinition` ids
(confirmed against the real profile before renaming), so this is a
clean redesign, not a migration.

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
a tier is unlocked it stays unlocked even if the underlying stat later
reads lower (a data correction, a deleted log entry), the same "a real
choice/event, not a live computation" reasoning `Profile.prestige_tier`
already established.

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
not up to a day later). Because chain tiers are checked independently
against the same live stat value, a profile that already had, say, 60
real engine hours logged before this system existed unlocks every
tier up to that value in one scan, not just the newest one — the
correct behavior for retroactively crediting real past accomplishment
(see the "add Faith a profile, credit accomplishments" 2026-09-14 ask).

**Hidden achievements (2026-09-14, third pass)** — the handoff's own
section 9: "the user should NOT know every achievement exists." A
`HiddenAchievement` is checked against the SUM of one or more real
stats (see `combined_stat_value()`) rather than a single stat, so it
can recognize combined effort across areas (the handoff's own "Built
Different" example) — deliberately built only from the same 3 real
stats above, not the handoff's own broader "outdoor hours" example
(nothing here measures that yet). Some sit strictly between two
visible chain tiers as a genuine surprise bonus (`grinder` at 50
missions, between the visible `missions_veteran`@25 and
`missions_legend`@100). Unlocking reuses the exact same
`Profile.unlocked_reward_ids` field as chain tiers — same real,
one-way, persisted state — but `unlocked_hidden_achievements()` is the
ONLY read accessor, and it only ever returns ones already unlocked:
there is no "list every hidden achievement" or "progress toward a
locked one" method anywhere in this module, on purpose — the UI has
nothing to show for a hidden achievement until it's already earned.
Scanned by a separate `scan_for_new_hidden_achievements()` (not folded
into `scan_for_new_unlocks()`, which returns `list[ChallengeTier]` —
keeping the two scans separate avoids a mixed-type return list and
keeps existing `ChallengeTier`-typed callers unchanged) — call both
together at every real call site.

**Notification restraint (2026-09-14, fourth pass)** — the handoff's
own section 12/14: "avoid making every tiny event generate an
annoying notification... M.I.A. should intelligently determine what
deserves presentation." Before this pass, retroactively crediting a
profile with real prior history (e.g. "add Faith, credit her past
accomplishments") could fire many separate toasts back to back — a
real, reproduced case (6 notifications in one scan while building
slice 1). Both scans now collect every new unlock first and fire
exactly ONE notification per scan: a single unlock keeps its existing,
more specific text, but more than one batches into
`format_multi_unlock_notification()`'s "N rewards/hidden achievements
unlocked!" + a plain comma-joined name list — restraint is about
toast COUNT here, not about suppressing any real unlock.
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
class ChallengeTier:
    """One rung of a challenge chain — a stable reward_id (persisted in
    Profile.unlocked_reward_ids, must never change once shipped), the
    threshold against its chain's stat, and a rarity_index (0=Common
    .. 4=Legendary, see core.rarity) rather than a separate color."""

    reward_id: str
    name: str
    description: str
    icon: str
    threshold: float
    rarity_index: int


@dataclass(frozen=True)
class ChallengeChain:
    """One stat's escalating ladder of rewards, ascending threshold
    order — e.g. Mowing: Lawn Rookie (10 hrs) -> ... -> Master of the
    Grounds (1,000 hrs)."""

    chain_id: str
    stat_id: str
    tiers: tuple[ChallengeTier, ...]


@dataclass(frozen=True)
class HiddenAchievement:
    """A secret milestone — see this module's own docstring for why it
    is never shown (no progress bar, no visible entry) until actually
    unlocked. Checked against the SUM of `stat_ids` (all hour-based
    stats sum meaningfully; a count like missions_completed is used
    alone, never mixed into a sum with hours)."""

    achievement_id: str
    name: str
    description: str
    icon: str
    rarity_index: int
    stat_ids: tuple[str, ...]
    threshold: float


#: Every stat here has a real, already-logged data source — see this
#: module's own docstring for why "water used watering plants" (the
#: user's own example) isn't in this list yet. 2026-09-14 (expanded
#: lifetime stats pass): checked every other manager for a real,
#: already-logged source before adding one — Maintenance's own
#: Property-category tasks are all calendar-scheduled (done/not-done),
#: not meter-tracked, so there's no real "property hours" number to
#: read yet; deliberately left out rather than fabricated.
STAT_DEFINITIONS: list[StatDefinition] = [
    StatDefinition("engine_hours_logged", "Engine Hours Logged", "hrs", "🚜"),
    StatDefinition("workout_hours_logged", "Workout Hours Logged", "hrs", "💪"),
    StatDefinition("missions_completed", "Missions Completed", "", "🏆"),
    StatDefinition("vehicle_miles_logged", "Vehicle Miles Logged", "mi", "🚗"),
    StatDefinition("meals_cooked", "Meals Cooked", "", "🍳"),
    StatDefinition("projects_completed", "Projects Completed", "", "🛠️"),
]

#: v2 reward set — real escalating chains against the real stats above,
#: per the user's own tiered-challenge handoff. Icons are plain emoji
#: placeholders (real character/cosmetic art is deliberately deferred,
#: per this module's own docstring); each tier's reward_id is the
#: stable identifier persisted in Profile.unlocked_reward_ids, so
#: renaming name/description/icon/rarity_index later is safe, but
#: reward_id itself must never change once shipped.
CHALLENGE_CHAINS: list[ChallengeChain] = [
    ChallengeChain(
        chain_id="mowing",
        stat_id="engine_hours_logged",
        tiers=(
            ChallengeTier("mowing_rookie", "Lawn Rookie", "Log 10 hours on your mower/equipment.", "🧢", 10.0, 0),
            ChallengeTier("mowing_yard_worker", "Yard Worker", "Log 25 hours on your mower/equipment.", "🎽", 25.0, 1),
            ChallengeTier("mowing_ranger", "Lawn Ranger", "Log 50 hours on your mower/equipment.", "🧥", 50.0, 2),
            ChallengeTier("mowing_groundskeeper", "Groundskeeper", "Log 250 hours on your mower/equipment.", "👔", 250.0, 3),
            ChallengeTier("mowing_master", "Master of the Grounds", "Log 1,000 hours on your mower/equipment.", "🏆", 1000.0, 4),
        ),
    ),
    ChallengeChain(
        chain_id="missions",
        stat_id="missions_completed",
        tiers=(
            ChallengeTier("missions_rookie", "Mission Rookie", "Complete 5 missions.", "🎖️", 5.0, 0),
            ChallengeTier("missions_veteran", "Mission Veteran", "Complete 25 missions.", "🏅", 25.0, 2),
            ChallengeTier("missions_legend", "Mission Legend", "Complete 100 missions.", "🌟", 100.0, 4),
        ),
    ),
    ChallengeChain(
        chain_id="fitness",
        stat_id="workout_hours_logged",
        tiers=(
            ChallengeTier("fitness_getting_started", "Getting Started", "Log 5 hours of workouts.", "🔥", 5.0, 0),
            ChallengeTier("fitness_iron_will", "Iron Will", "Log 25 hours of workouts.", "💪", 25.0, 2),
            ChallengeTier("fitness_unbreakable", "Unbreakable", "Log 100 hours of workouts.", "⚡", 100.0, 4),
        ),
    ),
    # 2026-09-14 (expanded lifetime stats pass) — 3 new chains against
    # 3 new real stats (see STAT_DEFINITIONS above for why "property
    # hours" isn't among them).
    ChallengeChain(
        chain_id="road_warrior",
        stat_id="vehicle_miles_logged",
        tiers=(
            ChallengeTier("road_warrior_first_mile", "First Mile", "Log 1,000 miles on a real vehicle.", "🚗", 1000.0, 0),
            ChallengeTier("road_warrior_road_tripper", "Road Tripper", "Log 5,000 miles on a real vehicle.", "🗺️", 5000.0, 1),
            ChallengeTier("road_warrior_long_hauler", "Long Hauler", "Log 15,000 miles on a real vehicle.", "🛣️", 15000.0, 2),
            ChallengeTier("road_warrior_road_warrior", "Road Warrior", "Log 50,000 miles on a real vehicle.", "🏁", 50000.0, 3),
            ChallengeTier("road_warrior_odometer_legend", "Odometer Legend", "Log 100,000 miles on a real vehicle.", "🏆", 100000.0, 4),
        ),
    ),
    ChallengeChain(
        chain_id="home_chef",
        stat_id="meals_cooked",
        tiers=(
            ChallengeTier("home_chef_apprentice", "Kitchen Apprentice", "Cook 10 real meals.", "🍳", 10.0, 0),
            ChallengeTier("home_chef_line_cook", "Line Cook", "Cook 25 real meals.", "🥘", 25.0, 1),
            ChallengeTier("home_chef_sous_chef", "Sous Chef", "Cook 100 real meals.", "👨‍🍳", 100.0, 2),
            ChallengeTier("home_chef_head_chef", "Head Chef", "Cook 250 real meals.", "🍽️", 250.0, 3),
            ChallengeTier("home_chef_iron_chef", "Iron Chef", "Cook 500 real meals.", "🏆", 500.0, 4),
        ),
    ),
    ChallengeChain(
        chain_id="builder",
        stat_id="projects_completed",
        tiers=(
            ChallengeTier("builder_first_build", "First Build", "Complete 1 real project.", "🔨", 1.0, 0),
            ChallengeTier("builder_handy", "Handy", "Complete 5 real projects.", "🧰", 5.0, 1),
            ChallengeTier("builder_craftsman", "Craftsman", "Complete 15 real projects.", "🛠️", 15.0, 2),
            ChallengeTier("builder_master_builder", "Master Builder", "Complete 30 real projects.", "🏗️", 30.0, 3),
            ChallengeTier("builder_legendary_maker", "Legendary Maker", "Complete 50 real projects.", "🏆", 50.0, 4),
        ),
    ),
]

#: Never enumerated to the user ahead of unlock — see this module's
#: own docstring and HiddenAchievement's own docstring. `grinder` sits
#: strictly between the visible mowing/missions chain tiers on
#: purpose, a real surprise bonus mid-progression.
HIDDEN_ACHIEVEMENTS: list[HiddenAchievement] = [
    HiddenAchievement(
        "built_different", "Built Different",
        "Complete 50 combined hours of equipment work and workouts.",
        "\U0001F4AA", 3, ("engine_hours_logged", "workout_hours_logged"), 50.0,
    ),
    HiddenAchievement(
        "grinder", "Grinder",
        "Complete 50 missions total.",
        "⚙️", 2, ("missions_completed",), 50.0,
    ),
    HiddenAchievement(
        "renaissance", "Renaissance",
        "Complete 200 combined hours of equipment work and workouts.",
        "\U0001F31F", 4, ("engine_hours_logged", "workout_hours_logged"), 200.0,
    ),
]


def all_tiers() -> list[ChallengeTier]:
    """Every tier across every chain, flattened — testable without a
    real manager. Used for both scanning and simple iteration where a
    caller doesn't need chain grouping."""
    return [tier for chain in CHALLENGE_CHAINS for tier in chain.tiers]


def stat_id_for_tier(reward_id: str) -> Optional[str]:
    """Which chain (by stat_id) a given tier's reward_id belongs to —
    pure logic, testable without a real manager. Looked up by
    reward_id rather than dataclass equality so two coincidentally
    identical tiers in different chains can never cross-match."""
    for chain in CHALLENGE_CHAINS:
        for tier in chain.tiers:
            if tier.reward_id == reward_id:
                return chain.stat_id
    return None


def reward_progress_fraction(value: float, threshold: float) -> float:
    """Pure logic — testable without Qt/a real manager. Clamped to
    [0, 1] for a progress bar; a zero/negative threshold reads as
    "already complete" rather than dividing by zero."""
    if threshold <= 0:
        return 1.0
    return min(max(value / threshold, 0.0), 1.0)


def highest_unlocked_tier(tiers: tuple[ChallengeTier, ...], unlocked_ids: set[str]) -> Optional[ChallengeTier]:
    """The furthest tier already unlocked in a chain (tiers is ascending
    threshold order), or None if the chain hasn't been started. Pure
    logic — testable without a real manager."""
    result: Optional[ChallengeTier] = None
    for tier in tiers:
        if tier.reward_id in unlocked_ids:
            result = tier
    return result


def next_locked_tier(tiers: tuple[ChallengeTier, ...], unlocked_ids: set[str]) -> Optional[ChallengeTier]:
    """The next tier still locked in a chain, or None once every tier
    is unlocked (the chain is maxed out). Pure logic — testable without
    a real manager."""
    for tier in tiers:
        if tier.reward_id not in unlocked_ids:
            return tier
    return None


def combined_stat_value(stat_values: dict[str, float], stat_ids: tuple[str, ...]) -> float:
    """Sums the named stats out of a stat_values dict (e.g.
    RewardsManager.all_stat_values()) — pure logic, testable without a
    real manager. Used to check a HiddenAchievement's combined-effort
    threshold."""
    return sum(stat_values.get(stat_id, 0.0) for stat_id in stat_ids)


def format_multi_unlock_notification(names: list[str], noun: str) -> tuple[str, str]:
    """Pure logic — testable without a real manager. One notification
    covering every unlock from a single scan, instead of one toast per
    unlock — the handoff's own section 12/14 restraint ("avoid making
    every tiny event generate an annoying notification"; "M.I.A. should
    intelligently determine what deserves presentation"). Only used
    when a scan finds MORE than one new unlock at once (a single unlock
    keeps its own existing, more specific notification text — see
    RewardsManager._notify_unlocked_tiers()/_notify_unlocked_hidden_achievements())."""
    return (f"\U0001F389 {len(names)} {noun} unlocked!", ", ".join(names))


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
        if stat_id == "vehicle_miles_logged":
            return self._compute_vehicle_miles_logged()
        if stat_id == "meals_cooked":
            return self._compute_meals_cooked()
        if stat_id == "projects_completed":
            return self._compute_projects_completed()
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

    def _compute_vehicle_miles_logged(self) -> float:
        """Sums the latest "Odometer" reading across every real
        Maintenance asset that tracks one — same "match by task title,
        not by asset category" pattern as _compute_engine_hours_logged(),
        so a future second vehicle's own Odometer task counts too.
        Deliberately NOT summing every mileage-unit task (Oil & filter
        change, Brake inspection, ... also log in miles) — those track
        miles-since-last-service, not the vehicle's real lifetime
        total, which only the Odometer task itself represents."""
        if self.context.maintenance is None:
            return 0.0
        total = 0.0
        for asset in self.context.maintenance.all_assets():
            for task in self.context.maintenance.tasks_for_asset(asset.asset_id):
                if task.title != "Odometer":
                    continue
                readings = self.context.maintenance.readings_for_task(task.task_id)
                if readings:
                    total += readings[-1].value
        return total

    def _compute_meals_cooked(self) -> float:
        if self.context.kitchen is None:
            return 0.0
        return float(len(self.context.kitchen.all_meal_log_entries()))

    def _compute_projects_completed(self) -> float:
        if self.context.projects is None:
            return 0.0
        return float(sum(1 for project in self.context.projects.all_projects() if project.status == "Complete"))

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

    def scan_for_new_unlocks(self, profile_id: str) -> list[ChallengeTier]:
        """Idempotent — checks every chain tier's real stat value
        against its threshold, unlocking (and notifying) any that just
        crossed it. Safe to call as often as convenient; see this
        module's own docstring for the two real call sites. Checks
        every tier independently (not just the next one in each chain),
        so a stat that's already well past several thresholds unlocks
        all of them at once — the correct behavior for retroactively
        crediting real past accomplishment, not just newly-logged
        activity. Notification restraint (2026-09-14): fires ONE
        notification per scan regardless of how many tiers just
        unlocked, not one toast per tier — see
        format_multi_unlock_notification()'s own docstring."""
        if self.context.profiles is None:
            return []

        newly_unlocked: list[ChallengeTier] = []
        stat_values = self.all_stat_values()
        for tier in all_tiers():
            if self.is_unlocked(profile_id, tier.reward_id):
                continue
            stat_id = stat_id_for_tier(tier.reward_id)
            if stat_values.get(stat_id, 0.0) < tier.threshold:
                continue
            if self.context.profiles.unlock_reward(profile_id, tier.reward_id):
                newly_unlocked.append(tier)

        if newly_unlocked and self.context.notifications is not None:
            self._notify_unlocked_tiers(newly_unlocked)
        return newly_unlocked

    def _notify_unlocked_tiers(self, tiers: list[ChallengeTier]) -> None:
        if len(tiers) == 1:
            tier = tiers[0]
            self.context.notifications.notify(
                title=f"{tier.icon} Reward unlocked!",
                message=f"You unlocked \"{tier.name}\" — {tier.description}",
                level="info",
                source="achievements",
            )
            return
        title, message = format_multi_unlock_notification([tier.name for tier in tiers], "rewards")
        self.context.notifications.notify(title=title, message=message, level="info", source="achievements")

    # ------------------------------------------------------------------
    # Hidden achievements — see this module's own docstring and
    # HiddenAchievement's own docstring for why there is no "list every
    # hidden achievement" or "progress toward a locked one" accessor.
    # ------------------------------------------------------------------

    def unlocked_hidden_achievements(self, profile_id: str) -> list[HiddenAchievement]:
        """Only ever returns achievements already unlocked — never
        exposes a locked one's existence, name, or threshold."""
        unlocked_ids = set(self.unlocked_reward_ids(profile_id))
        return [achievement for achievement in HIDDEN_ACHIEVEMENTS if achievement.achievement_id in unlocked_ids]

    def scan_for_new_hidden_achievements(self, profile_id: str) -> list[HiddenAchievement]:
        """Idempotent, same shape as scan_for_new_unlocks() — kept as
        its own method (not folded into scan_for_new_unlocks()) so that
        method's return type stays list[ChallengeTier] for its existing
        callers; call both together at every real call site. Same
        notification-restraint batching as scan_for_new_unlocks()."""
        if self.context.profiles is None:
            return []

        newly_unlocked: list[HiddenAchievement] = []
        stat_values = self.all_stat_values()
        for achievement in HIDDEN_ACHIEVEMENTS:
            if self.is_unlocked(profile_id, achievement.achievement_id):
                continue
            if combined_stat_value(stat_values, achievement.stat_ids) < achievement.threshold:
                continue
            if self.context.profiles.unlock_reward(profile_id, achievement.achievement_id):
                newly_unlocked.append(achievement)

        if newly_unlocked and self.context.notifications is not None:
            self._notify_unlocked_hidden_achievements(newly_unlocked)
        return newly_unlocked

    def _notify_unlocked_hidden_achievements(self, achievements: list[HiddenAchievement]) -> None:
        if len(achievements) == 1:
            achievement = achievements[0]
            self.context.notifications.notify(
                title=f"{achievement.icon} Hidden Achievement Unlocked!",
                message=f"\"{achievement.name}\" — {achievement.description}",
                level="info",
                source="achievements",
            )
            return
        title, message = format_multi_unlock_notification(
            [achievement.name for achievement in achievements], "hidden achievements",
        )
        self.context.notifications.notify(title=title, message=message, level="info", source="achievements")

    # ------------------------------------------------------------------
    # Prestige emblems — derived live from Profile.prestige_tier, not
    # a second unlock-tracking system (see this module's own docstring).
    # ------------------------------------------------------------------

    def prestige_rewards_for_profile(self, profile_id: str) -> list[dict]:
        """One entry per prestige tier already reached — [{"name",
        "color"}], newest first. Not a ChallengeTier (there's no
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
