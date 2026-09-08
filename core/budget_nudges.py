"""
core.budget_nudges
=====================

Pure decision logic for a proactive daily budget nudge — 2026-09-08,
at the user's explicit request following up on the "Field Manual"
brainstorm: "are we meeting our income needs or exceeding our planned
expenses, are we paying things on time, and covering what's due next
and when next expected pay day and amount is."

Same split as `core/daily_occasions.py` (its own three checks —
birthday/calendar-digest/check-in — established this exact "pure
functions, no Qt, no manager instances, wired into
core/application.py's existing daily-check timer" shape first): the
actual decision logic lives here, unit-testable without a real clock
or a running app, so `core/application.py` stays a thin wiring layer.

One consolidated message per day, not four separate notifications —
`build_nudge_message()` joins whichever of the four checks below have
something real to say, and returns None (no notification at all) when
everything's quiet, same "don't notify just to say nothing's wrong"
restraint `core/daily_occasions.py`'s own calendar digest already
takes for an empty day.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.budget_manager import Bill, BudgetTarget, IncomeSource, days_until_bill_due, days_until_income_due

_UPCOMING_WITHIN_DAYS = 7


def overdue_bills_summary(bills: list[Bill], today: date) -> Optional[str]:
    """Pure logic — testable without Qt."""
    overdue = [b for b in bills if (remaining := days_until_bill_due(b, today)) is not None and remaining < 0]
    if not overdue:
        return None
    if len(overdue) == 1:
        return f"'{overdue[0].name}' is overdue."
    names = ", ".join(b.name for b in overdue)
    return f"{len(overdue)} bills are overdue: {names}."


def upcoming_bills_summary(bills: list[Bill], today: date, within_days: int = _UPCOMING_WITHIN_DAYS) -> Optional[str]:
    """Pure logic — testable without Qt. Excludes anything already
    overdue (that's overdue_bills_summary()'s job) — 0 <= remaining
    <= within_days only."""
    upcoming = [
        b for b in bills
        if (remaining := days_until_bill_due(b, today)) is not None and 0 <= remaining <= within_days
    ]
    if not upcoming:
        return None
    parts = [f"{b.name} (${b.amount:.2f})" for b in sorted(upcoming, key=lambda b: days_until_bill_due(b, today))]
    return f"Due within {within_days} days: {', '.join(parts)}."


def upcoming_income_summary(sources: list[IncomeSource], today: date, within_days: int = _UPCOMING_WITHIN_DAYS) -> Optional[str]:
    """Pure logic — testable without Qt. Names the single soonest
    expected income if there's one due within range — "when's the next
    paycheck and how much" is a specific-answer question, not a count."""
    upcoming = [
        s for s in sources
        if (remaining := days_until_income_due(s, today)) is not None and 0 <= remaining <= within_days
    ]
    if not upcoming:
        return None
    soonest = min(upcoming, key=lambda s: days_until_income_due(s, today))
    remaining = days_until_income_due(soonest, today)
    when = "today" if remaining == 0 else f"in {remaining} days"
    return f"Next expected income: {soonest.name}, ${soonest.expected_amount:.2f} {when}."


def budget_overage_summary(targets: list[BudgetTarget], actual_by_category: dict[str, float]) -> Optional[str]:
    """Pure logic — testable without Qt. Only reports categories that
    actually exceed their planned amount — a category under or at
    target says nothing (this is a warning nudge, not a full report;
    see the Budget module's own Summary tab for the full comparison)."""
    over = []
    for target in targets:
        actual = actual_by_category.get(target.category, 0.0)
        if actual > target.monthly_amount:
            over.append((target.category, actual, target.monthly_amount))
    if not over:
        return None
    parts = [f"{category} (${actual:.2f} of ${planned:.2f} planned)" for category, actual, planned in over]
    return f"Over budget this month: {', '.join(parts)}."


def build_nudge_message(
    bills: list[Bill],
    income_sources: list[IncomeSource],
    targets: list[BudgetTarget],
    actual_expenses_by_category: dict[str, float],
    today: date,
) -> Optional[str]:
    """Pure logic — testable without Qt. Joins whichever checks have
    something to say into one multi-line message; None when every
    check is quiet, so a fully-caught-up day fires no notification at
    all rather than an empty or falsely-reassuring one."""
    lines = [
        line for line in (
            overdue_bills_summary(bills, today),
            upcoming_bills_summary(bills, today),
            upcoming_income_summary(income_sources, today),
            budget_overage_summary(targets, actual_expenses_by_category),
        )
        if line is not None
    ]
    if not lines:
        return None
    return "\n".join(lines)
