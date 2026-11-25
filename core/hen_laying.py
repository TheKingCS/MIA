"""
core.hen_laying
=================

"Why did my hens stop laying?" (Jarvis brainstorm, round 12; asked for, so no unprompted message: the daily check's
egg drop is core/unusual.py's): the likely causes for his flock, worked out from his own records and the sun for his
town, the most likely first, never one his records rule out.

- **Day length** (`day_hours`, offline from the sun for core/weather.place): under `LIGHT_HOURS` (14) hens slow down
  and many stop; said with today's daylight and the day it's back over 14 (`light_back`). The fix if he wants eggs
  through winter: a light on a timer adding the hours in the morning, so they still go to roost at dusk; letting them
  rest is fine too.
- **Molt** (late summer into fall, August to November in the north, February to May in the south): feathers dropping,
  6 to 12 weeks without eggs; more protein helps them through.
- **Age** (core/flock.py `started`): pullets start near 18 to 22 weeks; a flock past about three years lays
  noticeably less each year.
- **Heat** (today's or tomorrow's high at 90 °F or over, core/weather.card): shade and cool water.
- **Feed** (core/feed_runway.runway): running out or out.
- **Birds added or lost** in the last three weeks (the flock's log): a change in the flock is a stress.
- **What his log says** (core/flock.figures): the lay rate this week against the four weeks before, when there's
  enough of it.

Then what to check that only he can see: eggs laid somewhere new, water, a predator, mites. Facts in code; the model
only phrases them.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

LIGHT_HOURS = 14.0
HEAT_F = 90
PULLET_WEEKS = (18, 22)
OLD_YEARS = 3


def day_hours(lat: float, lon: float, day: date) -> Optional[float]:
    """Hours from sunrise to sunset that day (astral, in the place's own solar time, so a summer sunset past midnight
    UTC stays on its day), or None where the sun doesn't rise or set."""
    from datetime import timezone

    from astral import Observer
    from astral.sun import sun

    solar = timezone(timedelta(hours=round(lon / 15)))
    try:
        s = sun(Observer(lat, lon), day, tzinfo=solar)
    except ValueError:
        return None
    return round((s["sunset"] - s["sunrise"]).total_seconds() / 3600, 1)


def light_back(lat: float, lon: float, today: date) -> Optional[date]:
    """The first day ahead (within a year) with LIGHT_HOURS of daylight, or None."""
    for i in range(1, 366):
        day = today + timedelta(days=i)
        hours = day_hours(lat, lon, day)
        if hours is not None and hours >= LIGHT_HOURS:
            return day
    return None


def molt_season(today: date, lat: float) -> bool:
    """Pure logic. Late summer into fall where he is: August to November north of the equator, February to May
    south."""
    return today.month in ((8, 9, 10, 11) if lat >= 0 else (2, 3, 4, 5))


def _age(flock, today: date) -> Optional[int]:
    """Weeks since the flock came (its `started`), or None."""
    try:
        return (today - date.fromisoformat(str(flock.started)[:10])).days // 7
    except (TypeError, ValueError):
        return None


