"""
core.startup_briefing
========================

Pure logic for the "Good evening, Zac. Welcome back." launch greeting —
docs/VISION.md's 2026-07-15 companion-philosophy update, "Startup
Dashboard Briefing."

**Deliberately template-based, not an LLM call.** This runs once at
every app launch; boot-time latency (or Ollama simply not being warmed
up yet) is a worse trade-off here than a scripted-but-warm sentence —
same "start boring, not clever" principle `docs/VISION.md` already
applies to Continuous Learning. Revisit with real live-model iteration
(this project's own established discipline, see `docs/ROADMAP.md`'s
gotchas) if a template ever stops feeling "intelligent enough" — don't
assume a template can't be improved further before that happens.

**2026-07-15: `build_stat_highlights()` no longer covers missions/
projects.** Found via direct user feedback that the briefing felt like
"reading a script" rather than a real dashboard summary — root cause
was that this file hardcoded a fixed set of data sources completely
disconnected from `core/dashboard_widgets.py`'s actual enabled-widget
list, so adding/removing/reordering widgets never changed what the
briefing talked about. Mission/project highlights now come from
`gui/home_dashboard.py`'s own per-widget highlight providers instead —
each enabled widget contributes its own highlight (or nothing), so the
briefing is a genuine reflection of the dashboard's live state rather
than a separately-maintained list that silently drifts out of sync as
widgets are added. This function still covers Calendar/Notifications,
since those aren't Home widgets of their own (yet).

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


def build_stat_highlights(events_today_count: int, unread_notification_count: int) -> list[str]:
    """Each nonzero count becomes one short highlight phrase — a zero
    count is skipped entirely rather than padding the briefing with
    "you have 0 X", same reasoning as
    `gui/home_dashboard.py`'s per-card "not available" fallbacks.
    Missions/projects are no longer covered here — see this module's
    docstring for why."""
    highlights: list[str] = []
    if events_today_count:
        noun = "event" if events_today_count == 1 else "events"
        highlights.append(f"{events_today_count} calendar {noun} today")
    if unread_notification_count:
        noun = "notification" if unread_notification_count == 1 else "notifications"
        highlights.append(f"{unread_notification_count} unread {noun}")
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
