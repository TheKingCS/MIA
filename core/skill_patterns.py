"""
core.skill_patterns
======================

Pattern Insight slices 2 and 3 — scoped directly with the user, not
assumed (see core/mission_patterns.py's own docstring for slice 1,
repeated Mission abandonment, and mia_system_vision's "Phase 6"
framing this whole thread continues). Same observe -> insight ->
recommend loop; both slices here read the Skill/Profile domain, unlike
mission_patterns.py's Mission-history domain — the reason they share
this file rather than each getting a separate one the way
mission_insights.py/mission_patterns.py do (those two barely share any
code; these two share imports, a join-with-"and" formatter, and the
per-profile loop shape).

**Slice 2 — interest gaps**: a profile picked a real interest category
at the profile-creation interview (`Profile.interests`,
core/profile_manager.py) but has earned literally zero skill XP in any
skill under that category. Checked only once the profile is at least
_INTEREST_GAP_GRACE_DAYS old — a brand-new profile hasn't had time to
touch anything yet.

**Slice 3 — skill decline**: a category the profile DID genuinely
engage with (real historical XP > 0) but hasn't earned any new XP in
for _DECLINE_AFTER_DAYS+ — the mirror image of slice 2 (used to, then
stopped, vs. never started). This needed one real new field,
`SkillProgress.last_touched` (core/skill_manager.py) — XP is granted
from many places (Missions, Workout, Kitchen, Budget, Maintenance,
Project, Classroom, all through the one shared `grant_xp()` ->
`add_skill_xp()` choke point), so deriving "last touched" from any ONE
activity source (e.g. completed Missions alone) would be wrong; a
persisted timestamp at the actual choke point is the correct fix here,
not a "derive it, don't duplicate" violation, since no other single
source has this information to derive it from. A skill with real XP
but no real `last_touched` (earned before that field existed) can't be
judged either way and is treated as "no evidence," not flagged.

Both slices share `source_type="patterns"` with
core/mission_patterns.py's own signal (the same Observations module
section groups all three together) but each has its own distinct
`kind` ("interest_gap" / "skill_decline" / "repeated_abandonment"), so
`core.insight_manager.Insight`'s (source_type, source_id, kind) dedup
key keeps all three fully independent per profile — see
core/mission_patterns.py's own `scan_pattern_insights()` docstring for
the real cross-kind resolution bug slice 2 found and fixed in slice 1.
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


# ------------------------------------------------------------------
# Slice 3 — skill decline
# ------------------------------------------------------------------

_DECLINE_AFTER_DAYS = 60


def _last_touched_date(last_touched: str) -> Optional[date]:
    """Pure logic — testable without Qt. None for blank/unparseable —
    "no evidence," not "infinitely long ago"."""
    if not last_touched:
        return None
    try:
        return datetime.fromisoformat(last_touched).date()
    except ValueError:
        return None


def declining_categories(skill_manager, profile_id: str, today: date) -> list[str]:
    """Pure-ish logic (reads skill_manager's already-loaded state).
    Categories where this profile has real historical XP (> 0 in at
    least one skill) but nothing in that category has real evidence of
    being touched within _DECLINE_AFTER_DAYS. A category with real XP
    but zero real last_touched evidence (every skill in it earned
    before that field existed) is left alone — genuinely can't judge,
    not the same as "definitely stale.\""""
    declining = []
    for category in skill_manager.categories():
        has_real_xp = False
        touch_dates: list[date] = []
        for skill in skill_manager.skills_in_category(category):
            progress = skill_manager.get_progress(profile_id, skill.skill_id)
            if progress.total_xp > 0:
                has_real_xp = True
                touched = _last_touched_date(progress.last_touched)
                if touched is not None:
                    touch_dates.append(touched)
        if not has_real_xp or not touch_dates:
            continue
        most_recent = max(touch_dates)
        if (today - most_recent).days >= _DECLINE_AFTER_DAYS:
            declining.append(category)
    return declining


def format_decline_message(declining: list[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    categories = _join_with_and(declining)
    return f"You used to be active in {categories}, but haven't earned any real XP there in {_DECLINE_AFTER_DAYS}+ days."


def build_decline_recommendation(declining: list[str]) -> str:
    """Pure logic — testable without Qt."""
    if len(declining) == 1:
        return f"Pick up a Mission in {declining[0]} again, or let it go for now."
    return "Consider picking one of these back up, or letting it go for now."


def scan_skill_decline_insights(context, today: date) -> list[Insight]:
    """Real, deterministic daily scan over every real profile's own
    skill categories — creates a new "skill_decline" Insight (+
    Recommendation) the moment a category with real history goes
    quiet for _DECLINE_AFTER_DAYS+, resolves it the moment any real XP
    lands there again. Returns only the Insights newly created THIS
    run — same shape as scan_skill_pattern_insights() above."""
    if context.profiles is None or context.skills is None or context.insights is None:
        return []

    new_insights: list[Insight] = []
    for profile in context.profiles.list_profiles():
        existing_open = context.insights.open_insight_for("patterns", profile.profile_id, "skill_decline")
        declining = declining_categories(context.skills, profile.profile_id, today)

        if not declining:
            if existing_open is not None:
                context.insights.resolve_insight(existing_open.insight_id)
            continue

        title = f"\U0001F4C9 {profile.name}"
        message = format_decline_message(declining)
        insight = context.insights.create_insight_if_new(
            source_type="patterns", source_id=profile.profile_id, kind="skill_decline",
            title=title, message=message,
        )
        if insight is not None:
            context.insights.add_recommendation(insight.insight_id, build_decline_recommendation(declining))
            new_insights.append(insight)

    return new_insights


def format_skill_decline_insights_message(insights: list[Insight]) -> Optional[str]:
    """Pure formatting logic — testable without Qt. Same "join newly-
    created Insights into one message, None when there's nothing to
    say" shape as format_skill_pattern_insights_message() above."""
    if not insights:
        return None
    return " ".join(insight.message for insight in insights)