def causes(context, flock, today: date) -> list[str]:
    """The likely causes for one flock, most likely first (see the module's opening)."""
    from core import weather

    out = []
    where = weather.place(context)
    if where is not None:
        hours = day_hours(where["lat"], where["lon"], today)
        if hours is not None and hours < LIGHT_HOURS:
            back = light_back(where["lat"], where["lon"], today)
            out.append(f"Short days: {hours:g} hours of daylight today, and hens slow down or stop under about 14"
                       + (f"; it's back over 14 around {back:%B} {back.day}" if back else "") + ". For eggs through "
                       "winter, a light on a timer adding the hours in the morning (so they still roost at dusk) "
                       "brings them back; letting them rest is fine too.")
        if molt_season(today, where["lat"]):
            out.append("Molt season: feathers dropping means a molt, 6 to 12 weeks with few or no eggs; a higher "
                       "protein feed (about 20%) helps them regrow.")
    weeks = _age(flock, today)
    if weeks is not None and weeks < PULLET_WEEKS[0]:
        out.insert(0, f"Their age: about {weeks} weeks old, and pullets usually start at 18 to 22 weeks.")
    elif weeks is not None and weeks >= OLD_YEARS * 52:
        out.append(f"Their age: about {weeks // 52} years old, and hens lay less each year after their second or "
                   "third.")
    try:
        got = weather.card(context)
        highs = [h for h in (got.get("high"), (got.get("tomorrow") or {}).get("high")) if h is not None]
        hot = max(highs) if highs else None
        if hot is not None and (hot if "F" in str(got.get("unit", "")) else hot * 9 / 5 + 32) >= HEAT_F:
            out.append(f"Heat: a high of {hot}{got.get('unit', '')}; shade, cool water and air in the coop.")
    except Exception:  # noqa: BLE001 - no forecast leaves heat out
        pass
    try:
        from core.feed_runway import runway

        feed = runway(context.flock.entries_for(flock.flock_id), flock, today)
        if feed and not feed.get("unknown") and feed["days_left"] <= 0:
            out.insert(0, "Feed: by your log their feed has likely run out; hens stop laying within days without it.")
    except Exception:  # noqa: BLE001 - a log that can't be read leaves feed out
        pass
    try:
        changed = [e for e in context.flock.entries_for(flock.flock_id) if e.kind == "birds"
                   and date.fromisoformat(str(e.date)[:10]) >= today - timedelta(days=21)]
    except Exception:  # noqa: BLE001
        changed = []
    if changed:
        out.insert(0, "A change in the flock: birds were added or lost in the last three weeks, and the stress can "
                      "stop laying for a while.")
    return out


def _rates(context, flock, today: date) -> Optional[tuple]:
    """(this week's lay rate, the four weeks before's), eggs a hen a day, when both have logged eggs."""
    hens = max(0, int(flock.hens or 0))
    if not hens:
        return None
    entries = [e for e in context.flock.entries_for(flock.flock_id) if e.kind == "eggs"]

    def rate(start: date, end: date) -> Optional[float]:
        days = {str(e.date)[:10] for e in entries if start.isoformat() <= str(e.date)[:10] <= end.isoformat()}
        eggs = sum(e.count for e in entries if start.isoformat() <= str(e.date)[:10] <= end.isoformat())
        return round(eggs / (hens * len(days)), 2) if days else None

    now = rate(today - timedelta(days=6), today)
    before = rate(today - timedelta(days=34), today - timedelta(days=7))
    return (now, before) if now is not None and before is not None else None


CHECK = ("Worth checking yourself: eggs laid somewhere new (under bushes, in corners), water that's clean and not "
         "frozen, signs of a predator, and mites or lice (look under the wings and around the vent).")


def say(context, today: Optional[date] = None) -> str:
    """The answer for each flock (see the module's opening)."""
    from core import weather

    today = today or date.today()
    book = getattr(context, "flock", None)
    flocks = list(getattr(book, "flocks", []) or []) if book is not None else []
    if not flocks:
        return "No flock in MIA yet: add it under Apps → Chickens, and I'll work out why from their log."
    parts = []
    for flock in flocks:
        rates = _rates(context, flock, today)
        head = (f"{flock.name}: {rates[0]:g} eggs a hen a day this week, against {rates[1]:g} the four weeks before."
                if rates else f"{flock.name}:")
        found = causes(context, flock, today)
        parts.append(head + " " + (" ".join(f"{i}. {c}" for i, c in enumerate(found, 1)) if found else
                                   "Nothing in your records or the season explains it."))
    if weather.place(context) is None:
        parts.append("Tell me your town (\"my town is Springfield, Illinois\") and I'll count the daylight too.")
    return " ".join(parts) + " " + CHECK


def _tool(context, arguments: dict) -> str:
    """Tool why_hens_not_laying: `say`."""
    return say(context)


def register_hen_laying_actions(registry) -> None:
    """Registers why_hens_not_laying."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="why_hens_not_laying", domain="flock",
        description="Why his hens stopped laying or are laying less, and whether to put a light in the coop for "
                    "winter eggs: daylight against the 14 hours they need, molt season, their age, heat, feed and "
                    "changes in the flock, from his records and the season. How many eggs they laid is get_eggs; "
                    "plans to build a coop are find_plans.",
        parameters={"type": "object", "properties": {}},
        handler=_tool, trigger_phrases=("stopped laying", "stop laying", "not laying", "aren't laying",
                                        "laying less", "fewer eggs from", "no eggs from", "quit laying",
                                        "hens molting", "chickens molting", "start laying", "light in the coop",
                                        "coop light"),
    ))
