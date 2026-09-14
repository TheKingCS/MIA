"""
core.skill_patterns
======================

The second Pattern Insight slice — scoped directly with the user, not
assumed (see core/mission_patterns.py's own docstring for the first,
repeated Mission abandonment, and mia_system_vision's "Phase 6"
framing this whole thread continues). Same observe -> insight ->
recommend loop, a genuinely different real signal: a stated interest
with zero real engagement, not a history-of-actions pattern.

v1's one real pattern: a profile picked a real interest category at
the profile-creation interview (`Profile.interests`,
core/profile_manager.py) but has earned literally zero skill XP in any
skill under that category. Checked only once the profile is at least
_INTEREST_GAP_GRACE_DAYS old — a brand-new profile hasn't had time to
touch anything yet, so flagging immediately would be noise, not a real
signal. No new data model: reuses `Profile.interests`/`created_at` and
`SkillManager.skills_in_category()`/`get_progress()` exactly as they
already exist.

Shares `source_type="patterns"` with core/mission_patterns.py (both
are real "noticed from history/state, not from one specific record"
signals — the same Observations module section groups them together
deliberately) but a DIFFERENT `kind` ("interest_gap" vs.
"repeated_abandonment"), so `core.insight_manager.Insight`'s own
(source_type, source_id, kind) dedup key keeps them fully independent
per profile — see core/mission_patterns.py's own `scan_pattern_insights()`
for the real bug this distinction fixed (resolving one kind must never
touch a different kind's insight for the same profile).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from core.insight_manager import Insight
from core.profile_manager import Profile

_INTEREST_GAP_GRACE_DAYS = 30


def _profile_age_days(profile: Profile, today: date) -> Optional[int]:
    """Pure logic — testable without Qt. None if created_at is missing
    or unparseable — no evidence to judge "old enough" against, so the
    scan below treats that the same as "too new to flag"."""
    if not profile.created_at:
        return None
    try:
        created = datetime.fromisoformat(profile.created_at).date()
    except ValueError:
        return None
    return (today - created).days


def total_xp_in_category(skill_manager, profile_id: str, category: str) -> int:
    """Pure-ish (reads skill_manager's already-loaded state, no I/O of
    its own). Zero for a category the profile has never earned any XP
    in — same "untrained skill is 0 XP, not a missing record"
    convention SkillManager.get_progress() already establishes."""
    return sum(
        skill_manager.get_progress(profile_id, skill.skill_id).total_xp
        for skill in skill_manager.skills_in_category(category)
    )


def untouched_interests(skill_manager, profile: Profile) -> list[str]:
    """Pure-ish logic. `profile.interests` with literally zero real XP
    earned in any skill under them, in the order the profile picked
    them (not re-sorted)."""
    return [
        category for category in profile.interests
        if total_xp_in_category(skill_manager, profile.profile_id, category) == 0
    ]


def _join_with_and(items: list[str]) -> str:
    """Pure logic — testable without Qt. "A" / "A and B" / "A, B, and C"."""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def format_interest_gap_message(untouched: list[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    categories = _join_with_and(untouched)
    return f"You said you're interested in {categories}, but haven't earned any real XP there yet."


def build_interest_gap_recommendation(untouched: list[str]) -> str:
    """Pure logic — testable without Qt."""
    if len(untouched) == 1:
        return f"Try a Mission or Pathway in {untouched[0]} to get started."
    return "Try a Mission or Pathway in one of these categories to get started."


def scan_skill_pattern_insights(context, today: date) -> list[Insight]:
    """Real, deterministic daily scan over every real profile's own
    stated interests — creates a new "interest_gap" Insight (+
    Recommendation) the moment a profile (old enough to judge) has a
    real interest with zero real engagement, resolves it the moment
    any real XP lands in that category. Returns only the Insights
    newly created THIS run — same shape as
    core.mission_patterns.scan_pattern_insights()."""
    if context.profiles is None or context.skills is None or context.insights is None:
        return []

    new_insights: list[Insight] = []
    for profile in context.profiles.list_profiles():
        existing_open = context.insights.open_insight_for("patterns", profile.profile_id, "interest_gap")

        age_days = _profile_age_days(profile, today)
        old_enough = age_days is not None and age_days >= _INTEREST_GAP_GRACE_DAYS
        untouched = untouched_interests(context.skills, profile) if old_enough else []

        if not untouched:
            if existing_open is not None:
                context.insights.resolve_insight(existing_open.insight_id)
            continue

        title = f"\U0001F3AF {profile.name}"
        message = format_interest_gap_message(untouched)
        insight = context.insights.create_insight_if_new(
            source_type="patterns", source_id=profile.profile_id, kind="interest_gap",
            title=title, message=message,
        )
        if insight is not None:
            context.insights.add_recommendation(insight.insight_id, build_interest_gap_recommendation(untouched))
            new_insights.append(insight)

    return new_insights


def format_skill_pattern_insights_message(insights: list[Insight]) -> Optional[str]:
    """Pure formatting logic — testable without Qt. Same "join newly-
    created Insights into one message, None when there's nothing to
    say" shape as core.mission_patterns.format_pattern_insights_message()."""
    if not insights:
        return None
    return " ".join(insight.message for insight in insights)
