"""
core.mission_insights
========================

The Missions-domain scan for the observe -> understand -> insight ->
recommend -> act -> result loop (core/insight_manager.py) — the second
domain this loop covers, after core/maintenance_insights.py (see its
own docstring for the full reasoning behind Insight/Recommendation;
this file mirrors its shape exactly rather than reinventing it).
docs/VISION.md's Smart Suggestions section named "Missions-stale"
notifications as a natural extension once this machinery existed —
this is that extension, built against the real Insight/Recommendation
plumbing rather than a fifth separate notification mechanism.

Deliberately invents no new "how long has this been idle" math beyond
Mission.updated_at itself — every add_objective()/increment_tally()/
update_mission() call already bumps it
(core/mission_manager.py's own _bump_updated_at()), so it's already a
reliable "last real touch" signal, not something this file needs to
derive from scratch.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from core.insight_manager import Insight
from core.mission_manager import Mission

# A mission being actively worked gets touched at least every couple
# of weeks in practice (an objective ticked, a status edit); two full
# weeks of total silence on a still-"active" mission is a real signal
# it may have been forgotten, not just "not urgent today" — same
# reasoning core.maintenance_insights._DUE_SOON_WITHIN_DAYS gives a
# number to its own window, not an arbitrary pick.
_STALE_AFTER_DAYS = 14


def _last_touched(mission: Mission) -> Optional[date]:
    """mission.updated_at, falling back to created_at for a mission
    never edited since creation. Returns None (can't compute
    staleness) if both are blank — a mission from before either field
    existed."""
    raw = mission.updated_at or mission.created_at
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def days_since_last_touch(mission: Mission, today: date) -> Optional[int]:
    """Pure logic — testable without Qt."""
    last_touched = _last_touched(mission)
    if last_touched is None:
        return None
    return (today - last_touched).days


def is_stale(mission: Mission, today: date) -> bool:
    """Pure logic — testable without Qt. Only an "active" mission can
    go stale — a completed/abandoned one has already reached its own
    real resolution, nothing left to nudge about."""
    if mission.status != "active":
        return False
    days = days_since_last_touch(mission, today)
    return days is not None and days >= _STALE_AFTER_DAYS


def scan_mission_insights(context, today: date) -> list[Insight]:
    """Real, deterministic daily scan over every Mission — creates a
    new "stale" Insight (+ a linked Recommendation) for any mission
    newly gone quiet, resolves it automatically the moment the mission
    is touched again or leaves "active" status through the existing
    Missions UI. Returns only the Insights newly created THIS run, for
    batching into one notification — see
    format_mission_insights_message()."""
    if context.missions is None or context.insights is None:
        return []

    new_insights: list[Insight] = []
    for mission in context.missions.all_missions():
        existing_open = context.insights.open_insights_for_source("missions", mission.mission_id)

        if not is_stale(mission, today):
            for insight in existing_open:
                context.insights.resolve_insight(insight.insight_id)
            continue

        days = days_since_last_touch(mission, today)
        title = f"\U0001F4A4 {mission.name}"
        message = f"'{mission.name}' hasn't been touched in {days} days."
        insight = context.insights.create_insight_if_new(
            source_type="missions", source_id=mission.mission_id, kind="stale", title=title, message=message,
        )
        if insight is not None:
            context.insights.add_recommendation(
                insight.insight_id, f"Make progress on '{mission.name}', or abandon it in Missions."
            )
            new_insights.append(insight)

    return new_insights


def format_mission_insights_message(insights: list[Insight]) -> Optional[str]:
    """Pure formatting logic — testable without Qt. Same "join newly-
    created Insights into one message, None when there's nothing to
    say" shape as
    core.maintenance_insights.format_maintenance_insights_message()."""
    if not insights:
        return None
    return " ".join(insight.message for insight in insights)
