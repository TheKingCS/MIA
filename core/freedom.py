"""
core.freedom
==============

Freedom (DEC-0038; Life Runway, slice E of
docs/COGNITIVE_EXTENSION_PROPOSAL.md): the way out of the job you're
saving to leave, in numbers. The person's own plan, never a child's.

**The plan, in plain words.** A month of living needs some amount; the
homestead earns some of it; the **gap** is the rest. Freedom is having
enough saved to cover that gap for a **cushion** of months while the
homestead grows, plus the homestead **builds** still to pay for (the
greenhouse, the coop, solar, the root cellar: Projects with a budget,
core/homestead_costs.py). Saved so far, at the pace of the last three
months, reaches it on an **estimated date**. The day the homestead earns
the whole month, the gap is gone.

**Every number says where it came from** (`source`):
- a month of living: the person's own number, else the average of the
  last three full months of personal spending (build spending aside:
  that's what the builds line counts);
- the homestead: the business's books (core/ledger_manager.py: sales
  minus costs), three-month average;
- saved: cash in bank accounts (Plaid's depository balances, from the
  latest snapshots), else the person's own number;
- the pace: the person's own number, else the average of the last three
  full months of personal income minus spending;
- the date: an estimate, and says so.

`plan()` and the period sums are pure; `freedom_page()` gathers the
inputs from the stores and is served as /api/freedom.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

# The person's own settings (core/person_settings.py), with defaults.
SETTINGS = {
    "freedom.monthly_needs": 0.0,  # what a month of living takes (0: from spending)
    "freedom.cushion_months": 6,  # months of the gap to have saved
    "freedom.saved": 0.0,  # saved so far, until the bank says
    "freedom.monthly_saving": 0.0,  # saved a month (0: from income minus spending)
    "freedom.hourly": 0.0,  # take-home pay an hour at the job
    "freedom.shift_hours": 0.0,  # hours in a shift
}
DAYS_A_MONTH = 30.44
WINDOW_MONTHS = 3


@dataclass
class Inputs:
    needs: float = 0.0
    needs_source: str = ""
    homestead: float = 0.0
    homestead_source: str = ""
    saved: float = 0.0
    saved_source: str = ""
    pace: float = 0.0
    pace_source: str = ""
    cushion_months: int = 6
    builds_left: float = 0.0
    builds: list = field(default_factory=list)


def _r(x: float) -> float:
    return round(float(x or 0), 2)


def plan(i: Inputs, today: date) -> dict:
    """Pure logic. The freedom fund, how far along, the estimated date,
    and what moves it."""
    gap = max(0.0, i.needs - i.homestead)
    cushion = gap * max(0, int(i.cushion_months))
    goal = cushion + max(0.0, i.builds_left)
    covered = min(1.0, i.homestead / i.needs) if i.needs > 0 else None
    out = {"gap": _r(gap), "cushion": _r(cushion), "builds_left": _r(i.builds_left), "goal": _r(goal),
           "saved": _r(i.saved), "covered": round(covered, 3) if covered is not None else None,
           "progress": None, "left": None, "months": None, "date": None, "days": None, "ready": False,
           "levers": [], "why_no_date": ""}
    if i.needs <= 0:
        out["why_no_date"] = "Set what a month of living takes (or let the bank sync show it)."
        return out
    out["progress"] = round(min(1.0, i.saved / goal), 4) if goal > 0 else 1.0
    left = max(0.0, goal - i.saved)
    out["left"] = _r(left)
    if left <= 0:
        out.update(ready=True, months=0.0, date=today.isoformat(), days=0)
        return out
    if i.pace <= 0:
        out["why_no_date"] = ("At the last three months' pace the fund isn't growing, so there's no date yet."
                              if i.pace_source else "Set how much you save a month (or let the bank sync show it).")
        return out
    months = left / i.pace
    days = math.ceil(months * DAYS_A_MONTH)
    out.update(months=round(months, 1), days=days, date=(today + timedelta(days=days)).isoformat())

    def sooner(pace: float, homestead: float) -> int:
        g = max(0.0, i.needs - homestead) * max(0, int(i.cushion_months)) + max(0.0, i.builds_left)
        rest = max(0.0, g - i.saved)
        return days - math.ceil(rest / pace * DAYS_A_MONTH) if pace > 0 else 0

    step = 100.0
    out["levers"] = [
        {"what": "save more a month", "amount": step, "days_sooner": sooner(i.pace + step, i.homestead)},
        {"what": "homestead profit a month", "amount": step,
         "days_sooner": sooner(i.pace + step, i.homestead + step)},  # it's saved too, and it shrinks the gap
    ]
    return out


def shift(hourly: float, hours: float, needs: float, goal: float) -> Optional[dict]:
    """Pure logic. What one shift buys: its pay, the days of living it
    covers, and its step toward the fund."""
    if hourly <= 0 or hours <= 0:
        return None
    pay = hourly * hours
    return {"pay": _r(pay), "days_of_living": round(pay / (needs / DAYS_A_MONTH), 1) if needs > 0 else None,
            "of_goal": round(pay / goal, 4) if goal > 0 else None, "per_hour": _r(hourly), "hours": hours}


def week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def months_back(today: date, count: int) -> list[tuple[date, date]]:
    """Pure logic. The last `count` full months before this one, oldest
    first, as (first day, last day)."""
    out, first = [], today.replace(day=1)
    for _ in range(count):
        last = first - timedelta(days=1)
        first = last.replace(day=1)
        out.append((first, last))
    return list(reversed(out))


# ---------------------------------------------------------------- gathering


def _personal_spending(budget, start: str, end: str) -> float:
    """Personal spending in a period, builds aside (they're the builds line)."""
    return sum(e.amount for e in budget.all_expenses()
               if start <= e.date <= end and not getattr(e, "entity_id", "") and not getattr(e, "project_id", None))


def _personal_income(budget, start: str, end: str) -> float:
    return sum(i.amount for i in budget.all_income() if start <= i.date <= end and not getattr(i, "entity_id", ""))


def _homestead(ledger, start: str, end: str) -> float:
    return ledger.total_revenue(start, end) - ledger.total_expenses(start, end)


def bank_cash(context) -> Optional[float]:
    """Cash in bank accounts (checking, savings) from the latest
    snapshots: None when no bank is connected."""
    finance = getattr(context, "finance", None)
    if finance is None:
        return None
    total, saw = 0.0, False
    for snapshot in finance.all_latest_snapshots():
        for account in (snapshot.data or {}).get("accounts", []) or []:
            if str(account.get("type") or "").lower() != "depository":
                continue
            current = (account.get("balances") or {}).get("current")
            if current is not None:
                total += float(current)
                saw = True
    return total if saw else None


def settings(context) -> dict:
    from core import person_settings

    return {key: person_settings.get(context, key, default) for key, default in SETTINGS.items()}


def gather(context, today: date) -> tuple[Inputs, dict]:
    """The plan's inputs from the stores, and the monthly history behind them."""
    from core.homestead_costs import all_build_costs

    s = settings(context)
    budget = getattr(context, "budget", None)
    ledger = getattr(context, "ledger", None)
    window = months_back(today, WINDOW_MONTHS)
    history = []
    for first, last in months_back(today, 6):
        a, b = first.isoformat(), last.isoformat()
        spent = _personal_spending(budget, a, b) if budget is not None else 0.0
        earned = _personal_income(budget, a, b) if budget is not None else 0.0
        home = _homestead(ledger, a, b) if ledger is not None else 0.0
        history.append({"month": first.strftime("%Y-%m"), "label": first.strftime("%b"), "spent": _r(spent),
                        "income": _r(earned), "saved": _r(earned - spent), "homestead": _r(home)})
    recent = history[-WINDOW_MONTHS:]
    has_budget = any(h["spent"] or h["income"] for h in recent)
    has_ledger = any(h["homestead"] for h in recent)
    i = Inputs(cushion_months=int(s["freedom.cushion_months"] or 0))

    if float(s["freedom.monthly_needs"] or 0) > 0:
        i.needs, i.needs_source = float(s["freedom.monthly_needs"]), "your number"
    elif has_budget:
        i.needs, i.needs_source = sum(h["spent"] for h in recent) / len(recent), "your spending, 3-month average"
    if has_ledger:
        i.homestead, i.homestead_source = sum(h["homestead"] for h in recent) / len(recent), "the business's books, 3-month average"
    cash = bank_cash(context)
    if cash is not None:
        i.saved, i.saved_source = cash, "your bank accounts"
    elif float(s["freedom.saved"] or 0) > 0:
        i.saved, i.saved_source = float(s["freedom.saved"]), "your number"
    if float(s["freedom.monthly_saving"] or 0) > 0:
        i.pace, i.pace_source = float(s["freedom.monthly_saving"]), "your number"
    elif has_budget:
        # The homestead's money counts once it's in the bank (as income), never added twice.
        i.pace, i.pace_source = sum(h["saved"] for h in recent) / len(recent), "your income minus spending, 3-month average"

    builds = []
    if getattr(context, "projects", None) is not None:
        for cost in all_build_costs(context):
            if cost.status == "Complete" or cost.budget <= 0:
                continue
            builds.append({"id": cost.project_id, "name": cost.name, "budget": _r(cost.budget), "spent": _r(cost.spent),
                           "left": _r(max(0.0, cost.budget - cost.spent)), "status": cost.status})
    i.builds = builds
    i.builds_left = sum(b["left"] for b in builds)
    return i, {"history": history, "window": [(a.isoformat(), b.isoformat()) for a, b in window], "settings": s}


def periods(context, today: date) -> list[dict]:
    """Progress today, this week and this month: personal income minus
    spending (builds aside), plus the homestead's profit."""
    budget = getattr(context, "budget", None)
    ledger = getattr(context, "ledger", None)
    out = []
    for key, label, start in (("today", "Today", today), ("week", "This Week", week_start(today)),
                              ("month", "This Month", today.replace(day=1))):
        a, b = start.isoformat(), today.isoformat()
        saved = (_personal_income(budget, a, b) - _personal_spending(budget, a, b)) if budget is not None else 0.0
        home = _homestead(ledger, a, b) if ledger is not None else 0.0
        out.append({"id": key, "label": label, "saved": _r(saved), "homestead": _r(home), "total": _r(saved + home)})
    return out


def _money(x) -> str:
    from core.region import money

    return money(x)


def _signed(x: float) -> str:
    return ("+" if x > 0 else "−" if x < 0 else "") + _money(abs(x))


def freedom_page(context, today: Optional[date] = None) -> dict:
    """The Freedom screen: the plan, progress by period, the shift, the
    builds, six months of history, and the person's own reasons."""
    from core.child_accounts import is_child

    today = today or date.today()
    if is_child(context):
        return {"available": False}
    i, extra = gather(context, today)
    p = plan(i, today)
    s = extra["settings"]
    sh = shift(float(s["freedom.hourly"] or 0), float(s["freedom.shift_hours"] or 0), i.needs, p["goal"])
    why = []
    try:
        from core.why_graph import build_why_sheet

        sheet = build_why_sheet(context, today, record_checkpoint=False)
        for chain in sheet.chains[:2]:
            why.append([{"name": link.name, "reason": link.reason, "done": link.done} for link in chain])
        wins = sheet.wins[:3]
    except Exception:  # reasons are a bonus here, never a reason the screen fails
        wins = []
    words = {
        "needs": _money(i.needs) if i.needs else "", "homestead": _money(i.homestead) if i.homestead else _money(0),
        "saved": _money(p["saved"]), "goal": _money(p["goal"]), "gap": _money(p["gap"]), "left": _money(p["left"] or 0),
        "pace": _money(i.pace) if i.pace else "", "cushion": _money(p["cushion"]), "builds_left": _money(p["builds_left"]),
    }
    return {
        "available": True, "as_of": today.isoformat(),
        "plan": {**p, "text": words, "covered_pct": round(p["covered"] * 100) if p["covered"] is not None else None,
                 "progress_pct": round(p["progress"] * 100, 1) if p["progress"] is not None else None},
        "sources": {"needs": i.needs_source, "homestead": i.homestead_source, "saved": i.saved_source,
                    "pace": i.pace_source},
        "cushion_months": i.cushion_months,
        "periods": [{**x, "total_text": _signed(x["total"]), "saved_text": _signed(x["saved"]),
                     "homestead_text": _signed(x["homestead"])} for x in periods(context, today)],
        "shift": {**sh, "pay_text": _money(sh["pay"])} if sh else None,
        "builds": [{**b, "budget_text": _money(b["budget"]), "spent_text": _money(b["spent"]),
                    "left_text": _money(b["left"])} for b in i.builds],
        "history": extra["history"],
        "levers": [{**lv, "amount_text": _money(lv["amount"])} for lv in p["levers"]],
        "why": why, "wins": wins,
        "settings": s,
        "bank_connected": i.saved_source == "your bank accounts",
    }
