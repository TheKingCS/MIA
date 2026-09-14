"""
core.mission_patterns
========================

The first real "pattern inference" signal — core/pathway_manager.py's
own docstring names this "Phase 6: MIA inferring a pattern from
history," the one piece of the original "learns about itself" vision
still missing after core/discovery_manager.py proved out generating
from a snapshot of CURRENT state (Skills/Projects/Intent right now).
This looks at HISTORY instead — real completed/abandoned Missions over
time, not just what's true today.

Same observe -> insight -> recommend loop (core/insight_manager.py) as
core/maintenance_insights.py / core/mission_insights.py, the third real
domain to use it. Deliberately the smallest possible closed loop —
same discipline that scoped Discovery itself down originally — not the
full vision (skill-momentum trends, category-interest gaps, adaptive
difficulty); those are real, separate, explicitly future slices, not
attempted here.

v1's one real pattern: repeated Mission abandonment.
Mission.abandon_reason already exists specifically as a "struggle
signal" (2026-09-11, see core/mission_manager.py's own docstring) but
nothing has ever actually looked at it in aggregate before this. Reuses
core.mission_insights.days_since_last_touch() rather than re-deriving
"how long ago" math a second time.

Needs Mission.profile_id to actually be stamped on abandonment to
attribute a pattern to the right profile in a multi-user household —
core.mission_manager.MissionManager.update_mission() gained that stamp
this same pass (mirroring its existing on-completion stamp exactly).
An abandoned Mission from before that existed stays unattributed
(profile_id is None), same "shared/unknown" convention as everywhere
else in this codebase, and simply can't contribute to a specific
profile's own pattern.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.insight_manager import Insight
from core.mission_insights import days_since_last_touch
from core.mission_manager import Mission

_ABANDONMENT_WINDOW_DAYS = 30
_ABANDONMENT_THRESHOLD = 3

_REASON_LABELS = {
    "too_hard": "felt too hard",
    "not_interested": "weren't interesting",
    "no_time": "there wasn't time",
    "other": "other reasons",
}

_REASON_RECOMMENDATIONS = {
    "too_hard": "Try picking an easier difficulty for your next Mission.",
    "not_interested": "Try a Mission in a different category next time.",
    "no_time": "Try a smaller, quicker Mission next time.",
}
_DEFAULT_RECOMMENDATION = "Consider what would make your next Mission easier to stick with."


def recent_abandoned_missions(missions: list[Mission], profile_id: Optional[str], today: date) -> list[Mission]:
    """Pure logic — testable without Qt. Missions abandoned by
    `profile_id` within the last _ABANDONMENT_WINDOW_DAYS days."""
    result = []
    for mission in missions:
        if mission.status != "abandoned" or mission.profile_id != profile_id:
            continue
        days = days_since_last_touch(mission, today)
        if days is not None and days <= _ABANDONMENT_WINDOW_DAYS:
            result.append(mission)
    return result


def most_common_abandon_reason(missions: list[Mission]) -> str:
    """Pure logic — testable without Qt. The plurality abandon_reason
    among `missions` with a real one recorded; "" if none do (every
    Mission abandoned before that field existed, or reasons tied —
    ties fall back to the "other"/default framing rather than guessing
    which reason "really" won)."""
    counts: dict[str, int] = {}
    for mission in missions:
        if mission.abandon_reason:
            counts[mission.abandon_reason] = counts.get(mission.abandon_reason, 0) + 1
    if not counts:
        return ""
    top_count = max(counts.values())
    tied = [reason for reason, count in counts.items() if count == top_count]
    return tied[0] if len(tied) == 1 else ""


def format_abandonment_pattern_message(missions: list[Mission], reason: str) -> str:
    """Pure formatting logic — testable without Qt."""
    count = len(missions)
    noun = "Mission" if count == 1 else "Missions"
    message = f"You've abandoned {count} {noun} in the last {_ABANDONMENT_WINDOW_DAYS} days"
    label = _REASON_LABELS.get(reason)
    if label:
        message += f", most often because they {label}"
    return message + "."


def build_abandonment_recommendation(reason: str) -> str:
    """Pure logic — testable without Qt."""
    return _REASON_RECOMMENDATIONS.get(reason, _DEFAULT_RECOMMENDATION)


def scan_pattern_insights(context, today: date) -> list[Insight]:
    """Real, deterministic daily scan over every real profile's own
    recent Mission abandonments — creates a new "repeated_abandonment"
    Insight (+ Recommendation) the moment a profile crosses
    _ABANDONMENT_THRESHOLD within the rolling window, resolves it once
    they're back under it. Returns only the Insights newly created
    THIS run, for batching into one notification — same shape as
    core.mission_insights.scan_mission_insights()."""
    if context.missions is None or context.insights is None or context.profiles is None:
        return []

    all_missions = context.missions.all_missions()
    new_insights: list[Insight] = []
    for profile in context.profiles.list_profiles():
        recent = recent_abandoned_missions(all_missions, profile.profile_id, today)
        # Scoped to this exact kind, not open_insights_for_source()'s
        # every-kind list — a profile can carry more than one real
        # "patterns" insight at once (see core/skill_patterns.py), and
        # resolving ALL of them here would wrongly clear an unrelated
        # one (e.g. an interest-gap insight) just because THIS profile
        # happens to be back under the abandonment threshold. Real bug,
        # found and fixed while adding that second pattern kind.
        existing_open = context.insights.open_insight_for("patterns", profile.profile_id, "repeated_abandonment")

        if len(recent) < _ABANDONMENT_THRESHOLD:
            if existing_open is not None:
                context.insights.resolve_insight(existing_open.insight_id)
            continue

        reason = most_common_abandon_reason(recent)
        title = f"\U0001F914 {profile.name}"
        message = format_abandonment_pattern_message(recent, reason)
        insight = context.insights.create_insight_if_new(
            source_type="patterns", source_id=profile.profile_id, kind="repeated_abandonment",
            title=title, message=message,
        )
        if insight is not None:
            context.insights.add_recommendation(insight.insight_id, build_abandonment_recommendation(reason))
            new_insights.append(insight)

    return new_insights


def format_pattern_insights_message(insights: list[Insight]) -> Optional[str]:
    """Pure formatting logic — testable without Qt. Same "join newly-
    created Insights into one message, None when there's nothing to
    say" shape as core.mission_insights.format_mission_insights_message()."""
    if not insights:
        return None
    return " ".join(insight.message for insight in insights)
