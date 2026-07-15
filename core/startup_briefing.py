"""
core.startup_briefing
========================

Pure logic for the "Good evening, Zac. Welcome back." launch greeting —
docs/VISION.md's 2026-07-15 companion-philosophy update, "Startup
Dashboard Briefing." Picked as the first concrete slice from that
update: it's aggregation/summarization over data that already exists
(the same five sections `modules/dashboard/module.py` already lists —
missions, calendar, notifications, projects, memories — reused here as
a short spoken-style greeting instead of a bare list), so it carries no
new data-model risk.

**Deliberately template-based, not an LLM call.** This runs once at
every app launch; boot-time latency (or Ollama simply not being warmed
up yet) is a worse trade-off here than a scripted-but-warm sentence —
same "start boring, not clever" principle `docs/VISION.md` already
applies to Continuous Learning. Revisit with real live-model iteration
(this project's own established discipline, see `docs/ROADMAP.md`'s
gotchas) if a template ever stops feeling "intelligent enough" — don't
assume a template can't be improved further before that happens.

**Weather, workout recommendations, financial updates, and smart home
status are named in the original ask but have no real module/data
source yet** (all listed as new, not-yet-built subsystems in
`docs/VISION.md`'s companion-philosophy update) — omitted here, same
"don't build fake data" discipline as `gui/home_dashboard.py`'s missing
"currently playing song".

Pure functions only, no Qt/manager coupling — testable without a real
app (see `tests/test_startup_briefing.py`), same shape as
`core/daily_occasions.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def greeting_for_hour(hour: int) -> str:
    """Pure logic — testable without a real clock."""
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def _join_with_and(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def build_stat_highlights(
    active_mission_count: int,
    events_today_count: int,
    unread_notification_count: int,
    active_project_count: int,
) -> list[str]:
    """Each nonzero count becomes one short highlight phrase — a zero
    count is skipped entirely rather than padding the briefing with
    "you have 0 X", same reasoning as
    `gui/home_dashboard.py`'s per-card "not available" fallbacks."""
    highlights: list[str] = []
    if active_mission_count:
        noun = "mission" if active_mission_count == 1 else "missions"
        highlights.append(f"{active_mission_count} active {noun}")
    if events_today_count:
        noun = "event" if events_today_count == 1 else "events"
        highlights.append(f"{events_today_count} calendar {noun} today")
    if unread_notification_count:
        noun = "notification" if unread_notification_count == 1 else "notifications"
        highlights.append(f"{unread_notification_count} unread {noun}")
    if active_project_count:
        noun = "project" if active_project_count == 1 else "projects"
        highlights.append(f"{active_project_count} {noun} in progress")
    return highlights


def build_startup_briefing(
    profile_name: str,
    now: datetime,
    stat_highlights: list[str],
    latest_memory_line: Optional[str] = None,
) -> str:
    """Pure logic — testable without Qt or a real clock. `stat_highlights`
    comes from `build_stat_highlights()`; `latest_memory_line` is a
    already-formatted description of the most recent Memory (or None)."""
    sentences = [f"{greeting_for_hour(now.hour)}, {profile_name}. Welcome back."]
    if stat_highlights:
        sentences.append(f"You have {_join_with_and(stat_highlights)}.")
    if latest_memory_line:
        sentences.append(f"Your most recent memory: {latest_memory_line}.")
    if len(sentences) == 1:
        sentences.append("Nothing new to report today — a clean slate.")
    return " ".join(sentences)
