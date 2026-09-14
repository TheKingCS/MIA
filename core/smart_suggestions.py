"""
core.smart_suggestions
=========================

Pure decision logic for a proactive "Smart Suggestions" daily check —
docs/VISION.md's principle 3 ("Proactive, not just reactive") names
three concrete examples: "recovery after intense workouts, a grocery
trip when supplies run low, a birthday gift reminder before the date."

All three are built here now. Recovery/pantry shipped first, reading
real data from core.workout_manager.WorkoutManager/
core.kitchen_manager.KitchenManager. The gift reminder was deliberately
deferred at first — it needed "Relationship Profiles" (people MIA
knows, with their own birthdays), which didn't exist yet; now that
core.relationships_manager.RelationshipsManager does, it has real data
behind it too.

**Fourth check added 2026-09-14**: `build_walkthrough_suggestion()`,
the modular-tutorial-system half docs/VISION.md flagged as still
needing "a real per-feature usage-tracking subsystem that doesn't
exist yet" — now core.usage_tracker.UsageTracker. Deliberately takes
just ONE display_name (or None), not a list — core.application's daily
check already narrows a whole list of never-opened modules down to a
single candidate before calling this (see UsageTracker's own docstring
for why: never repeat the same nudge, never fire more than once a
day), so this function's only job is turning "the chosen module" into
the actual notification sentence.

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
day after a real session, not every day after), the pantry check only
ever names real expiring/expired items (never a guessed low-stock
heuristic — PantryItem has no reorder-threshold concept), and the gift
reminder fires exactly once, exactly 7 days before the birthday (real
lead time to actually get a gift, not a same-day notice).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.kitchen_manager import PantryItem, days_until_expiration
from core.relationships_manager import Person, days_until_birthday

_EXPIRING_WITHIN_DAYS = 3
_GIFT_REMINDER_LEAD_DAYS = 7


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


def build_gift_reminder_suggestion(people: list[Person], today: date) -> Optional[str]:
    """Pure logic — testable without Qt. Names anyone whose birthday is
    exactly _GIFT_REMINDER_LEAD_DAYS away — real lead time to actually
    get a gift, not a same-day notice — including their stored gift
    ideas when present. Fires once per person per year (the date math
    only matches on the one exact day), never a repeating nag."""
    parts = []
    for person in people:
        days = days_until_birthday(person.birthday, today)
        if days != _GIFT_REMINDER_LEAD_DAYS:
            continue
        gift_part = f" Gift ideas: {person.gift_ideas}." if person.gift_ideas else ""
        parts.append(f"{person.name}'s birthday is in {_GIFT_REMINDER_LEAD_DAYS} days.{gift_part}")
    if not parts:
        return None
    return " ".join(parts)


def build_walkthrough_suggestion(never_used_display_name: Optional[str]) -> Optional[str]:
    """Pure logic — testable without Qt. `never_used_display_name` is
    the ONE module the caller has already chosen to suggest this time
    (or None if there's nothing left to suggest) — see this module's
    docstring for why the narrowing happens before this function, not
    inside it."""
    if not never_used_display_name:
        return None
    return (
        f"You haven't tried the {never_used_display_name} module yet — "
        f'say "teach me how {never_used_display_name.lower()} works" any time you want a walkthrough.'
    )


def build_smart_suggestions_message(
    last_session_date: Optional[str], pantry_items: list[PantryItem], people: list[Person], today: date,
) -> Optional[str]:
    """Pure logic — testable without Qt. Joins whichever checks above
    have something real to say; None (no notification) when
    everything's quiet."""
    parts = [
        message for message in (
            build_recovery_suggestion(last_session_date, today),
            build_pantry_suggestion(pantry_items, today),
            build_gift_reminder_suggestion(people, today),
        )
        if message is not None
    ]
    if not parts:
        return None
    return " ".join(parts)
