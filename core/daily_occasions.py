"""
core.daily_occasions
=======================

Pure decision logic for `core/application.py`'s daily-occasion-check
timer — 2026-07-14 aesthetic pass part 5, at the user's explicit
request: "know and celebrate the user's birthday, remind them of
anniversaries, check in with them and see how they are doing." Split
out as pure functions (no Qt, no manager instances) so the actual
decision logic is unit-testable without a real clock or a running app,
same reasoning as core/power_manager.py's `should_warn_low_battery()`.

Three independent daily checks, each with its own "already ran today"
date tracker in config (`system.last_birthday_celebrated_date`/
`system.last_calendar_digest_date`/`system.last_checkin_date`) rather
than one combined gate, since they don't all fire on the same
condition — a birthday should be celebrated as soon as possible after
midnight, while the check-in deliberately waits until evening (see
`should_send_checkin()`) so opening the app at 6am doesn't immediately
scold the user for not having chatted yet.

**"Anniversaries" reuses the existing Calendar module rather than being
a new concept.** Calendar gained real recurrence support (2026-09-08,
core.calendar_manager's `occurs_on()`) — a user-created "Our
Anniversary" event now surfaces via this digest every matching
anniversary, not just the exact date it was originally entered,
closing the gap docs/KNOWN_ISSUES.md used to document here.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from core.calendar_manager import occurs_on


def is_birthday_today(birthday_iso: Optional[str], today: date) -> bool:
    """Pure logic — testable without Qt. Compares month/day only; the year is irrelevant to "is it today."""
    if not birthday_iso:
        return False
    try:
        parsed = date.fromisoformat(birthday_iso)
    except ValueError:
        return False
    return (parsed.month, parsed.day) == (today.month, today.day)


def calendar_events_today(events: list, today_iso: str) -> list:
    """Pure logic — testable without Qt. `events` are anything with
    `.date`/`.recurrence` attributes (core.calendar_manager.CalendarEvent)
    — a recurring event surfaces here on every matching anniversary via
    occurs_on(), not just the exact date it was originally entered."""
    today = date.fromisoformat(today_iso)
    return [event for event in events if occurs_on(event, today)]


def should_run_once_daily(last_run_date: Optional[str], today_iso: str) -> bool:
    """Pure logic — True the first time this is called on a new day (or ever, if last_run_date is None)."""
    return last_run_date != today_iso


# Deliberately not "any time of day" — found via just thinking through
# the obvious bad case before ever building this: firing a "haven't
# heard from you" notification first thing in the morning, before the
# user has had any real chance to open the app yet, would read as
# presumptuous/nagging rather than caring. Waiting until evening gives
# a full day's worth of opportunity for real activity first.
_CHECKIN_HOUR = 18


def should_send_checkin(now: datetime, has_conversation_activity_today: bool) -> bool:
    """Pure logic — testable without Qt or a real clock."""
    return now.hour >= _CHECKIN_HOUR and not has_conversation_activity_today
