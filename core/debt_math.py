"""
core.debt_math
================

Pure logic (DEC-0052, the "debts" question plan): when each debt is paid
off at the current payments, the interest it costs, and what an extra
amount a month changes. MIA never asks the model to do this arithmetic.

The month-by-month rule, the usual one: interest is added each month at
the rate in effect (a promotional rate until its end date); every debt
gets its minimum; the extra, and every paid-off debt's minimum after it
(the "rollover"), goes to the first debt in the payoff order that still
has a balance. A debt whose minimum doesn't cover its interest never
gets paid off by the minimum alone: that's reported, not looped forever.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

MAX_MONTHS = 600  # 50 years: past this, "not at these payments"


@dataclass
class DebtResult:
    name: str
    balance: float
    months: Optional[int]  # None: not paid off at these payments
    paid_off: Optional[str]  # "2027-08" (year-month), or None
    interest: float  # interest paid until then (or over MAX_MONTHS)


@dataclass
class Payoff:
    debts: list  # DebtResult, in payoff order
    months: Optional[int]  # until every debt is paid, or None
    debt_free: Optional[str]
    interest: float
    monthly: float  # minimums + extra: what goes to debts each month


def _add_months(day: date, months: int) -> str:
    total = day.year * 12 + day.month - 1 + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _rate_on(debt, day: date) -> float:
    """The APR in effect in the month starting `day` (percent)."""
    promo, ends = getattr(debt, "promo_apr", None), getattr(debt, "promo_expires_date", None)
    if promo is not None and ends:
        try:
            if day.isoformat() < str(ends)[:10]:
                return float(promo)
        except (TypeError, ValueError):
            pass
    return float(getattr(debt, "interest_rate", 0) or 0)


def simulate(debts: list, extra: float = 0.0, today: Optional[date] = None) -> Payoff:
    """`debts` in payoff order (the first gets the extra). Each needs
    name, balance, interest_rate, minimum_payment (promo_apr and
    promo_expires_date optional)."""
    today = today or date.today()
    start = today.replace(day=1)
    open_ = [d for d in debts if float(d.balance or 0) > 0]
    balances = [float(d.balance) for d in open_]
    interest = [0.0] * len(open_)
    done: list[Optional[int]] = [None] * len(open_)
    monthly = sum(float(d.minimum_payment or 0) for d in open_) + max(0.0, float(extra or 0))
    for month in range(1, MAX_MONTHS + 1):
        if all(b <= 0.005 for b in balances):
            break
        first = start.replace(year=start.year + (start.month - 1 + month - 1) // 12,
                              month=(start.month - 1 + month - 1) % 12 + 1)
        budget = monthly
        for i, d in enumerate(open_):  # interest, then minimums
            if balances[i] <= 0.005:
                continue
            charge = balances[i] * _rate_on(d, first) / 100 / 12
            interest[i] += charge
            balances[i] += charge
            pay = min(balances[i], float(d.minimum_payment or 0), budget)
            balances[i] -= pay
            budget -= pay
        for i in range(len(open_)):  # the extra and the rollover, in order
            if budget <= 0.005:
                break
            if balances[i] > 0.005:
                pay = min(balances[i], budget)
                balances[i] -= pay
                budget -= pay
        for i in range(len(open_)):
            if done[i] is None and balances[i] <= 0.005:
                done[i] = month
    results = [DebtResult(d.name, round(float(d.balance), 2), done[i],
                          _add_months(start, done[i] - 1) if done[i] else None, round(interest[i], 2))
               for i, d in enumerate(open_)]
    last = max(done) if open_ and all(m is not None for m in done) else None
    return Payoff(results, last, _add_months(start, last - 1) if last else None,
                  round(sum(interest), 2), round(monthly, 2))
