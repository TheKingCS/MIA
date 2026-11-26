"""
core.homestead_health
=======================

The homestead's health in one line (brainstorm round 16, 2026-11-25): how many days his water, food, the flock's
feed and the generator's fuel last, the lowest first ("Feed: 6 days, the lowest. Water: 9 days. Food: 23 days.
Fuel: 2 days of generator."), each worked out by the module that already keeps it (core/preparedness for water and
food, core/feed_runway for the feed, core/power_ready for the fuel), and what isn't counted said plainly.

How: `days(context, today)` (read-only) gives {name: days} for what can be counted, plus what can't and why;
`line(context)` says it. Asked by "how's the homestead?", "how long could we last?" (core/assistant_turn's
`_own_tool_reply` route) and joined to the morning briefing when something is low.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

LOW_DAYS = 7  # this few days or under is worth saying first, and in the morning briefing


def days(context, today: Optional[date] = None) -> tuple[dict, list]:
    """({"Water": 9.0, "Food": 23.0, "Feed": 6, "Fuel": 2.0}, [what isn't counted, in words]); read-only."""
    today = today or date.today()
    found, missing = {}, []
    try:
        from core import preparedness

        kitchen = getattr(context, "kitchen", None)
        items = kitchen.all_pantry_items() if kitchen is not None else []
        people = preparedness._setting(context, "prepared.people", 1)
        water, _unread = preparedness.water_days(items, people)
        food, counted, _uncounted = preparedness.food_days(items, people)
        if water:
            found["Water"] = water
        else:
            missing.append("water (none logged in the pantry)")
        if counted:
            found["Food"] = food
        else:
            missing.append("food (no staples logged by weight)")
    except Exception:  # noqa: BLE001 - one part that can't be read never takes the line with it
        log.exception("Homestead health: water and food couldn't be read")
    try:
        from core.feed_runway import runway

        book = getattr(context, "flock", None)
        for flock in getattr(book, "flocks", []) or []:
            got = runway(book.entries, flock, today)
            if got and not got.get("unknown") and got.get("days_left") is not None:
                found["Feed" if len(book.flocks) == 1 else f"Feed ({flock.name})"] = got["days_left"]
    except Exception:  # noqa: BLE001
        log.exception("Homestead health: the feed couldn't be read")
    try:
        from core import power_ready

        have, _unread = power_ready.fuel_on_hand(power_ready._records(context))
        gph = power_ready._number(context, "prepared.generator_gph", None)
        hours = power_ready._number(context, "prepared.generator_hours", power_ready.HOURS_A_DAY) or \
            power_ready.HOURS_A_DAY
        gallons = sum(have.values()) if have else 0
        if gallons and gph:
            found["Fuel"] = round(power_ready.run_days(gallons, gph, hours), 1)
        elif gallons:
            missing.append("fuel (his generator's burn rate isn't set)")
    except Exception:  # noqa: BLE001
        log.exception("Homestead health: the fuel couldn't be read")
    return found, missing


def line(context, today: Optional[date] = None) -> str:
    """The homestead's days in one line, the lowest first, and what isn't counted."""
    found, missing = days(context, today)
    if not found:
        return ("Nothing to count yet: log water and staples in the Pantry, the flock's feed with its weight, and your "
                "generator's fuel and burn rate, and I'll say how many days each lasts.")
    order = sorted(found.items(), key=lambda kv: kv[1])
    parts = []
    for i, (name, n) in enumerate(order):
        unit = "day" if n == 1 else "days"
        extra = " of generator" if name == "Fuel" else ""
        low = ", the lowest" if i == 0 and len(order) > 1 else ""
        parts.append(f"{name}: {n:g} {unit}{extra}{low}.")
    out = " ".join(parts)
    if missing:
        out += " Not counted: " + "; ".join(missing) + "."
    return out


def low_line(context, today: Optional[date] = None) -> str:
    """The ones at LOW_DAYS or under, for the morning briefing ("Running low: feed 5 days."); "" when none."""
    found, _missing = days(context, today)
    low = sorted(((n, v) for n, v in found.items() if v <= LOW_DAYS), key=lambda kv: kv[1])
    return ("Running low: " + ", ".join(f"{n.lower()} {v:g} day{'' if v == 1 else 's'}" for n, v in low) + ".") \
        if low else ""
