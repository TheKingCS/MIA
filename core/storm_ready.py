"""
core.storm_ready
==================

"Is a storm coming? Get me ready." (Jarvis brainstorm, round 10; asked for, so no unprompted message): the next three
days' forecast (core/weather.py) read for a storm, and one checklist from his own records for it.

**A storm** (`storms`): a day whose weather is thunderstorms, freezing rain or drizzle, heavy rain or snow, or whose
gusts reach `GUST_MPH` (40 mph, 65 km/h: the National Weather Service's wind advisory is about there). Each said with
its day and what it is.

**The checklist** (`checklist`), each line only when it applies: the generator's fuel days (core/power_ready.say), his
drinking water in days (core/preparedness.water_days), the hens shut in with water that won't freeze (a flock), the
greenhouse's air pump on backup power (the greenhouse taken over), the pipes (and the well's pump house) kept from
freezing when one of the three nights is cold enough (`cold_nights`, core/weather_watch.PIPES_FREEZE), lumber, tarps and tools put away (a build in
progress), phones and power banks charged, and "the power went out" to start the outage clock if it goes
(core/outage.py). With no storm in three days, that's said with the days' weather.

Facts from the forecast and his records; the model only phrases them.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

GUST_MPH = 40
GUST_KMH = 65
STORMY = ("thunderstorm", "freezing rain", "freezing drizzle", "heavy rain", "heavy snow", "snow", "heavy showers",
          "hail")


def storms(forecast: dict, days: int = 3) -> list[dict]:
    """Pure logic. The stormy days among the next `days` (today first): each {date, why}."""
    gust_limit = GUST_MPH if "F" in str((forecast or {}).get("unit", "")) else GUST_KMH
    speed = "mph" if gust_limit == GUST_MPH else "km/h"
    out = []
    for day in ((forecast or {}).get("days") or [])[:days]:
        words = str(day.get("words") or "").lower()
        reasons = [day["words"].lower()] if any(w in words for w in STORMY) else []
        if (day.get("gust") or 0) >= gust_limit:
            reasons.append(f"gusts to {day['gust']} {speed}")
        if reasons:
            out.append({"date": str(day.get("date", "")), "why": " and ".join(reasons)})
    return out


def _day(iso: str) -> str:
    """Pure logic. "2026-11-26" -> "Thursday"; today and tomorrow by name."""
    try:
        when = date.fromisoformat(iso)
    except ValueError:
        return iso
    delta = (when - date.today()).days
    return "today" if delta == 0 else "tomorrow" if delta == 1 else when.strftime("%A")


def cold_nights(forecast: dict, days: int = 3) -> list[dict]:
    """Pure logic. The next `days` days whose low reaches the pipes' freezing point (core/weather_watch.PIPES_FREEZE,
    20 °F, -7 °C): each {date, low}."""
    from core.weather_watch import PIPES_FREEZE, _f

    unit = str((forecast or {}).get("unit", ""))
    return [{"date": str(d.get("date", "")), "low": d["low"]} for d in ((forecast or {}).get("days") or [])[:days]
            if d.get("low") is not None and _f(d["low"], unit) <= PIPES_FREEZE]


def checklist(context, forecast: dict = None) -> list[str]:
    """What to do from his records before a storm (see the module's opening); `forecast` adds the pipes when a night
    in it is cold enough."""
    from core import power_ready, preparedness, weather_watch

    lines = [power_ready.say(context)]
    cold = cold_nights(forecast) if forecast else []
    if cold:
        coldest = min(cold, key=lambda c: c["low"])
        lines.append(f"Keep the pipes from freezing (a low of {coldest['low']}{forecast.get('unit', '')} "
                     f"{_day(coldest['date'])}): drip a faucet on an outside wall, open the sink cabinets, unhook the "
                     "hoses" + (", and keep the well's pump house from freezing." if weather_watch._well(context)
                                else "."))
    kitchen = getattr(context, "kitchen", None)
    people = preparedness._setting(context, "prepared.people", 1)
    water, _unread = preparedness.water_days(kitchen.all_pantry_items() if kitchen is not None else [], people)
    lines.append(f"Drinking water: about {water:g} days at a gallon a person a day." if water else
                 "Fill water jugs: a gallon a person a day, in case the power or the well goes.")
    if weather_watch._birds(context):
        lines.append("Shut the hens in early, with water that won't freeze or tip.")
    link = getattr(context, "greenhouse_link", None)
    if link is not None and getattr(link, "taken_over", False):
        lines.append("Check the greenhouse's air pump has backup power: the fish need aeration if the power goes.")
    try:
        builds = weather_watch._builds(context)
    except Exception:  # noqa: BLE001 - a plan that can't be read leaves the line out
        builds = ()
    if builds:
        lines.append(f"Put lumber, tarps and tools from {', '.join(builds)} away or tie them down.")
    lines.append("Charge phones and power banks. If the power goes, tell me \"the power went out\" and I'll keep "
                 "the clock on the food.")
    return lines


def say(context, fetch=None) -> str:
    """The answer: the storm days and the checklist (with the forecast, so a hard-freeze night adds the pipes), or
    that none is in the next three days."""
    from core import weather

    got = weather.card(context, fetch)
    if got.get("set"):
        return "I don't know your town yet. Tell me which one, like \"my town is Springfield, Illinois\"."
    if got.get("loading") or not got.get("days"):
        return f"I'm getting the forecast for {got.get('place') or 'your town'}; ask me again in a moment."
    found = storms(got)
    if not found:
        return ("Nothing stormy in the next three days: " + "; ".join(
            f"{_day(d['date'])} {str(d.get('words') or '').lower()}" for d in got["days"][:3]) + ".")
    head = "Coming: " + "; ".join(f"{_day(s['date'])}, {s['why']}" for s in found) + "."
    return head + " Before it: " + " ".join(checklist(context, got))
