"""
core.money_ahead
==================

The next 13 weeks of money, week by week (Jarvis brainstorm 6.1; Zac, 2026-11-23: "finance skills"): what's coming
in and going out from the bills, income and debt payments he keeps in the budget, so the tight weeks show before they
come. Worked out in code from his records; the model only says it. No bank balance goes into it (bank linking waits,
Zac 2026-11-17), so it shows each week's flow, never a balance it can't know.

- **In**: each income source's expected amount on each day it's due (core/budget_manager.next_income_due_date for the
  first, then `date_recurs_on` from its anchor); every one expected but not yet received counts today, said as late.
- **Out**: each bill the same way (every missed one today, said as overdue; a bill on the 31st skips shorter months,
  as `date_recurs_on` does), and each debt's minimum once a month, on the day of the month he last paid it (the 1st
  when he never logged a payment: said), not again in a month already paid, and not at all when a bill of the same
  name already holds that payment.
- **The weeks** (`weeks`): Monday to Sunday, from this week; each {start, in, out, net, items}. `tight` are those where
  more goes out than comes in, the worst first.

`say(context)` is the tool `money_ahead`'s answer; `page(context)` the Budget page's "Next 13 Weeks" panel.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

WEEKS = 13


def _monday(day: date) -> date:
    """Pure logic. The Monday of the week a day falls in."""
    return day - timedelta(days=day.weekday())


def _dates(first: Optional[date], anchor_text: str, recurrence: Optional[str], end: date) -> list[date]:
    """Pure logic. The next due day and every later occurrence up to `end` (only the first for a one-time item)."""
    from core.calendar_manager import date_recurs_on

    if first is None or first > end:
        return []
    out = [first]
    if recurrence is None:
        return out
    try:
        anchor = date.fromisoformat(anchor_text)
    except ValueError:
        return out
    day = first + timedelta(days=1)
    while day <= end:
        if date_recurs_on(anchor, recurrence, day):
            out.append(day)
        day += timedelta(days=1)
    return out


def _monthly(day_of_month: int, start: date, end: date) -> list[date]:
    """Pure logic. That day of each month from start to end (the month's last day when it's shorter)."""
    import calendar

    out, year, month = [], start.year, start.month
    while True:
        last = calendar.monthrange(year, month)[1]
        day = date(year, month, min(day_of_month, last))
        if day > end:
            return out
        if day >= start:
            out.append(day)
        month += 1
        if month > 12:
            year, month = year + 1, 1


def flows(bills: list, incomes: list, debts: list, today: date, weeks: int = WEEKS) -> list[dict]:
    """Pure logic. Every money movement in the window: {day, amount (+ in, - out), what, note}. Every late or
    overdue one is put on today, with its note; a debt's minimum skips a month already paid and a debt whose payment
    is already a bill of the same name."""
    from core.budget_manager import next_bill_due_date, next_income_due_date

    end = _monday(today) + timedelta(weeks=weeks, days=-1)
    out = []
    billed = [b.name.lower() for b in bills]
    for b in bills:
        for day in _dates(next_bill_due_date(b), b.due_date, b.recurrence, end):
            late = day < today  # every missed one, not only the first, counts now
            out.append({"day": today if late else day, "amount": -float(b.amount), "what": b.name,
                        "note": "overdue" if late else ""})
    for s in incomes:
        for day in _dates(next_income_due_date(s), s.next_date, s.recurrence, end):
            late = day < today
            out.append({"day": today if late else day, "amount": float(s.expected_amount), "what": s.name,
                        "note": "late" if late else ""})
    for d in debts:
        if float(d.minimum_payment or 0) <= 0 or float(d.balance or 0) <= 0:
            continue
        name = d.name.lower()
        if any(name in b or b in name for b in billed):
            continue  # its payment is already a bill: counted once
        try:
            paid = date.fromisoformat(str(d.last_payment_date)[:10])
            dom, note = paid.day, ""
        except ValueError:
            paid, dom, note = None, 1, "on the 1st: no payment logged yet to know its day"
        for day in _monthly(dom, today, end):
            if paid is not None and (day.year, day.month) == (paid.year, paid.month):
                continue  # this month's is paid already
            out.append({"day": day, "amount": -float(d.minimum_payment), "what": f"{d.name} minimum", "note": note})
    return sorted(out, key=lambda f: (f["day"], f["amount"]))


def weeks(movements: list, today: date, count: int = WEEKS) -> list[dict]:
    """Pure logic. The movements by week, Monday first: {start, in, out, net, items}."""
    first = _monday(today)
    out = [{"start": first + timedelta(weeks=i), "in": 0.0, "out": 0.0, "items": []} for i in range(count)]
    for m in movements:
        i = (_monday(m["day"]) - first).days // 7
        if 0 <= i < count:
            week = out[i]
            week["in" if m["amount"] > 0 else "out"] += abs(m["amount"])
            week["items"].append(m)
    for week in out:
        week["in"], week["out"] = round(week["in"], 2), round(week["out"], 2)
        week["net"] = round(week["in"] - week["out"], 2)
    return out


def tight(by_week: list) -> list[dict]:
    """Pure logic. The weeks where more goes out than comes in, the worst first."""
    return sorted((w for w in by_week if w["net"] < 0), key=lambda w: w["net"])


def _records(context) -> tuple[list, list, list]:
    """His bills, income sources and debts (empty without a budget)."""
    budget = getattr(context, "budget", None)
    if budget is None:
        return [], [], []
    return budget.all_bills(), budget.all_income_sources(), budget.all_debts()


def page(context, today: Optional[date] = None) -> dict:
    """The Budget page's "Next 13 Weeks": each week {start, label, in, out, net, items said} and the tight ones."""
    from core.region import money

    today = today or date.today()
    by_week = weeks(flows(*_records(context), today), today)
    said = []
    for w in by_week:
        said.append({"start": w["start"].isoformat(), "label": f"{w['start']:%b} {w['start'].day}", "in": w["in"], "out": w["out"], "net": w["net"],
                     "in_text": money(w["in"]), "out_text": money(w["out"]),
                     "items": [f"{m['day']:%a} {m['day'].day}: {m['what']} {money(abs(m['amount']))}"
                               + (f" ({m['note']})" if m["note"] else "") for m in w["items"]]})
    return {"weeks": said, "tight": [f"{w['start']:%b} {w['start'].day}" for w in tight(by_week)],
            "any": any(w["items"] for w in by_week)}


