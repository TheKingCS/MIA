"""
core.money_periods
====================

Money over a period, in code (the live sweep, 2026-11-26: "how much did I spend last month?" got "I don't have that
information", "my biggest expense category this year" a guess, "what did I make from the shop this month?" the fact
sheet's words). From his own records:

- `spent`: his household's spending in the period (entity "", core/budget_manager), with its three biggest
  categories;
- `biggest`: the biggest category in the period (this year when none is said);
- `shop_made`: the workshop ledger's revenue, expenses and profit in the period (core/ledger_manager).

`period(words, today)` reads "today", "yesterday", "this week", "last week", "this month", "last month", "this year",
"last year" and a month by name ("in October": the latest one not after today); (start, end, label) or None.
Read only.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Optional

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}


def period(words: str, today: date) -> Optional[tuple[date, date, str]]:
    """Pure logic. (start, end, label) for the period his words name, or None."""
    said = (words or "").lower()
    if re.search(r"\btoday\b", said):
        return today, today, "today"
    if re.search(r"\byesterday\b", said):
        day = today - timedelta(days=1)
        return day, day, "yesterday"
    monday = today - timedelta(days=today.weekday())
    if re.search(r"\bthis week\b", said):
        return monday, today, "this week"
    if re.search(r"\blast week\b", said):
        return monday - timedelta(days=7), monday - timedelta(days=1), "last week"
    if re.search(r"\bthis month\b", said):
        return today.replace(day=1), today, "this month"
    if re.search(r"\blast month\b", said):
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end, f"last month ({end:%B})"
    if re.search(r"\bthis year\b|\bso far this year\b|\bytd\b", said):
        return today.replace(month=1, day=1), today, "this year"
    if re.search(r"\blast year\b", said):
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31), f"last year ({today.year - 1})"
    named = re.search(r"\b(?:in|for|during) (" + "|".join(MONTHS) + r")\b", said)
    if named:
        month = MONTHS[named.group(1)]
        year = today.year if month <= today.month else today.year - 1
        last = calendar.monthrange(year, month)[1]
        return date(year, month, 1), min(date(year, month, last), today), f"{calendar.month_name[month]}"
    return None


def _money(amount: float) -> str:
    """In his currency."""
    from core.region import money

    return money(amount)


def spent(context, words: str, today: Optional[date] = None) -> Optional[str]:
    """His household's spending in the period with its biggest three categories, or None with no period said."""
    today = today or date.today()
    found = period(words, today)
    budget = getattr(context, "budget", None)
    if found is None:
        return None
    if budget is None:
        return "Your budget isn't on this MIA."
    start, end, label = found
    by = budget.total_expenses_by_category(start.isoformat(), end.isoformat(), entity_id="")
    total = sum(by.values())
    if not total:
        return f"Nothing logged as spent {label}. Tell me as you spend (\"I spent $30 on groceries\") and I'll keep count."
    top = sorted(by.items(), key=lambda kv: -kv[1])[:3]
    return (f"You spent {_money(total)} {label}. The most: " + ", ".join(f"{c} {_money(v)}" for c, v in top) + ".")


def biggest(context, words: str, today: Optional[date] = None) -> str:
    """The biggest household spending category in the period (this year when none is said)."""
    today = today or date.today()
    start, end, label = period(words, today) or (today.replace(month=1, day=1), today, "this year")
    budget = getattr(context, "budget", None)
    if budget is None:
        return "Your budget isn't on this MIA."
    by = budget.total_expenses_by_category(start.isoformat(), end.isoformat(), entity_id="")
    if not by or not sum(by.values()):
        return f"Nothing logged as spent {label} yet, so there's no biggest category to say."
    ranked = sorted(by.items(), key=lambda kv: -kv[1])
    total = sum(by.values())
    first, amount = ranked[0]
    then = f" Next: {ranked[1][0]} ({_money(ranked[1][1])})." if len(ranked) > 1 else ""
    return (f"Your biggest category {label} is {first}: {_money(amount)}, {round(100 * amount / total)}% of the "
            f"{_money(total)} you spent.{then}")


def shop_made(context, words: str, today: Optional[date] = None) -> str:
    """The workshop's revenue, expenses and profit in the period (this month when none is said)."""
    today = today or date.today()
    start, end, label = period(words, today) or (today.replace(day=1), today, "this month")
    ledger = getattr(context, "ledger", None)
    if ledger is None:
        return "The workshop ledger isn't on this MIA."
    s, e = start.isoformat(), end.isoformat()
    revenue, expenses = ledger.total_revenue(s, e), ledger.total_expenses(s, e)
    if not revenue and not expenses:
        return f"No sales or shop costs logged {label}. Tell me when you sell (\"I sold 2 cutting boards for $80\")."
    net = revenue - expenses
    return (f"The shop {label}: {_money(revenue)} in sales, {_money(expenses)} in costs, "
            + (f"{_money(net)} profit." if net >= 0 else f"{_money(-net)} behind."))
