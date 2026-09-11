"""
core.gamification
====================

Shared "grant XP for a real completion" helper — docs/VISION.md's
Missions/Gamification concept, extended 2026-09-11 from the dedicated
Missions module out to routine completion moments in other domains
(Kitchen/Workout/Maintenance/Budget), at the user's own explicit
request to make MIA feel more like a game "System" narrator.

**2026-09-11, "My Hero's Path" pass**: gained an optional
`skill_weights` param so one real activity can train several
core.skill_manager.SkillManager skills at once (e.g. a workout session
crediting both profile-wide XP and Strength skill XP) — see
docs/ROADMAP.md's dated entry for the full design. Backward compatible
by construction: `skill_weights` defaults to `None`, so every call
site written before this pass keeps compiling and behaving identically
with zero edits.

Deliberately a thin wrapper around machinery that already exists and
is already proven — not a new reward/notification mechanism:
`context.profiles.add_xp()`/`add_credits()` (the exact same crediting
methods `core.mission_manager.MissionManager._credit_mission_rewards()`
already uses) and `context.notifications.notify()` (the exact same
toast+persisted delivery Missions' own completion callouts already use,
same emoji-led-title/second-person-encouraging-message voice —
`"\U0001F3C6 Objective complete!"`, `"\U0001F389 Mission complete!"`).
Graceful-degradation stance mirrors `_credit_mission_rewards()` exactly:
no active profile (or no profiles/notifications service at all, e.g.
during first-run setup) just means no one to credit — never raises.

**Reward sizing is deliberately small and flat, not tuned.**
core/leveling.py's own docstring states per-Mission rewards run "tens to
low hundreds of XP" — routine actions here stay well under that (5-10
XP), so logging a meal or finishing a workout never competes with
actually completing a Mission. No credits are granted for routine
actions either — credits stay Mission-specific, a bigger reward for the
"main quest" rather than routine "side activity." Revisit these numbers
once real usage shows whether they feel right; there's no formula to
derive them from today (Mission rewards are hand-entered flat ints too).

**No rate-limiting** — deliberately not added. Every real call site this
is wired into (finishing a workout session, logging a meal, marking a
maintenance task or bill complete) is already an infrequent, deliberate
user action, not something that could be spammed in a tight loop the
way, say, an inventory-quantity tweak could be.
"""

from __future__ import annotations

from typing import NamedTuple, Optional

from core.app_context import AppContext


class SkillWeight(NamedTuple):
    """One (skill_id, xp) entry in a `skill_weights` list — how much a
    single real activity should train a single Skill. A list of these
    is how one activity trains several skills at once (My Hero's
    Path's "multi-skill activities" concept) without grant_xp() itself
    needing to know anything about what the activity was."""

    skill_id: str
    xp: int


def grant_xp(
    context: AppContext,
    amount: int,
    title: str,
    message: str,
    credits: int = 0,
    skill_weights: Optional[list[SkillWeight]] = None,
) -> None:
    """Credits `amount` XP (and optionally `credits`) to the active
    profile, credits each entry in `skill_weights` to its Skill (if
    `context.skills` is wired), and raises a real notification
    announcing it — the one shared path every routine-completion hook
    in this codebase should call through, rather than each
    reimplementing the credit+notify pairing on its own.

    `skill_weights` gracefully no-ops (same stance as the profile-XP
    crediting below) if `context.skills` isn't wired or there's no
    active profile — never raises."""
    active_profile = None
    if context.profiles is not None:
        active_profile = context.profiles.get_active_profile()
        if active_profile is not None:
            if amount:
                context.profiles.add_xp(active_profile.profile_id, amount)
            if credits:
                context.profiles.add_credits(active_profile.profile_id, credits)

    if skill_weights and context.skills is not None and active_profile is not None:
        for weight in skill_weights:
            context.skills.add_skill_xp(active_profile.profile_id, weight.skill_id, weight.xp)

    if context.notifications is not None:
        context.notifications.notify(title=title, message=message, level="info", source="gamification")
