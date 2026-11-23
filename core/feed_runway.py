"""
core.feed_runway
==================

How long the hens' feed will last (Jarvis brainstorm round 2; Zac, 2026-11-23: "homestead skills ... aware"), from his
flock log (core/flock.py): the last bag bought, how much his flock really eats (from his own purchases over time, at
least two weeks of them), else the usual quarter pound a hen a day (US extension guidance for laying hens), and the day
it's likely to run out. A guess from his own numbers, said as one ("about"), never more exact than it is.

`runway(entries, flock, today)` is the figure; `words` says it; `soon(context, today)` is what core/unusual.py offers
when a flock is down to RUN_LOW days, once for each bag (its key names the purchase).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

LB_A_HEN_A_DAY = 0.25
RUN_LOW = 5  # days of feed left worth a word
HISTORY_DAYS = 14  # his own rate needs at least this much purchase history


def _day(text: str) -> Optional[date]:
    """A date from text, or None."""
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def runway(entries: list, flock, today: date) -> Optional[dict]:
    """Pure logic. {left_lb, days_left, runs_out, rate, from_history, bought_on} for this flock's feed, or None without
    a purchase with pounds, or without hens."""
    birds = max(0, int(getattr(flock, "hens", 0) or 0)) + max(0, int(getattr(flock, "roosters", 0) or 0))
    if not birds:
        return None
    buys = sorted(((d, float(e.pounds)) for e in entries
                   if e.flock_id == flock.flock_id and e.kind == "feed" and float(e.pounds or 0) > 0
                   and (d := _day(e.date)) is not None and d <= today), key=lambda x: x[0])
    if not buys:
        return None
    rate, from_history = birds * LB_A_HEN_A_DAY, False
    span = (buys[-1][0] - buys[0][0]).days
    if len(buys) >= 2 and span >= HISTORY_DAYS:
        rate, from_history = sum(lb for _d, lb in buys[:-1]) / span, True  # what he bought before the last bag lasted
    last_day, last_lb = buys[-1]
    left = max(0.0, last_lb - rate * (today - last_day).days)
    days_left = int(left / rate) if rate > 0 else 0
    return {"left_lb": round(left, 1), "days_left": days_left, "runs_out": today + timedelta(days=days_left),
            "rate": round(rate, 2), "from_history": from_history, "bought_on": last_day.isoformat()}


def words(name: str, found: dict) -> str:
    """Pure logic. The runway in a sentence, saying where the rate came from."""
    how = (f"at the {found['rate']:g} lb a day your flock has been going through" if found["from_history"]
           else f"at the usual quarter pound a hen a day ({found['rate']:g} lb a day)")
    if found["days_left"] <= 0:
        return f"{name}'s feed has likely run out by now, {how}. Buy feed, and log it so I can keep count."
    out = found["runs_out"]
    return (f"{name} has about {found['left_lb']:g} lb of feed left, {how}: about {found['days_left']} days, "
            f"so it likely runs out around {out:%A, %B} {out.day}.")


def soon(context, today: date) -> list[dict]:
    """Each flock whose feed is down to RUN_LOW days or less: {kind, title, text, key} for core/unusual.py, once per
    bag bought."""
    book = getattr(context, "flock", None)
    out = []
    for flock in getattr(book, "flocks", []) or []:
        found = runway(book.entries, flock, today)
        if found is not None and found["days_left"] <= RUN_LOW:
            out.append({"kind": "feed", "title": f"{flock.name}: feed running low", "text": words(flock.name, found),
                        "key": f"feed-{flock.flock_id}-{found['bought_on']}"})
    return out
