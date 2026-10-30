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

**H-0067 (Muse, 2026-10-21):** the fund is the accounts the person picks
(`freedom.fund_accounts`; all checking and savings until they pick); a
small daily log of the fund's balance (`FreedomLog`, their own file)
gives the pace today / this week / this month from real balance changes
and a **green-week streak** (a red week is said plainly, never
punished); the estimate is a **range** (from the best and the slowest of
the last three months), never one promised date; the builds keep the
person's own order (`freedom.build_order`), the first unfinished one is
the next target.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

# The person's own settings (core/person_settings.py), with defaults.
SETTINGS = {
    "freedom.monthly_needs": 0.0,  # what a month of living takes (0: from spending)
    "freedom.cushion_months": 6,  # months of the gap to have saved
    "freedom.saved": 0.0,  # saved so far, until the bank says
    "freedom.monthly_saving": 0.0,  # saved a month (0: from income minus spending)
    "freedom.fund_accounts": [],  # the bank accounts that are the fund (account ids); [] = all checking and savings
    "freedom.build_order": [],  # the builds in the person's own order (project ids)
}
# Retired 2026-10-30 (DEC-0052): pay is the Dungeon's (core/web_dungeon.job_pay).
# Read only by move_pay_to_dungeon(), once, to carry an old value over.
RETIRED_PAY = ("freedom.hourly", "freedom.shift_hours")
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
    pace_low: Optional[float] = None  # the slowest of the last three months (for the range)
    pace_high: Optional[float] = None  # the best
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
           "earliest": None, "latest": None,
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
    # The range (H-0067): at the best month's pace, and at the slowest; never one promised day.
    high = i.pace_high if i.pace_high and i.pace_high > 0 else None
    low = i.pace_low if i.pace_low and i.pace_low > 0 else None
    out["earliest"] = (today + timedelta(days=math.ceil(left / max(high, i.pace) * DAYS_A_MONTH))).isoformat() \
        if high else out["date"]
    out["latest"] = (today + timedelta(days=math.ceil(left / min(low, i.pace) * DAYS_A_MONTH))).isoformat() \
        if low else None  # a month that saved nothing: no latest day can be promised

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


def move_pay_to_dungeon(context) -> Optional[str]:
    """DEC-0052: Freedom used to keep its own take-home rate and shift.
    Pay belongs to the Dungeon now, so an old value moves there once: into
    the first dungeon that has no rate (made, named "Work", when there's
    none), as take-home (100% kept, since that's what it was). A dungeon
    that already has a rate keeps it: the owner wins. Then the old
    settings are cleared. Returns what happened, for the log."""
    from core import person_settings

    hourly = float(person_settings.get(context, RETIRED_PAY[0], 0.0) or 0)
    hours = float(person_settings.get(context, RETIRED_PAY[1], 0.0) or 0)
    book = getattr(context, "dungeon", None)
    if hourly <= 0 or book is None:
        return None
    target = next((d for d in book.dungeons if not d.hourly), None)
    if any(d.hourly for d in book.dungeons):
        said = "kept the Dungeon's rate"
    elif target is not None:
        book.update_dungeon(target.dungeon_id, hourly=hourly, take_home_pct=100,
                            **({"shift_hours": hours} if hours > 0 else {}))
        said = f"moved into {target.name}"
    else:
        book.add_dungeon("Work", hourly=hourly, take_home_pct=100, **({"shift_hours": hours} if hours > 0 else {}))
        said = "moved into a new dungeon, Work"
    for key in RETIRED_PAY:
        person_settings.put(context, key, 0.0)
    log.info("Freedom's own pay rate %s (DEC-0052).", said)
    return said


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


def bank_accounts(context) -> list[dict]:
    """The checking and savings accounts in the latest bank snapshots:
    id, name, last four digits, balance (for picking the fund)."""
    finance = getattr(context, "finance", None)
    out = []
    if finance is None:
        return out
    for snapshot in finance.all_latest_snapshots():
        for account in (snapshot.data or {}).get("accounts", []) or []:
            if str(account.get("type") or "").lower() != "depository":
                continue
            out.append({"id": str(account.get("account_id") or ""), "name": account.get("name") or "Account",
                        "mask": account.get("mask") or "", "bank": (snapshot.data or {}).get("institution_name") or "",
                        "balance": (account.get("balances") or {}).get("current")})
    return out


