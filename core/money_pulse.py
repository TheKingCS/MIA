"""
core.money_pulse
==================

A money pulse (brainstorm round 16, 2026-11-25): once a week, his money in a line or two, never a report: the one
spending category drifting furthest over its usual pace this month (core/spending_pace), what's due in the next seven
days from his bills and debts, and the tightest week of the next four, where more goes out than comes in
(core/money_ahead). Everything is worked out in code from his own budget; the model never sees a number to phrase.

How: `line(context, today)` gives the words (or "" with nothing in his budget to say from); `offer(context, now)` is
the daily check `money_pulse`, said on Sundays only, once a week (its fingerprint names the ISO week), through the
gate as AMBIENT. "How's my money this week?" and "money pulse" reach `say` in code (core/assistant_turn's
`_own_tool_reply`). His household's money only (a business's is its own); read only.

The Fable review (2026-11-25): a category paid in one lump (rent, insurance, a bill's category, debt payments) is
compared whole month to whole month, never paced (rent on the 1st read as thousands over); "ahead" starts tomorrow
(the pulse is said on a Sunday, the last day of its week); an overdue bill is said once by name, never every missed
month summed as due; with no income logged no week is called tight.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

DRIFT = 1.1  # a category on pace for this much of its usual month is drifting
DRIFT_MARGIN = 25.0  # and at least this much over, in money, so a few dollars isn't news
AHEAD_WEEKS = 4
PULSE_WEEKDAY = 6  # Sunday
LUMP_CATEGORIES = ("Mortgage/Rent", "Insurance", "Debt Payment", "Taxes")  # paid in one go, never paced


def drift(context, today: date) -> Optional[dict]:
    """{category, so_far, going, usual} for the category furthest over its usual pace this month, or None (too early
    in the month, under two months of history, or nothing over)."""
    from core import spending_pace

    budget = getattr(context, "budget", None)
    if budget is None or today.day <= spending_pace.EARLY_DAYS:
        return None
    usual, so_far = spending_pace._usual(budget, today)
    lumps = set(LUMP_CATEGORIES) | {b.category for b in _household(budget.all_bills())}
    best = None
    for category, normal in usual.items():
        spent = so_far.get(category, 0.0)
        going = spent if category in lumps else spending_pace.pace(spent, today)
        over = going - normal
        if going > normal * DRIFT and over >= DRIFT_MARGIN and (best is None or over > best["going"] - best["usual"]):
            best = {"category": category, "so_far": so_far.get(category, 0.0), "going": going, "usual": normal}
    return best


def _household(records: list) -> list:
    """Only the household's own records (entity_id ""); a business's bills and debts are its own."""
    return [r for r in records if not getattr(r, "entity_id", "")]


def ahead(context, today: date) -> tuple[list, list, Optional[dict]]:
    """(what goes out in the next seven days, not overdue [{day, amount, what, note}]; the overdue ones' names, each
    once; the tightest of the AHEAD_WEEKS weeks starting tomorrow {start, in, out, net}, or None when every week comes
    out even or ahead, or when no income is logged to weigh them against)."""
    from core import money_ahead

    bills, incomes, debts = (_household(r) for r in money_ahead._records(context))
    moves = money_ahead.flows(bills, incomes, debts, today, weeks=AHEAD_WEEKS + 1)
    week_end = today + timedelta(days=7)
    due = [m for m in moves if m["amount"] < 0 and m["day"] < week_end and m["note"] != "overdue"]
    overdue = list(dict.fromkeys(m["what"] for m in moves if m["note"] == "overdue"))
    tight = None
    if incomes:
        later = [m for m in moves if m["note"] not in ("overdue", "late")]
        worst = money_ahead.tight(money_ahead.weeks(later, today + timedelta(days=1), AHEAD_WEEKS))
        tight = worst[0] if worst else None
    return due, overdue, tight


def line(context, today: Optional[date] = None) -> str:
    """The pulse's words: the drifting category, what's due this week, the tightest week ahead; "" when none of the
    three has anything to say from."""
    from core.region import money

    today = today or date.today()
    parts = []
    try:
        found = drift(context, today)
        if found:
            parts.append(f"{found['category']} is running about {money(found['going'] - found['usual'])} over "
                         f"your usual this month.")
    except Exception:  # noqa: BLE001 - one part that can't be read never takes the rest
        log.exception("Money pulse: the spending couldn't be read")
    try:
        due, overdue, tight = ahead(context, today)
        if due:
            names = list(dict.fromkeys(m["what"] for m in due))
            said = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
            parts.append(f"Due this week: {money(sum(-m['amount'] for m in due))} ({said}).")
        if overdue:
            parts.append("Not marked paid yet: " + ", ".join(overdue[:3])
                         + (f" and {len(overdue) - 3} more" if len(overdue) > 3 else "") + ".")
        if tight:
            parts.append(f"Tightest week ahead: the week of {tight['start']:%b} {tight['start'].day}, "
                         f"{money(-tight['net'])} more going out than coming in.")
    except Exception:  # noqa: BLE001
        log.exception("Money pulse: the weeks ahead couldn't be worked out")
    return " ".join(parts)


def say(context, today: Optional[date] = None) -> str:
    """For "how's my money this week?": the pulse, or how to give her something to say it from."""
    said = line(context, today)
    if said:
        return said
    budget = getattr(context, "budget", None)
    if budget is None:
        return "Your budget isn't on this MIA."
    try:
        has_any = bool(budget.all_bills() or budget.all_income_sources())
    except Exception:  # noqa: BLE001
        has_any = False
    if has_any:
        return "Nothing drifting over your usual and nothing due this week."
    return ("Nothing to take a pulse from yet: add your bills and income in Budget and log spending as it happens, "
            "and I'll say each week what's drifting and what's due.")


def offer(context, now: datetime) -> list:
    """The daily check's message: on Sundays, once a week (the fingerprint names the ISO week), when there's anything
    to say; AMBIENT through the gate."""
    from core.communication_gate import AMBIENT, Candidate

    today = now.date()
    if today.weekday() != PULSE_WEEKDAY:
        return []
    said = line(context, today)
    if not said:
        return []
    year, week, _ = today.isocalendar()
    return [Candidate(topic="money_pulse", title="Your money this week", message=said, urgency=AMBIENT,
                      source="system", fingerprint=f"money-pulse-{year}-W{week:02d}")]
