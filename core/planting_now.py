"""
core.planting_now
===================

What to plant now, and when to plant one crop (Jarvis brainstorm, round 5), for crops he hasn't planned yet: "what
can I plant now?", "when should I plant potatoes?", "is it too late for tomatoes?". The Planner's crop calendar
(core/garden_plans.py `CROPS`, from US land-grant extension planting calendars) dated from his last spring frost
(`garden.last_frost`, kept when he plans a garden or says it), never an assumed date: without it, she asks.

How: `window(crop, last_frost, today)` (pure) says where today falls for a crop: start indoors, transplant or sow,
coming up (with its date), or past its spring window. `now(last_frost, today)` lists the crops whose step falls in
the next DUE_DAYS days or the last LATE_DAYS (still fine). `say_now` and `say_crop` read his frost date and put it in
words. Read-only.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

DUE_DAYS = 14  # a step this soon is "now"
LATE_DAYS = 14  # and one this recent is still fine to do
SEASON_AFTER_DAYS = 90  # this long after the last frost, the spring that counts is next year's


def _frost(context, today: date) -> Optional[date]:
    """His last spring frost for the season ahead, from `garden.last_frost`, or None: this year's until three months
    after it, then next year's (in November the spring that counts is the coming one)."""
    from core.garden_plans import parse_day

    config = getattr(context, "config", None)
    said = str(config.get("garden.last_frost", "") if config is not None else "")
    found = parse_day(said, today.year) if said else None
    if found is not None and (today - found).days > SEASON_AFTER_DAYS:
        found = parse_day(said, today.year + 1)
    return found


def window(crop, last_frost: date, today: date) -> dict:
    """Pure logic. Where today falls for one crop: {"step", "on", "days"} for its next step (start indoors,
    transplant or sow; `days` from today, negative when it was that many days ago), or {"step": "past"} when its
    spring sowing is more than LATE_DAYS behind."""
    from core.garden_plans import schedule

    when = schedule(crop, last_frost)
    steps = [("start indoors", when["start_indoors"]), (when["how"], when["out"])]
    for step, on in steps:
        if on is None:
            continue
        days = (on - today).days
        if days >= -LATE_DAYS:
            return {"step": step, "on": on, "days": days}
    return {"step": "past", "on": when["out"], "days": (when["out"] - today).days}


def now(last_frost: date, today: date) -> list[dict]:
    """Pure logic. The crops whose next step falls from LATE_DAYS ago to DUE_DAYS ahead: [{name, step, on, days}],
    soonest first."""
    from core.garden_plans import CROPS

    out = []
    for crop in CROPS.values():
        w = window(crop, last_frost, today)
        if w["step"] != "past" and w["days"] <= DUE_DAYS:
            out.append({"name": crop.name, **w})
    return sorted(out, key=lambda x: (x["days"], x["name"]))


def _when(days: int, on: date) -> str:
    """Pure logic. "now", "in 5 days (Mar 3)", "since Feb 20"."""
    if days < 0:
        return f"since {on:%b} {on.day}"
    if days == 0:
        return "today"
    return f"in {days} day{'s' if days != 1 else ''} ({on:%b} {on.day})"


_ASK = ("When's your last spring frost? Tell me (\"my last frost is April 20\") and I'll work it out; your local "
        "extension office or a frost-date lookup by zip code has it.")


def say_now(context, today: Optional[date] = None) -> str:
    """For "what can I plant now?": the crops due now or just past, by step, from his last frost."""
    today = today or date.today()
    frost = _frost(context, today)
    if frost is None:
        return _ASK
    found = now(frost, today)
    if not found:
        return (f"Nothing on the spring calendar is due in the next two weeks (your last frost is {frost:%b} "
                f"{frost.day}). Ask me about one crop, like \"when do I plant tomatoes?\"")
    lines = [f"{x['name']}: {x['step']} {_when(x['days'], x['on'])}" for x in found]
    return f"From your last frost ({frost:%b} {frost.day}): " + "; ".join(lines) + "."


def say_crop(context, said: str, today: Optional[date] = None) -> str:
    """For "when should I plant potatoes?": that crop's next step and date, or that its spring window has passed."""
    from core.garden_plans import CROPS

    today = today or date.today()
    words = " ".join(str(said or "").lower().split())
    crop = next((c for c in sorted(CROPS.values(), key=lambda c: -len(c.name))
                 if c.id in words or c.name.lower() in words or c.name.lower().rstrip("s") in words), None)
    if crop is None:
        return "Which crop? I have the planting dates for " + ", ".join(sorted(c.name.lower() for c in CROPS.values())) + "."
    frost = _frost(context, today)
    if frost is None:
        return _ASK
    w = window(crop, frost, today)
    if w["step"] == "past":
        return f"The spring window for {crop.name.lower()} has passed: it was {w['on']:%b} {w['on'].day}."
    note = f" {crop.note[0].upper()}{crop.note[1:]}." if crop.note else ""
    return f"{crop.name}: {w['step']} {_when(w['days'], w['on'])}, from your last frost ({frost:%b} {frost.day}).{note}"
