"""
core.progress_history
=======================

A prestige reached or a reward unlocked, kept in that person's history
(2026-11-09, from the self-audit's unheard events). The profile manager
publishes `profile.prestiged` and `profile.reward_unlocked`, and until
now nothing heard either: a toast said it, and then it was gone, so the
Chronicle and "what did I do this month?" never knew. `subscribe()`
hears both and records a life event in the person's own folder (the
profile's data_dir, so a reward earned from the phone is theirs, not
whoever is signed in at the PC), naming the reward from its tier or
hidden achievement.
"""

from __future__ import annotations

from core import life_events
from core.logger import get_logger

log = get_logger(__name__)


def reward_name(reward_id: str) -> str:
    """Pure logic. A reward's name from its challenge tier or hidden achievement, or "" for one not known."""
    from core.rewards_manager import HIDDEN_ACHIEVEMENTS, all_tiers

    for tier in all_tiers():
        if tier.reward_id == reward_id:
            return tier.name
    return next((a.name for a in HIDDEN_ACHIEVEMENTS if a.achievement_id == reward_id), "")


def _profile(context, profile_id: str):
    """The profile, or None (no profiles here, or it's gone)."""
    profiles = getattr(context, "profiles", None)
    return profiles.get_profile(profile_id) if profiles is not None and profile_id else None


def on_prestiged(context):
    """The handler for profile.prestiged: "Reached prestige tier N" in that person's history."""
    def heard(profile_id: str = "", new_tier: int = 0, **_):
        """Records the prestige; nothing when the profile is gone."""
        profile = _profile(context, profile_id)
        if profile is not None:
            life_events.record(profile, "prestiged", f"Reached prestige tier {new_tier}",
                               payload={"tier": new_tier}, profile_id=profile_id)
    return heard


def on_reward_unlocked(context):
    """The handler for profile.reward_unlocked: "Unlocked <reward>" in that person's history."""
    def heard(profile_id: str = "", reward_id: str = "", **_):
        """Records the reward, by name when it's known; nothing when the profile is gone."""
        profile = _profile(context, profile_id)
        if profile is not None:
            name = reward_name(reward_id)
            life_events.record(profile, "reward_unlocked", f"Unlocked {name}" if name else "Unlocked a reward",
                               payload={"reward_id": reward_id}, profile_id=profile_id)
    return heard


def subscribe(context) -> None:
    """Hears both events on the context's bus (the desktop app and headless Core each call this once)."""
    events = getattr(context, "events", None)
    if events is None:
        return
    events.subscribe("profile.prestiged", on_prestiged(context))
    events.subscribe("profile.reward_unlocked", on_reward_unlocked(context))