def bank_cash(context, only: Optional[list] = None) -> Optional[float]:
    """Cash in bank accounts (checking, savings) from the latest
    snapshots, only the accounts in `only` when given: None when no bank
    is connected."""
    finance = getattr(context, "finance", None)
    if finance is None:
        return None
    total, saw = 0.0, False
    for snapshot in finance.all_latest_snapshots():
        for account in (snapshot.data or {}).get("accounts", []) or []:
            if str(account.get("type") or "").lower() != "depository":
                continue
            if only and str(account.get("account_id") or "") not in only:
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
    picked = [str(a) for a in (s.get("freedom.fund_accounts") or [])]
    cash = bank_cash(context, picked or None)
    if cash is not None:
        i.saved, i.saved_source = cash, ("the accounts you picked as the fund" if picked else "your bank accounts")
        fund_log = getattr(context, "freedom_log", None)
        if fund_log is not None:
            fund_log.record(today, cash)
    elif float(s["freedom.saved"] or 0) > 0:
        i.saved, i.saved_source = float(s["freedom.saved"]), "your number"
    if float(s["freedom.monthly_saving"] or 0) > 0:
        i.pace, i.pace_source = float(s["freedom.monthly_saving"]), "your number"
    elif has_budget:
        # The homestead's money counts once it's in the bank (as income), never added twice.
        i.pace, i.pace_source = sum(h["saved"] for h in recent) / len(recent), "your income minus spending, 3-month average"
        i.pace_low, i.pace_high = min(h["saved"] for h in recent), max(h["saved"] for h in recent)

    builds = []
    if getattr(context, "projects", None) is not None:
        for cost in all_build_costs(context):
            if cost.status == "Complete" or cost.budget <= 0:
                continue
            builds.append({"id": cost.project_id, "name": cost.name, "budget": _r(cost.budget), "spent": _r(cost.spent),
                           "left": _r(max(0.0, cost.budget - cost.spent)), "status": cost.status})
    order = [str(x) for x in (s.get("freedom.build_order") or [])]
    builds.sort(key=lambda b: (order.index(b["id"]) if b["id"] in order else len(order), b["name"].lower()))
    i.builds = builds
    i.builds_left = sum(b["left"] for b in builds)
    return i, {"history": history, "window": [(a.isoformat(), b.isoformat()) for a, b in window], "settings": s}


def periods(context, today: date) -> list[dict]:
    """Progress today, this week and this month: the fund's own balance
    change when MIA has logged its balance since the period began
    (H-0067: "from snapshot deltas"), else personal income minus spending
    (builds aside) plus the homestead's profit. Each says which."""
    budget = getattr(context, "budget", None)
    ledger = getattr(context, "ledger", None)
    fund_log = getattr(context, "freedom_log", None)
    out = []
    for key, label, start in (("today", "Today", today), ("week", "This Week", week_start(today)),
                              ("month", "This Month", today.replace(day=1))):
        a, b = start.isoformat(), today.isoformat()
        change = fund_log.change(start, today) if fund_log is not None else None
        home = _homestead(ledger, a, b) if ledger is not None else 0.0
        if change is not None:
            out.append({"id": key, "label": label, "saved": _r(change), "homestead": _r(home), "total": _r(change),
                        "source": "the fund's balance"})
            continue
        saved = (_personal_income(budget, a, b) - _personal_spending(budget, a, b)) if budget is not None else 0.0
        out.append({"id": key, "label": label, "saved": _r(saved), "homestead": _r(home), "total": _r(saved + home),
                    "source": "income minus spending"})
    return out


def streak(weeks: list[float]) -> int:
    """Pure logic. Green weeks in a row, the latest last: how many of the
    most recent full weeks saved something."""
    n = 0
    for saved in reversed(weeks):
        if saved <= 0:
            break
        n += 1
    return n


def week_totals(context, today: date, count: int = 12) -> list[float]:
    """What each of the last `count` full weeks saved, oldest first: the
    fund's balance change when logged, else income minus spending."""
    budget = getattr(context, "budget", None)
    fund_log = getattr(context, "freedom_log", None)
    out = []
    this_week = week_start(today)
    for k in range(count, 0, -1):
        start = this_week - timedelta(days=7 * k)
        end = start + timedelta(days=6)
        change = fund_log.change(start, end) if fund_log is not None else None
        if change is None and budget is not None:
            a, b = start.isoformat(), end.isoformat()
            change = _personal_income(budget, a, b) - _personal_spending(budget, a, b)
        out.append(round(change or 0.0, 2))
    return out


