"""
core.web_dungeon
==================

The Dungeon screen (DEC-0046, core/work_dungeon.py), put together here so
the web only formats, and the same numbers MIA says in Talk and in Game
Master mode: today's run, this week's loot (earned, projected, the boss
bonus), the month and the year at this pace, what an overtime hour is
worth right now, loot banked (paychecks from the bank), the hard-mode
record, and how far one run moves the next dungeon (the Freedom plan).
Served as /api/dungeon.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)


def _money(x) -> str:
    from core.region import money

    return money(x)


def banked(context, dungeon, start: date, end: date) -> list:
    """The paychecks in the budget between two days (inclusive): the
    deposits whose description holds the dungeon's paycheck words, else
    everything filed as Salary."""
    budget = getattr(context, "budget", None)
    if budget is None:
        return []
    words = str(dungeon.payer or "").strip().lower()
    out = []
    for i in budget.all_income():
        d = (i.date or "")[:10]
        if not (start.isoformat() <= d <= end.isoformat()):
            continue
        if words and words not in (i.description or "").lower():
            continue
        if not words and i.category != "Salary":
            continue
        out.append(i)
    return out


def _run_row(run, split: dict, d) -> dict:
    from core.work_dungeon import AFFIX_BY_ID, boss_bonus, loot, run_xp

    regular, overtime = split.get(run.run_id, (run.hours, 0.0))
    boss = overtime > 0 or run.boss
    return {"id": run.run_id, "date": run.date, "hours": run.hours, "status": run.status,
            "affixes": [{"id": a, "name": AFFIX_BY_ID[a].name if a in AFFIX_BY_ID else a,
                         "real": AFFIX_BY_ID[a].real if a in AFFIX_BY_ID else a} for a in run.affixes],
            "boss": boss, "regular": regular, "overtime": overtime,
            "loot": loot(d, regular, overtime), "loot_text": _money(loot(d, regular, overtime)) if d.hourly else "",
            "bonus_text": _money(boss_bonus(d, overtime)) if overtime and d.hourly else "",
            "xp": run_xp(run.hours, run.affixes, boss), "note": run.note}


def dungeon_view(context, d, runs: list, today: date) -> dict:
    """One dungeon's numbers."""
    from core.work_dungeon import AFFIX_BY_ID, AFFIXES, boss_bonus, loot, split_hours, take_home_share, week_of

    cleared = split_hours(d, runs)
    projected = split_hours(d, runs, include_planned=True)
    mine = [r for r in runs if r.dungeon_id == d.dungeon_id]
    week0 = week_of(today, d.week_starts)
    week1 = week0 + timedelta(days=6)
    month0 = today.replace(day=1)
    month1 = (month0 + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    def total(split: dict, start: date, end: date, statuses=("cleared",)) -> tuple[float, float, float, float]:
        reg = ot = 0.0
        for r in mine:
            if r.status in statuses and r.run_id in split and start.isoformat() <= r.date <= end.isoformat():
                a, b = split[r.run_id]
                reg, ot = reg + a, ot + b
        return round(reg, 2), round(ot, 2), loot(d, reg, ot), boss_bonus(d, ot)

    w_reg, w_ot, w_loot, w_bonus = total(cleared, week0, week1)
    p_reg, p_ot, p_loot, p_bonus = total(projected, week0, week1, ("cleared", "planned"))
    m_loot = total(cleared, month0, month1)[2]
    mp_loot = total(projected, month0, month1, ("cleared", "planned"))[2]
    # The pace: the last four full pay weeks, cleared runs only.
    weeks = [total(cleared, week0 - timedelta(days=7 * k), week0 - timedelta(days=7 * k - 6)) for k in range(4, 0, -1)]
    worked = [w for w in weeks if w[0] + w[1] > 0]
    weekly = round(sum(w[2] for w in worked) / len(worked), 2) if worked else 0.0
    # Overtime right now: hours left this week before it starts, and what an overtime hour pays.
    limit = float(d.overtime_after or 0)
    hours_week = w_reg + w_ot
    to_ot = round(max(0.0, limit - hours_week), 2) if limit else None
    ot_hour = round(float(d.hourly or 0) * float(d.overtime_multiplier or 1), 2)
    boss_shift = loot(d, *(_after(to_ot, d.shift_hours) if to_ot is not None else (d.shift_hours, 0.0)))

    # Banked: the last 30 days of paychecks against the loot earned in the 30 days before each lands
    # (pay comes after the week it's for), and this month's.
    start60 = today - timedelta(days=59)
    paid = banked(context, d, start60, today)
    paid_30 = [p for p in paid if p.date[:10] >= (today - timedelta(days=29)).isoformat()]
    banked_30 = round(sum(p.amount for p in paid_30), 2)
    earned_window = total(cleared, today - timedelta(days=43), today - timedelta(days=7))[2]
    share, share_source = take_home_share(d, banked_30, earned_window)
    month_paid = [p for p in paid if p.date[:10] >= month0.isoformat()]
    latest = max(paid, key=lambda p: p.date) if paid else None

    upcoming = sorted((r for r in mine if r.status == "planned" and r.date > today.isoformat()), key=lambda r: r.date)
    waiting = sorted((r for r in mine if r.status == "planned" and r.date < today.isoformat()), key=lambda r: r.date)
    done = sorted((r for r in mine if r.status == "cleared"), key=lambda r: (r.date, r.created_at), reverse=True)
    # A night shift after midnight is still the run that started yesterday (core/the_loop.py).
    from core.the_loop import shift_day_for

    shift = shift_day_for(context, d.dungeon_id).isoformat() if today == date.today() else today.isoformat()
    today_run = next((r for r in mine if r.date == shift), None)

    # The hard-mode record: this month's and last month's, by modifier, with the dates.
    since = (month0 - timedelta(days=1)).replace(day=1)
    record = []
    for affix_id in dict.fromkeys([a.affix_id for a in AFFIXES] + [x for r in done for x in r.affixes]):
        dates = sorted({r.date for r in done if affix_id in r.affixes and r.date >= since.isoformat()})
        if dates:
            a = AFFIX_BY_ID.get(affix_id)
            record.append({"id": affix_id, "name": a.name if a else affix_id, "real": a.real if a else affix_id,
                           "this_month": sum(1 for x in dates if x >= month0.isoformat()), "dates": dates})
    record.sort(key=lambda x: -len(x["dates"]))
    net = (lambda x: _money(x * share) if share is not None and x else "")
    return {
        "id": d.dungeon_id, "name": d.name, "hourly": d.hourly, "set_up": bool(d.hourly),
        "rates": {"hourly_text": _money(d.hourly) if d.hourly else "", "overtime_text": _money(ot_hour) if d.hourly else "",
                  "multiplier": d.overtime_multiplier, "after": d.overtime_after, "week_starts": d.week_starts},
        "today": _run_row(today_run, projected, d) if today_run else None,
        "week": {"start": week0.isoformat(), "end": week1.isoformat(), "hours": round(hours_week, 2), "overtime": w_ot,
                 "earned": w_loot, "earned_text": _money(w_loot), "bonus_text": _money(w_bonus) if w_bonus else "",
                 "projected": p_loot, "projected_text": _money(p_loot), "projected_hours": round(p_reg + p_ot, 2),
                 "projected_overtime": p_ot, "projected_bonus_text": _money(p_bonus) if p_bonus else "",
                 "projected_net_text": net(p_loot)},
        "month": {"earned": m_loot, "earned_text": _money(m_loot), "projected": mp_loot, "projected_text": _money(mp_loot),
                  "projected_net_text": net(mp_loot)},
        "pace": {"weekly": weekly, "weekly_text": _money(weekly) if weekly else "", "yearly": round(weekly * 52, 2),
                 "yearly_text": _money(weekly * 52) if weekly else "", "weeks": len(worked),
                 "yearly_net_text": net(weekly * 52)},
        "overtime_now": {"hours_to_overtime": to_ot, "hour_text": _money(ot_hour) if d.hourly and limit else "",
                         "in_overtime": to_ot == 0 if to_ot is not None else False,
                         "boss_shift_hours": d.shift_hours, "boss_shift_text": _money(boss_shift) if d.hourly else ""},
        "banked": {"month": round(sum(p.amount for p in month_paid), 2),
                   "month_text": _money(sum(p.amount for p in month_paid)), "count_month": len(month_paid),
                   "last_30": banked_30, "last_30_text": _money(banked_30),
                   "latest": {"date": latest.date[:10], "amount_text": _money(latest.amount),
                              "description": latest.description, "from_bank": bool(latest.plaid_transaction_id)}
                   if latest else None,
                   "matching": f"deposits that say “{d.payer}”" if d.payer else "income filed as Salary",
                   "share_pct": round(share * 100) if share is not None else None, "share_source": share_source},
        "planned": [_run_row(r, projected, d) for r in upcoming[:14]],
        "waiting": [_run_row(r, projected, d) for r in waiting[-7:]],
        "runs": [_run_row(r, cleared, d) for r in done[:30]],
        "hard_mode": record,
        "values": {f: getattr(d, f) for f in ("name", "hourly", "overtime_multiplier", "overtime_after", "week_starts",
                                              "take_home_pct", "payer", "shift_hours", "break_minutes", "notes")},
        "share": share,
    }


def _after(regular_left: float, hours: float) -> tuple[float, float]:
    """Pure logic. A run of `hours` when `regular_left` regular hours
    remain this week: (regular, overtime)."""
    regular = max(0.0, min(hours, regular_left))
    return regular, round(hours - regular, 2)


def next_dungeon(context, view: Optional[dict], today: date) -> Optional[dict]:
    """The Freedom plan as the next dungeon: how far along, and what one
    usual run moves it (its take-home if known, else its gross)."""
    try:
        from core.freedom import gather, plan

        inputs, _ = gather(context, today)
        p = plan(inputs, today)
    except Exception:
        log.exception("Dungeon: the Freedom plan couldn't be read")
        return None
    if not p.get("goal") or p.get("progress") is None:
        return {"ready": False, "line": "Set up Freedom (Apps → Freedom) and the next dungeon shows here."}
    out = {"ready": True, "progress_pct": round(p["progress"] * 100, 1), "goal_text": _money(p["goal"]),
           "left_text": _money(p["left"] or 0), "saved_text": _money(p["saved"]), "date": p.get("date"),
           "earliest": p.get("earliest"), "latest": p.get("latest"), "unlocked": bool(p.get("ready"))}
    if view and view.get("hourly"):
        hours = float(view["values"]["shift_hours"] or 8)
        gross = hours * float(view["hourly"])
        share = view.get("share")
        moved = gross * share if share is not None else gross
        out.update(run_text=_money(moved), run_basis="take-home" if share is not None else "before taxes",
                   run_pct=round(100 * moved / p["goal"], 2) if p["goal"] else None,
                   runs_left=int(-(-(p["left"] or 0) // moved)) if moved > 0 and p["left"] else 0)
    return out


def _loop(context, today: date) -> dict:
    from core.the_loop import loop_page

    try:
        return loop_page(context, today)
    except Exception:
        log.exception("Dungeon: the loop couldn't be read")
        return {"available": False}


def job_pay(context, today: Optional[date] = None) -> Optional[dict]:
    """The person's pay, for everything else that needs it (DEC-0052: the
    Dungeon owns pay; Freedom and MIA's answers read it here, never keep
    their own). The first dungeon with a rate: gross an hour, the share
    that reaches the bank (theirs, or learned from deposits), take-home an
    hour and a shift's paid hours. None when no dungeon has a rate."""
    book = getattr(context, "dungeon", None)
    d = next((x for x in (book.dungeons if book is not None else []) if x.hourly), None)
    if d is None:
        return None
    view = dungeon_view(context, d, book.runs, today or date.today())
    share = view["share"]
    net = round(d.hourly * share, 2) if share is not None else None
    return {"dungeon": d.name, "dungeon_id": d.dungeon_id, "hourly": d.hourly, "share": share,
            "share_source": view["banked"]["share_source"], "take_home_hourly": net,
            "shift_hours": float(d.shift_hours or 0),
            "weekly_pace": view["pace"]["weekly"]}


def dungeon_page(context, today: Optional[date] = None) -> dict:
    from core.child_accounts import is_child
    from core.dungeon_actions import DUNGEON
    from core.record_actions import record_form
    from core.work_dungeon import AFFIXES, DAYS

    today = today or date.today()
    book = getattr(context, "dungeon", None)
    if book is None or is_child(context):
        return {"available": False}
    views = [dungeon_view(context, d, book.runs, today) for d in book.dungeons]
    first = views[0] if views else None
    return {
        "available": True, "as_of": today.isoformat(),
        "dungeons": views,
        "summary": {"week_text": _money(sum(v["week"]["earned"] for v in views)),
                    "projected_text": _money(sum(v["week"]["projected"] for v in views)),
                    "banked_text": _money(sum(v["banked"]["month"] for v in views)),
                    "hard_this_month": sum(x["this_month"] for v in views for x in v["hard_mode"])},
        "next_dungeon": next_dungeon(context, first, today),
        "loop": _loop(context, today),
        "affixes": [{"id": a.affix_id, "name": a.name, "real": a.real, "line": a.line, "xp": a.xp} for a in AFFIXES],
        "forms": {"dungeon": record_form(DUNGEON)}, "picks": {"days": [{"id": x, "name": x} for x in DAYS]},
    }
