"""
core.context_assembler
=========================

The "Life State" layer — a real service answering "what's going on in
this person's life right now," synthesized live from every domain
manager already in AppContext. This exact shape was discussed and
agreed on 2026-09-11 (see mia_system_vision's own dated entry: a
context_assembler.py query layer as the "world model" — a live view,
not a stored object) and then never actually built until now, at the
user's own explicit request after an external architecture review
named it the single most valuable missing piece.

Deliberately NOT a new database and NOT a second source of truth for
anything: every field on `LifeStateSnapshot` is computed fresh from
real, already-owned state each time `assemble_life_state()` runs —
Missions, recurring-mission streaks, Skill categories (reusing
core.skill_patterns' own momentum/decline/gap functions rather than
reimplementing them), open Insights, overdue Maintenance, and active
Projects. If any underlying manager's data changes, the next call
reflects it immediately — nothing here is cached or persisted.

GUI-only, same reason core.mission_patterns/core.skill_patterns' own
scans are GUI-only: context.insights/context.maintenance/
context.projects/context.recurring_missions are only ever constructed
in core/application.py, not core/core_runtime.py's headless boot path.
Every field gracefully degrades to empty/zero if its manager isn't
wired, rather than raising — same stance every other optional-service
check in this codebase takes.

The first real consumer is an Assistant action ("what's going on with
me?") so a user can get one synthesized answer instead of checking a
dozen screens. Future consumers (Discovery reasoning over the same
state, a Dashboard "System HUD" section, cross-tree Pattern Insights
correlation) should all read from this same function rather than each
re-deriving their own partial view — the whole reason this is worth
having as one shared layer instead of staying inline in one caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from core.maintenance_manager import is_overdue
from core.skill_patterns import declining_categories, momentum_categories, untouched_interests


@dataclass
class LifeStateSnapshot:
    """A live, synthesized read of one profile's current state — never
    persisted, rebuilt fresh on every call to assemble_life_state()."""

    profile_id: str
    active_mission_count: int = 0
    # (template display name, current streak) for every recurring
    # template with a real streak > 0 right now — a 0-streak template
    # isn't "going on" in the person's life, so it's left out rather
    # than padded with zeros.
    recurring_streaks: list[tuple[str, int]] = field(default_factory=list)
    skills_growing: list[str] = field(default_factory=list)
    skills_declining: list[str] = field(default_factory=list)
    skills_dormant: list[str] = field(default_factory=list)
    # Open Insight messages relevant to this profile — this profile's
    # own Pattern Insights (source_type="patterns", scoped by
    # source_id == profile_id) plus every other still-open Insight,
    # which today is all household-wide (Maintenance/Missions-stale
    # signals aren't profile-scoped in the data model at all).
    system_signals: list[str] = field(default_factory=list)
    overdue_maintenance_count: int = 0
    active_project_count: int = 0


def _find_profile(context, profile_id: str):
    if context.profiles is None:
        return None
    return next((p for p in context.profiles.list_profiles() if p.profile_id == profile_id), None)


def _missions_count_for_profile(context, profile_id: str) -> int:
    """A Mission counts toward this profile if it's unattributed
    (profile_id is None — shared/counts for everyone, the same
    convention core.gamification.grant_xp() and
    core.mission_manager.MissionManager._credit_mission_rewards()
    already establish), explicitly assigned to this profile, or this
    profile is one of its real group-quest participants."""
    return sum(
        1 for mission in context.missions.all_missions()
        if mission.status == "active"
        and (
            mission.profile_id is None
            or mission.profile_id == profile_id
            or profile_id in mission.participant_profile_ids
        )
    )


def assemble_life_state(context, profile_id: str, today: date) -> LifeStateSnapshot:
    """Real, deterministic synthesis — every section gracefully
    degrades to empty/zero if its manager isn't wired (GUI-only
    services, see module docstring), never raises."""
    snapshot = LifeStateSnapshot(profile_id=profile_id)

    if context.missions is not None:
        snapshot.active_mission_count = _missions_count_for_profile(context, profile_id)

    if context.recurring_missions is not None:
        for template in context.recurring_missions.all_templates():
            streak = context.recurring_missions.current_streak_for_template(template.template_id, today)
            if streak > 0:
                snapshot.recurring_streaks.append((template.name, streak))

    if context.skills is not None:
        snapshot.skills_growing = momentum_categories(context.skills, profile_id, today)
        snapshot.skills_declining = declining_categories(context.skills, profile_id, today)
        profile = _find_profile(context, profile_id)
        if profile is not None:
            snapshot.skills_dormant = untouched_interests(context.skills, profile)

    if context.insights is not None:
        for insight in context.insights.open_insights():
            if insight.source_type == "patterns" and insight.source_id != profile_id:
                continue  # a different profile's own pattern signal, not this one's
            snapshot.system_signals.append(insight.message)

    if context.maintenance is not None:
        snapshot.overdue_maintenance_count = sum(
            1 for task in context.maintenance.all_tasks() if is_overdue(task, today)
        )

    if context.projects is not None:
        snapshot.active_project_count = sum(
            1 for project in context.projects.all_projects() if project.status != "Complete"
        )

    return snapshot


def format_life_state_summary(snapshot: LifeStateSnapshot) -> str:
    """Pure formatting logic — testable without Qt. Turns the snapshot
    into a short plain-English status report. Always returns real
    text, even when everything is quiet (a pull-query response, unlike
    a notification message, must never come back empty)."""
    lines: list[str] = []

    if snapshot.active_mission_count:
        lines.append(f"{snapshot.active_mission_count} active mission(s).")

    if snapshot.recurring_streaks:
        streak_text = ", ".join(f"{name} ({streak})" for name, streak in snapshot.recurring_streaks)
        lines.append(f"Live streaks: {streak_text}.")

    if snapshot.skills_growing:
        lines.append(f"Skills gaining real momentum: {', '.join(snapshot.skills_growing)}.")

    if snapshot.skills_declining:
        lines.append(f"Skills that have gone quiet: {', '.join(snapshot.skills_declining)}.")

    if snapshot.skills_dormant:
        lines.append(f"Stated interests with nothing started yet: {', '.join(snapshot.skills_dormant)}.")

    if snapshot.overdue_maintenance_count:
        lines.append(f"{snapshot.overdue_maintenance_count} maintenance item(s) overdue.")

    if snapshot.active_project_count:
        lines.append(f"{snapshot.active_project_count} active project(s).")

    if snapshot.system_signals:
        lines.append("MIA has also noticed: " + " ".join(snapshot.system_signals))

    if not lines:
        return "Nothing notable right now — no active missions, no maintenance overdue, and no skill trends to report."

    return " ".join(lines)
