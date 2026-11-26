"""
core.homestead_health
=======================

The homestead's health in one line (brainstorm round 16, 2026-11-25): how many days his water, food, the flock's
feed and the generator's fuel last, the lowest first ("Feed: 6 days, the lowest. Water: 9 days. Food: 23 days.
Fuel: 2 days of generator."), each worked out by the module that already keeps it (core/preparedness for water and
food, core/feed_runway for the feed, core/power_ready for the fuel), and what isn't counted said plainly.

How: `days(context, today)` (read-only) gives {name: days} for what can be counted, plus what can't and why;
`line(context)` says it. Asked by "how's the homestead?", "how long could we last?" (core/assistant_turn's
`_own_tool_reply` route) and joined to the morning briefing when something is low (`low_line`: water, food and fuel at
a week or under, each said at most once a week; the feed is left to core/feed_runway.soon, which offers once a bag).
Water here is the pantry's drinking water; fuel is only his generator's own (`prepared.generator_fuel`). The Fable
review (2026-11-25) found every fuel summed, a zero staple read as "Food: 0 days" and an unknown bag left unsaid.
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
        if counted and food > 0:  # a staple logged at 0 is no food, not "Food: 0 days"
            found["Food"] = food
        else:
            missing.append("food (no staples logged by weight)")
    except Exception:  # noqa: BLE001 - one part that can't be read never takes the line with it
        log.exception("Homestead health: water and food couldn't be read")
    try:
        from core.feed_runway import runway

        book = getattr(context, "flock", None)
        flocks = getattr(book, "flocks", []) or []
        for i, flock in enumerate(flocks):
            got = runway(book.entries, flock, today)
            name = "Feed" if len(flocks) == 1 else f"Feed ({flock.name})"
            if name in found:  # two flocks with one name
                name = f"Feed ({flock.name} {i + 1})"
            if got and got.get("unknown"):
                missing.append(f"{name.lower()} (the last bag's weight isn't logged)")
            elif got and got.get("days_left") is not None:
                found[name] = got["days_left"]
    except Exception:  # noqa: BLE001
        log.exception("Homestead health: the feed couldn't be read")
    try:
        from core import power_ready

        from core import person_settings

        have, unread = power_ready.fuel_on_hand(power_ready._records(context))
        gph = power_ready._number(context, "prepared.generator_gph", None)
        hours = power_ready._number(context, "prepared.generator_hours", power_ready.HOURS_A_DAY) or \
            power_ready.HOURS_A_DAY
        fuel = power_ready.SAID_AS.get(str(person_settings.get(context, "prepared.generator_fuel", "gasoline")
                                           or "").lower(), "gasoline")
        gallons = (have or {}).get(fuel, 0)  # only the generator's own fuel runs it
        if gallons and gph:
            found["Fuel"] = round(power_ready.run_days(gallons, gph, hours), 1)
        elif gallons:
            missing.append("fuel (your generator's burn rate isn't set)")
        elif unread:
            missing.append("fuel (logged without an amount, like \"5 gal\")")
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


SAID_KEY = "homestead.low_said"  # {name: ISO date it was last said in the briefing}
QUIET_DAYS = 7


def low_line(context, today: Optional[date] = None) -> str:
    """Water, food and fuel at LOW_DAYS or under, for the morning briefing ("Running low: water 5 days."), each at most
    once every QUIET_DAYS (kept in person_settings under SAID_KEY); the feed is core/feed_runway.soon's. "" when
    none is due."""
    today = today or date.today()
    found, _missing = days(context, today)
    try:
        from core import person_settings

        said = dict(person_settings.get(context, SAID_KEY, {}) or {})
    except Exception:  # noqa: BLE001 - no settings: say it, remember nothing
        person_settings, said = None, {}
    due = []
    for name, value in sorted(found.items(), key=lambda kv: kv[1]):
        if name.startswith("Feed") or value > LOW_DAYS:
            continue
        try:
            last = date.fromisoformat(said.get(name, ""))
        except ValueError:
            last = None
        if last is not None and (today - last).days < QUIET_DAYS:
            continue
        due.append((name, value))
        said[name] = today.isoformat()
    if not due:
        return ""
    if person_settings is not None:
        try:
            person_settings.put(context, SAID_KEY, said)
        except Exception:  # noqa: BLE001
            log.exception("Homestead health: couldn't remember what the briefing said")
    return "Running low: " + ", ".join(f"{n.lower()} {v:g} day{'' if v == 1 else 's'}" for n, v in due) + "."
