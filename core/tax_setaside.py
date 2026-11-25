"""
core.tax_setaside
===================

"How much should I set aside for taxes?" (Jarvis brainstorm, round 12; his businesses): this year's workshop profit
so far from his ledger (core/ledger_manager.py, revenue less expenses since January 1), and what it owes the IRS,
worked out here and never by the model.

- **Self-employment tax** (`se_tax`): 15.3% (12.4% Social Security, 2.9% Medicare) of 92.35% of the profit, owed once
  that is $400 or more (Schedule SE). Past `WAGE_BASE_NOTE` the Social Security part stops at that year's wage base,
  which is said, never worked out from a number that changes each year.
- **Income tax**: his bracket isn't in his records, so it's said at 12% and 22%, the two most common, side by side,
  with a rate he gives ("I'm in the 24% bracket") among them; never called his, since the model may pass a bracket he
  never said (the live check, 2026-11-24, saw it send 12% unasked). Worked on the whole profit, before deductions (half the
  self-employment tax, the qualified business income deduction), so it errs high: safe to set aside.
- **The next estimated payment** (`next_due`): April 15, June 15, September 15 and January 15 (Form 1040-ES), a
  weekend or holiday moving it to the next business day.

US only (core/region.py): elsewhere it says so. A workshop at a loss or no profit owes no self-employment tax yet.
Rental income (Schedule E) isn't in it. Read-only; not tax advice, and it says a tax preparer has the last word.
Due dates move to the next business day past a weekend, Martin Luther King Jr. Day or DC Emancipation Day
(`business_day`).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

SE_RATE = 0.153
SE_SHARE = 0.9235
SE_FLOOR = 400.0
WAGE_BASE_NOTE = 150_000.0  # past this the Social Security part's yearly cap may apply
DUE = ((4, 15), (6, 15), (9, 15), (1, 15))  # month, day; January's is for the year before
COMMON_RATES = (12, 22)


def se_tax(profit: float) -> float:
    """Pure logic. Self-employment tax on a year's profit: 15.3% of 92.35% of it, 0 under $400 of that."""
    earnings = max(0.0, profit) * SE_SHARE
    return round(earnings * SE_RATE, 2) if earnings >= SE_FLOOR else 0.0


def _holidays(year: int) -> set:
    """Pure logic. The federal holidays that can land on a due date's next business day: Martin Luther King Jr. Day
    (January's third Monday) and DC Emancipation Day (April 16, observed Friday the 15th or Monday the 17th)."""
    first = date(year, 1, 1)
    mlk = first + timedelta(days=(0 - first.weekday()) % 7 + 14)
    emancipation = date(year, 4, 16)
    if emancipation.weekday() == 5:
        emancipation = date(year, 4, 15)
    elif emancipation.weekday() == 6:
        emancipation = date(year, 4, 17)
    return {mlk, emancipation}


def business_day(when: date) -> date:
    """Pure logic. The date, or the next business day when it's a weekend or one of those holidays."""
    while when.weekday() >= 5 or when in _holidays(when.year):
        when += timedelta(days=1)
    return when


def next_due(today: date) -> date:
    """Pure logic. The next estimated-tax due date on or after today: January 15 (last year's fourth), April 15, June
    15, September 15, then next January 15, each moved to the next business day (`business_day`: 2028's January 15 is
    a Saturday and the 17th Martin Luther King Jr. Day, so it's the 18th)."""
    dates = [date(today.year, 1, 15), *(date(today.year, m, d) for m, d in DUE[:3]), date(today.year + 1, 1, 15)]
    return next(business_day(when) for when in dates if business_day(when) >= today)


def rate_in(words: str) -> Optional[float]:
    """Pure logic. The rate he named ("12%", "the 22 percent bracket", "0.24"), as a percent, or None."""
    found = re.search(r"(\d+(?:\.\d+)?)\s*(%|percent|per cent)?", str(words or ""))
    if not found:
        return None
    value = float(found.group(1))
    value = value * 100 if value < 1 and not found.group(2) else value
    return value if 0 < value < 60 else None


def plan(profit: float, today: date, rate: Optional[float] = None) -> dict:
    """Pure logic. {profit, se, income: [(rate, amount)], total: [(rate, se + income)], due}: the common rates and a
    given one, lowest first."""
    se = se_tax(profit)
    rates = sorted({*COMMON_RATES, *((rate,) if rate else ())})
    income = [(r, round(max(0.0, profit) * r / 100, 2)) for r in rates]
    return {"profit": round(profit, 2), "se": se, "income": income,
            "total": [(r, round(se + amount, 2)) for r, amount in income], "due": next_due(today)}


def say(context, today: Optional[date] = None, rate=None) -> str:
    """The answer in words (see the module's opening)."""
    from core.region import country_of, money

    today = today or date.today()
    if country_of(context) != "US":
        return ("I work this out for US self-employment tax only, and your country is set to somewhere else: your "
                "tax office's guidance for the self-employed is the place to start.")
    ledger = getattr(context, "ledger", None)
    if ledger is None:
        return "The workshop ledger isn't on this MIA, so I have no profit to work from."
    profit = ledger.net_profit(f"{today.year}-01-01", today.isoformat())
    if profit <= 0:
        return (f"Your workshop ledger shows no profit so far in {today.year} ({money(profit)}), so there's no "
                "self-employment tax on it yet.")
    got = plan(profit, today, rate_in(rate) if rate else None)
    out = (f"Your workshop's profit so far in {today.year} is {money(got['profit'])}. Self-employment tax on it is "
           f"about {money(got['se'])} (15.3% of 92.35% of the profit)")
    if got["se"] == 0:
        out = (f"Your workshop's profit so far in {today.year} is {money(got['profit'])}: under the $400 of "
               "earnings that self-employment tax starts at")
    out += (". Income tax depends on your bracket: " + "; ".join(
        f"at {r:g}% it's about {money(a)}, so {money(t)} in all" for (r, a), (_r, t) in zip(got["income"],
                                                                                        got["total"])) + ".")
    if got["profit"] * SE_SHARE > WAGE_BASE_NOTE:
        out += " Past this much, the Social Security part may stop at this year's wage base, so it may be less."
    due = got["due"]
    out += (f" That errs high (before deductions like half the self-employment tax), so it's safe to set aside. The "
            f"next estimated payment (Form 1040-ES) is due {due.strftime('%B')} {due.day}, {due.year}. A tax preparer "
            "has the last word.")
    return out


def _tool(context, arguments: dict) -> str:
    """Tool tax_set_aside: `say`, with the bracket he named."""
    return say(context, rate=arguments.get("bracket"))


def register_tax_setaside_actions(registry) -> None:
    """Registers tax_set_aside."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="tax_set_aside", domain="business",
        description="How much to set aside for taxes on his workshop's profit this year: self-employment tax and "
                    "income tax at his bracket, and when the next quarterly estimated payment is due. The ledger's "
                    "totals alone are get_ledger_summary; his deadlines and filings are get_deadlines.",
        parameters={"type": "object", "properties": {
            "bracket": {"type": "string", "description": "his income tax bracket, only if he said, e.g. '12%'"}}},
        handler=_tool, trigger_phrases=("set aside for tax", "save for tax", "put away for tax", "owe in tax",
                                        "self-employment tax", "self employment tax", "tax on my profit",
                                        "tax on the shop", "my tax bracket", "owe the irs", "aside for taxes"),
    ))