class FreedomLog:
    """The fund's balance, once a day (H-0067): the person's own file,
    `freedom_log.json` in their folder. Written when the Freedom figures
    are read with a bank balance; read for balance changes."""

    FILE = "freedom_log.json"
    KEEP = 800  # days

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / self.FILE
        self._load()

    def _load(self) -> None:
        self.balances: dict[str, float] = {}
        if self._file.exists():
            try:
                raw = json.loads(self._file.read_text(encoding="utf-8"))
                self.balances = {str(k): float(v) for k, v in (raw.get("balances") or {}).items()}
            except (json.JSONDecodeError, OSError, TypeError, ValueError, AttributeError):
                log.exception("freedom_log.json unreadable — starting empty.")

    def reload(self) -> None:
        self._load()

    def record(self, day: date, balance: float) -> None:
        key = day.isoformat()
        if self.balances.get(key) == round(float(balance), 2):
            return
        self.balances[key] = round(float(balance), 2)
        for old in sorted(self.balances)[:-self.KEEP]:
            del self.balances[old]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"balances": self.balances}, indent=1))

    def balance_on(self, day: date) -> Optional[float]:
        """The latest balance logged on or before `day`."""
        key = day.isoformat()
        earlier = [k for k in self.balances if k <= key]
        return self.balances[max(earlier)] if earlier else None

    def change(self, start: date, end: date) -> Optional[float]:
        """The balance change from the end of the day before `start` to
        `end`; None when there's no balance from before `start`."""
        before = self.balance_on(start - timedelta(days=1))
        after = self.balance_on(end)
        return round(after - before, 2) if before is not None and after is not None else None


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
    try:
        move_pay_to_dungeon(context)
    except Exception:  # never the reason the screen fails
        log.exception("Couldn't move Freedom's pay rate to the Dungeon")
    i, extra = gather(context, today)
    p = plan(i, today)
    s = extra["settings"]
    from core.web_dungeon import job_pay

    pay = job_pay(context, today)
    rate = (pay["take_home_hourly"] or pay["hourly"]) if pay else 0.0
    sh = shift(float(rate or 0), pay["shift_hours"] if pay else 0.0, i.needs, p["goal"])
    if sh is not None:  # where the pay came from, said plainly
        sh["source"] = pay["dungeon"]
        sh["take_home"] = pay["take_home_hourly"] is not None
    why = []
    try:
        from core.why_graph import build_why_sheet

        sheet = build_why_sheet(context, today, record_checkpoint=False)
        for chain in sheet.chains[:2]:
            why.append([{"name": link.name, "reason": link.reason, "done": link.done} for link in chain])
        wins = sheet.wins[:3]
    except Exception:  # reasons are a bonus here, never a reason the screen fails
        wins = []
    weeks = _safe_weeks(context, today)
    accounts = bank_accounts(context)
    picked = set(str(a) for a in (s.get("freedom.fund_accounts") or []))
    nxt = next((b for b in i.builds if b["left"] > 0), None)
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
        "bank_connected": i.saved_source in ("your bank accounts", "the accounts you picked as the fund"),
        # H-0067
        "accounts": [{**a, "in_fund": (a["id"] in picked) if picked else True,
                      "balance_text": _money(a["balance"]) if a["balance"] is not None else ""} for a in accounts],
        "accounts_picked": bool(picked),
        "streak": streak(weeks), "weeks": weeks[-8:],
        "range": {"earliest": p.get("earliest"), "latest": p.get("latest")},
        "next_build": {**nxt, "pct": round(100 * nxt["spent"] / nxt["budget"]) if nxt["budget"] else 0,
                       "left_text": _money(nxt["left"]), "spent_text": _money(nxt["spent"]),
                       "budget_text": _money(nxt["budget"])} if nxt else None,
    }


def _safe_weeks(context, today: date) -> list[float]:
    try:
        return week_totals(context, today)
    except Exception:
        log.exception("Freedom: week totals failed")
        return []
