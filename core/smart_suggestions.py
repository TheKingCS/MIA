"""
core.smart_suggestions
=========================

Pure decision logic for a proactive "Smart Suggestions" daily check —
docs/VISION.md's principle 3 ("Proactive, not just reactive") names
three concrete examples: "recovery after intense workouts, a grocery
trip when supplies run low, a birthday gift reminder before the date."

Only the first two are built here — both have real, already-tracked
data behind them (core.workout_manager.WorkoutManager/
core.kitchen_manager.KitchenManager). A birthday-gift reminder needs
"Relationship Profiles" (people MIA knows, with their own birthdays) —
a real, separate, still-unbuilt subsystem with no data source today;
faking one against data that doesn't exist would be worse than not
building it yet.

Same split as core.daily_occasions/core.budget_nudges (both established
this exact "pure functions, no Qt, no manager instances, wired into
core.application's existing daily-check timer" shape first): the
actual decision logic lives here, unit-testable without a real clock
or a running app. build_smart_suggestions_message() joins whichever
checks below have something real to say and returns None (no
notification at all) when everything's quiet — the same "don't notify
just to say nothing's wrong" restraint build_nudge_message() already
takes, and the concrete mechanism behind VISION's own "calibrated to
feel helpful, never naggy" standard: recovery fires exactly once (the
day after a real session, not every day after), and the pantry check
only ever names real expiring/expired items, never a guessed low-stock
heuristic (PantryItem has no reorder-threshold concept).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.kitchen_manager import PantryItem, days_until_expiration

_EXPIRING_WITHIN_DAYS = 3


def build_recovery_suggestion(last_session_date: Optional[str], today: date) -> Optional[str]:
    """Pure logic — testable without Qt. Fires exactly once, the day
    after a real logged workout session — not for "intensity," which
    this app has no real way to measure (no heart-rate/soreness data),
    and not every day after (that would be naggy, not helpful)."""
    if not last_session_date:
        return None
    try:
        session_date = date.fromisoformat(last_session_date)
    except ValueError:
        return None
    if session_date != today - timedelta(days=1):
        return None
    return "You worked out yesterday — prioritize recovery today (sleep, hydration, protein)."


def build_pantry_suggestion(pantry_items: list[PantryItem], today: date) -> Optional[str]:
    """Pure logic — testable without Qt. Names real items expiring
    within _EXPIRING_WITHIN_DAYS or already expired — a real, honest
    "grocery trip when supplies run low" signal grounded in tracked
    data, not a guessed low-stock heuristic."""
    expiring_names = []
    for item in pantry_items:
        remaining = days_until_expiration(item, today)
        if remaining is not None and remaining <= _EXPIRING_WITHIN_DAYS:
            expiring_names.append(item.name)
    if not expiring_names:
        return None
    names = ", ".join(expiring_names)
    return f"Pantry items expiring soon: {names} — might be time for a grocery trip."


def build_smart_suggestions_message(
    last_session_date: Optional[str], pantry_items: list[PantryItem], today: date,
) -> Optional[str]:
    """Pure logic — testable without Qt. Joins whichever checks above
    have something real to say; None (no notification) when
    everything's quiet."""
    parts = [
        message for message in (
            build_recovery_suggestion(last_session_date, today),
            build_pantry_suggestion(pantry_items, today),
        )
        if message is not None
    ]
    if not parts:
        return None
    return " ".join(parts)
