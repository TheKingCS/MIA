"""
core.outdoor_work
===================

"Is it safe to work outside today?" (Jarvis brainstorm, round 12; asked for, so no unprompted message): the day's
hourly forecast (core/weather.py `hours`) read for heat and cold, with the National Weather Service's own formulas,
worked out here and never by the model.

**Heat** (`heat_index`): the NWS heat index (the Rothfusz regression, with its low- and high-humidity adjustments,
and Steadman's simple form below about 80 °F), and its levels (`HEAT_LEVELS`): caution from 80 °F, extreme caution
from 90, danger from 103, extreme danger from 125. At 90 or more the cooler hours to do the heavy work are named
(`cool_hours`), with OSHA's advice: a cup of water every 15 to 20 minutes, rest in the shade, and the signs of heat
stroke with the emergency number for his country (core/region.py).

**Cold** (`wind_chill`): the NWS wind chill (2001; air at 50 °F or colder, wind over 3 mph), and the time to
frostbite on bare skin from its chart (`FROSTBITE`: about 30 minutes at -18 °F, 10 at -33, 5 at -48), with the
warmest hours named.

Only the working day (`DAY_HOURS`, 6 am to 8 pm) is read. Figures in his own unit (°F or °C, as the forecast is).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Optional

DAY_HOURS = range(6, 21)  # 6 am through 8 pm
HEAT_LEVELS = (  # (heat index °F from, level, what it means: the NWS's words)
    (125, "extreme danger", "heat stroke is highly likely"),
    (103, "danger", "heat cramps or heat exhaustion are likely, and heat stroke is possible with long exposure"),
    (90, "extreme caution", "heat cramps or heat exhaustion are possible with long exposure and hard work"),
    (80, "caution", "fatigue is possible with long exposure and hard work"),
)
FROSTBITE = ((-48, 5), (-33, 10), (-18, 30))  # (wind chill °F at or below, minutes to frostbite on bare skin)


def heat_index(t_f: float, rh: float) -> float:
    """Pure logic. The NWS heat index (°F) for an air temperature (°F) and relative humidity (%)."""
    simple = 0.5 * (t_f + 61.0 + (t_f - 68.0) * 1.2 + rh * 0.094)
    if (simple + t_f) / 2 < 80:
        return simple
    hi = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh - 0.22475541 * t_f * rh - 0.00683783 * t_f * t_f
          - 0.05481717 * rh * rh + 0.00122874 * t_f * t_f * rh + 0.00085282 * t_f * rh * rh
          - 0.00000199 * t_f * t_f * rh * rh)
    if rh < 13 and 80 <= t_f <= 112:
        hi -= ((13 - rh) / 4) * math.sqrt((17 - abs(t_f - 95)) / 17)
    elif rh > 85 and 80 <= t_f <= 87:
        hi += ((rh - 85) / 10) * ((87 - t_f) / 5)
    return hi


def wind_chill(t_f: float, mph: float) -> Optional[float]:
    """Pure logic. The NWS wind chill (°F), or None when it doesn't apply (air above 50 °F, or wind 3 mph or less)."""
    if t_f > 50 or mph <= 3:
        return None
    v = mph ** 0.16
    return 35.74 + 0.6215 * t_f - 35.75 * v + 0.4275 * t_f * v


def _to_f(value: float, metric: bool) -> float:
    """Pure logic. °C to °F when the forecast is metric."""
    return value * 9 / 5 + 32 if metric else value


def _from_f(value: float, metric: bool) -> int:
    """Pure logic. °F back to his unit, rounded."""
    return round((value - 32) * 5 / 9) if metric else round(value)


def _clock(hour: int) -> str:
    """Pure logic. 15 -> "3 pm", 0 -> "midnight", 12 -> "noon"."""
    return "noon" if hour == 12 else "midnight" if hour in (0, 24) else f"{hour % 12} {'am' if hour < 12 else 'pm'}"


def day_hours(forecast: dict, iso: str) -> list[dict]:
    """Pure logic. The working day's hours of that date: each {hour, heat (°F), chill (°F or None), temp (°F)}."""
    metric = "C" in str((forecast or {}).get("unit", ""))
    out = []
    for h in (forecast or {}).get("hours") or []:
        when = str(h.get("time", ""))
        try:
            hour = int(when[11:13])
        except ValueError:
            continue
        if not when.startswith(iso) or hour not in DAY_HOURS or h.get("temp") is None:
            continue
        t_f = _to_f(float(h["temp"]), metric)
        mph = float(h.get("wind") or 0) / (1.609344 if metric else 1)
        heat = heat_index(t_f, float(h["rh"])) if h.get("rh") is not None else t_f
        out.append({"hour": hour, "temp": t_f, "heat": heat, "chill": wind_chill(t_f, mph)})
    return out


def heat_level(index_f: float) -> Optional[tuple]:
    """Pure logic. The NWS level (level, meaning) for a heat index in °F, or None under 80."""
    return next(((lvl, words) for start, lvl, words in HEAT_LEVELS if index_f >= start), None)


