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
- `afford`: a purchase once against this month's logged income, spending and what's still due (never a bank
  balance: none is linked).

`period(words, today)` reads "today", "yesterday", "this week", "last week", "this month", "last month", "this year",
"last year" and a month by name ("in October": the latest one not after today; "in March 2025" that year, said in
the label); (start, end, label) or None. `only_period` keeps the routes to asks whose rest is only a period.
Read only.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Optional

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}


def period(words: str, today: date) -> Optional[tuple[date, date, str]]:
    """Pure logic. (start, end, label) for the period his words name, or None; a month with its year when he says
    one, and the year in the label when it isn't this one."""
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
    named = re.search(r"\b(?:in|for|during) (" + "|".join(MONTHS) + r")(?:,? (\d{4}))?\b", said)
    if named:
        month = MONTHS[named.group(1)]
        year = int(named.group(2)) if named.group(2) else (today.year if month <= today.month else today.year - 1)
        last = calendar.monthrange(year, month)[1]
        label = calendar.month_name[month] + (f" {year}" if year != today.year else "")
        return date(year, month, 1), min(date(year, month, last), today), label
    return None


_PERIOD_WORDS = re.compile(r"\b(?:so far )?(?:today|yesterday|this week|last week|this month|last month|this year|"
                           r"last year|ytd|so far this year)\b|\b(?:in|for|during) (?:" + "|".join(MONTHS) +
                           r")(?:,? \d{4})?\b", re.I)
_FILLER = re.compile(r"\b(?:in total|in all|total|overall|altogether|so far|all|money|of my money|of our money|then|"
                     r"exactly|roughly|about|again|please|mia)\b|[,.!?]", re.I)


def only_period(rest: str) -> bool:
    """Pure logic. Whether what follows the question is a period and filler only ("last month", "so far this year"),
    never a place, a thing or a comparison ("at Costco last month", "this month vs last month": the Fable review)."""
    if re.search(r"\b(?:vs\.?|versus|compared|than|and)\b", rest or "", re.I):
        return False
    left = _FILLER.sub(" ", _PERIOD_WORDS.sub(" ", rest or ""))
    return not left.strip()


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


def afford(context, amount: float, today: Optional[date] = None) -> str:
    """For "can I afford a $500 purchase this month?" (the live sweep, 2026-11-26: "you can afford it ... you have the
    full $0.00 available"): this month's logged income less its spending and the bills still due by its end, against
    the amount, a bill not marked paid counted once (never every missed month); with no income logged, that it can't
    be told (no bank balance is linked), and what's still due. A purchase once; a monthly cost is the afford plan's
    (the freedom date)."""
    from core import money_ahead

    today = today or date.today()
    budget = getattr(context, "budget", None)
    if budget is None:
        return "Your budget isn't on this MIA."
    first = today.replace(day=1).isoformat()
    income = budget.total_income(first, today.isoformat())
    spent = sum(budget.total_expenses_by_category(first, today.isoformat(), entity_id="").values())
    end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    bills, incomes, debts = money_ahead._records(context)
    bills = [b for b in bills if not getattr(b, "entity_id", "")]
    moves = money_ahead.flows(bills, [], [d for d in debts if not getattr(d, "entity_id", "")], today, 6)
    due = [m for m in moves if m["amount"] < 0 and m["day"] <= end and m["note"] != "overdue"]
    late_amounts = {}
    for m in moves:
        if m["note"] == "overdue":
            late_amounts.setdefault(m["what"], -m["amount"])  # each counted once, never every missed month
    late = list(late_amounts)
    owed = sum(-m["amount"] for m in due) + sum(late_amounts.values())
    names = ", ".join(dict.fromkeys(m["what"] for m in due))
    nth = "st" if end.day == 31 else "th"  # a month ends on the 28th, 29th, 30th or 31st
    still = f" Still due by the {end.day}{nth}: {_money(owed)} ({names})." if due else ""
    if late:
        still += " Not marked paid yet: " + ", ".join(late) + " (each counted once)."
    if not income:
        return (f"I can't tell from your records: no income is logged this month, and no bank balance is linked, so I "
                f"don't know what you have.{still} Log your pay as it comes in (\"I got paid $1,200\") and I'll work it "
                f"out.")
    left = income - spent - owed
    verdict = (f"From what's logged, {_money(amount)} fits: {_money(left)} is left after what's due." if left >= amount
               else f"From what's logged, it doesn't fit: {_money(max(left, 0))} is left after what's due, "
                    f"{_money(amount - max(left, 0))} short.")
    return (f"{verdict} This month: {_money(income)} in, {_money(spent)} spent.{still} That's from your records, not "
            f"a bank balance.")