def say(context, today: Optional[date] = None) -> str:
    """For "what does money look like the next few months?": the totals, the tight weeks with what's in them, and
    anything overdue or late now."""
    from core.region import money

    today = today or date.today()
    moves = flows(*_records(context), today)
    if not moves:
        return ("I don't have any bills, income or debt payments in your budget to look ahead with. Add them in Budget "
                "and I'll show you the next 13 weeks.")
    by_week = weeks(moves, today)
    total_in = sum(w["in"] for w in by_week)
    total_out = sum(w["out"] for w in by_week)
    parts = [f"The next 13 weeks: {money(total_in)} coming in and {money(total_out)} going out, from what's in your "
             f"budget (no bank balance: that waits for bank linking)."]
    now = [m for m in moves if m["note"] in ("overdue", "late")]
    if now:
        parts.append("Right now: " + "; ".join(f"{m['what']} {money(abs(m['amount']))} is {m['note']}" for m in now) + ".")
    worst = tight(by_week)
    if worst:
        w = worst[0]
        outs = sorted((m for m in w["items"] if m["amount"] < 0), key=lambda m: m["amount"])[:4]
        parts.append(f"Tightest: the week of {w['start']:%B} {w['start'].day}, {money(w['out'])} out against "
                     f"{money(w['in'])} in ({', '.join(m['what'] for m in outs)}).")
        if len(worst) > 1:
            parts.append(f"{len(worst) - 1} more week{'s' if len(worst) > 2 else ''} with more going out than coming "
                         "in: " + ", ".join(f"{x['start']:%b} {x['start'].day}" for x in worst[1:5]) + ".")
    else:
        parts.append("No week has more going out than coming in.")
    return " ".join(parts)