def cool_hours(hours: list[dict], limit: float = 90) -> str:
    """Pure logic. When the heat index is under `limit`: "before 10 am and after 7 pm", "until 11 am", "after 6 pm",
    or "" when no working hour is."""
    cool = [h["hour"] for h in hours if h["heat"] < limit]
    if not cool:
        return ""
    first, last = hours[0]["hour"], hours[-1]["hour"]
    morning = [h for h in cool if h == first + cool.index(h)] if cool[0] == first else []
    evening = []
    for h in reversed(cool):
        if h == last - len(evening):
            evening.insert(0, h)
        else:
            break
    if morning and evening and morning[-1] >= evening[0] - 1:
        return "all day"
    parts = []
    if morning:
        parts.append(f"before {_clock(morning[-1] + 1)}")
    if evening and evening != morning:
        parts.append(f"after {_clock(evening[0])}")
    return " and ".join(parts)


def frostbite_minutes(chill_f: float) -> Optional[int]:
    """Pure logic. Minutes to frostbite on bare skin at a wind chill (°F), from the NWS chart, or None above -18 °F."""
    return next((minutes for at, minutes in FROSTBITE if chill_f <= at), None)


def judge(forecast: dict, iso: str, emergency: str = "911") -> str:
    """Pure logic. The day's answer from its hours (see the module's opening)."""
    metric = "C" in str((forecast or {}).get("unit", ""))
    sign = "°C" if metric else "°F"
    hours = day_hours(forecast, iso)
    if not hours:
        return ""
    hot = max(hours, key=lambda h: h["heat"])
    chills = [h for h in hours if h["chill"] is not None]
    cold = min(chills, key=lambda h: h["chill"]) if chills else None
    if hot["heat"] >= 80:
        level, words = heat_level(hot["heat"])
        out = (f"The heat index reaches about {_from_f(hot['heat'], metric)}{sign} around {_clock(hot['hour'])}: "
               f"{level}, {words}.")
        if hot["heat"] >= 90:
            when = cool_hours(hours)
            out += (f" Do the heavy work {when}, when it's under {_from_f(90, metric)}{sign}." if when else
                    " No working hour is under " + f"{_from_f(90, metric)}{sign}, so keep the heavy work short.")
            out += (" Drink a cup of water every 15 to 20 minutes even if you aren't thirsty, and rest in the shade. "
                    f"Confusion, slurred speech or hot skin that stops sweating is heat stroke: call {emergency} and "
                    "cool down at once.")
        else:
            out += " Fine for work: take water and breaks."
        return out
    if cold is not None and cold["chill"] <= 32:
        warm = max(hours, key=lambda h: h["temp"])
        out = (f"The wind chill gets down to about {_from_f(cold['chill'], metric)}{sign} around "
               f"{_clock(cold['hour'])}.")
        minutes = frostbite_minutes(cold["chill"])
        if minutes:
            out += (f" Frostbite can set in on bare skin in about {minutes} minutes: cover your face, ears and hands, "
                    "and keep the time outside short.")
        else:
            out += " Dress in layers, keep dry, and cover your ears and hands."
        return out + f" The warmest hour is around {_clock(warm['hour'])}."
    lo, hi = min(h["temp"] for h in hours), max(h["temp"] for h in hours)
    return (f"Good for working outside: {_from_f(lo, metric)} to {_from_f(hi, metric)}{sign} through the day, no heat "
            "or wind chill to worry about.")


def say(context, day: str = "today", fetch=None) -> str:
    """The answer for today or tomorrow, from the forecast kept for his town, found by its date (a forecast that
    doesn't reach it says so, never yesterday's hours as today's)."""
    from core import region, weather

    got = weather.card(context, fetch)
    if got.get("set"):
        return "I don't know your town yet. Tell me which one, like \"my town is Springfield, Illinois\"."
    if got.get("loading") or not got.get("days"):
        return f"I'm getting the forecast for {got.get('place') or 'your town'}; ask me again in a moment."
    tomorrow = str(day or "").strip().lower().startswith("tom")
    wanted = (date.today() + timedelta(days=1 if tomorrow else 0)).isoformat()
    if not any(d.get("date") == wanted for d in got["days"]):  # a stale forecast kept while offline (review 2026-11-24)
        return (f"The forecast I have doesn't reach {'tomorrow' if tomorrow else 'today'} yet; ask me again when "
                "I'm back online.")
    iso = wanted
    said = judge(got, iso, region.region_for(context).emergency)
    if not said:
        return "The forecast I have doesn't give that day's hours; ask me again in a moment."
    return ("Tomorrow: " if tomorrow else "Today: ") + said


def _tool(context, arguments: dict) -> str:
    """Tool work_outside_wind_chill_heat_index: `say` for the day he asked about."""
    return say(context, str(arguments.get("day", "") or "today"))


def register_outdoor_work_actions(registry) -> None:
    """Registers work_outside_wind_chill_heat_index."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="work_outside_wind_chill_heat_index", domain="today",
        description="The wind chill or heat index today or tomorrow, and whether it's safe to work outside in the "
                    "heat or cold (on the roof, cutting wood, in the garden): the risk level through the working day "
                    "from the hourly forecast, the cooler or warmer hours for the heavy work, and frostbite or "
                    "heat-stroke warnings. The plain forecast is get_weather; storms are storm_ready.",
        parameters={"type": "object", "properties": {
            "day": {"type": "string", "description": "today or tomorrow"}}},
        handler=_tool, trigger_phrases=("work outside", "working outside", "too hot to work", "too cold to work",
                                        "heat index", "wind chill", "heat stroke", "frostbite", "too hot outside",
                                        "too cold outside", "safe to work out", "hot to be outside",
                                        "cold to be outside", "in this heat", "in the heat", "in this cold",
                                        "in the cold", "heat advisory"),
    ))
