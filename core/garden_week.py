"""
core.garden_week
==================

This week in the garden (Jarvis brainstorm, round 2; Zac, 2026-11-23: "homestead skills ... aware"): what his confirmed
garden plans say is due in the next seven days (start indoors, transplant or sow, ready to harvest), said once a week
through the communication gate, so a seed-starting date never slips by. The dates are core/homestead_year.py's, from
his own frost dates (core/garden_plans.schedule); nothing is guessed.

Crops starting in the next month with no seeds logged are added (core/seed_check.py).

`this_week(context, today)` is the list; `offer(context, now)` the daily check's message (AMBIENT, once per ISO week,
only when something falls in it); `say(context)` answers "what's due in the garden this week?".
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DAYS = 7


def this_week(context, today: Optional[date] = None) -> list[tuple[date, str]]:
    """The garden's steps from today through the next DAYS - 1 days, soonest first: (day, what)."""
    from core.homestead_year import garden_items

    today = today or date.today()
    plans = getattr(context, "project_plans", None)
    if plans is None:
        return []
    try:
        return garden_items(plans.listed(), today, today + timedelta(days=DAYS - 1))
    except Exception:  # noqa: BLE001 - a plan that can't be read never breaks the check
        log.exception("Garden week: the plans couldn't be read")
        return []


def words(items: list[tuple[date, str]], today: date) -> str:
    """Pure logic. The week's steps in a sentence, each with its day ("today", "Thursday")."""
    def when(day: date) -> str:
        return "today" if day == today else "tomorrow" if day == today + timedelta(days=1) else f"{day:%A}"

    return "; ".join(f"{what} ({when(day)})" for day, what in items[:8]) + \
        (f"; and {len(items) - 8} more" if len(items) > 8 else "")


def offer(context, now: datetime) -> list:
    """The daily check's message: once a week (its fingerprint names the ISO week), when anything falls in it or a
    crop starting in the next month has no seeds logged (core/seed_check.py)."""
    from core.communication_gate import AMBIENT, Candidate

    today = now.date()
    items = this_week(context, today)
    seeds = _seeds(context, today)
    if not items and not seeds:
        return []
    year, week, _ = today.isocalendar()
    said = " ".join(x for x in (("This week in the garden: " + words(items, today) + ".") if items else "", seeds) if x)
    return [Candidate(topic="garden_week", title="This week in the garden", message=said, urgency=AMBIENT,
                      source="system", fingerprint=f"garden-week-{year}-W{week:02d}")]


def _seeds(context, today: date) -> str:
    """The crops starting in the next month with no seeds logged (core/seed_check.py), "" when none or unreadable."""
    from core import seed_check

    try:
        return seed_check.words(seed_check.check(context, today))
    except Exception:  # noqa: BLE001 - the week's message goes without it
        log.exception("Garden week: the seed check failed")
        return ""


def say(context, today: Optional[date] = None) -> str:
    """For "what's due in the garden this week?", with any crop starting soon that has no seeds logged. With nothing
    due it says whether that's because no garden plan is confirmed yet or because the confirmed ones have nothing
    this week, so a model never reads "your plans are confirmed" into an empty planner."""
    today = today or date.today()
    items = this_week(context, today)
    seeds = _seeds(context, today)
    if items:
        return " ".join(x for x in ("This week in the garden: " + words(items, today) + ".", seeds) if x)
    book = getattr(context, "project_plans", None)
    confirmed = [p for p in (book.listed() if book is not None else []) if p.kind == "garden" and p.status == "confirmed"]
    if confirmed:
        said = (f"Your {len(confirmed)} confirmed garden plan{'s have' if len(confirmed) != 1 else ' has'} nothing due "
                "this week.")
    else:
        said = ("No garden plan is confirmed yet, so there are no garden dates to go by. Plan one in the Planner with "
                "your frost dates and its steps show up here.")
    return " ".join(x for x in (said, seeds) if x)
