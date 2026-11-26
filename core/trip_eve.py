"""
core.trip_eve
===============

"Before you go" (brainstorm round 16, 2026-11-25): the afternoon before a planned trip (core/trip_manager.py, a
trip starting tomorrow and still planned), one message through the gate: what on its packing list isn't packed yet,
tomorrow's forecast here (core/weather.card: his town, not the trip's), and the few checks for that kind of trip,
with the one that matters on every trip first: tell someone where you're going and when you'll be back. A market day
has its own day-before message (core/market_eve.py).

`plan(context, today)` gives the trips and their lists; `say` words them for "what do I need for my trip?" (asked
the morning of, today's trip; else tomorrow's; else the next one planned); `offer(context, now)` is the daily check
`trip_eve`, from EVENING_HOUR on, TIMELY, once per trip and start date (moved, it's said again), waiting while the
forecast is first being fetched, and ending at midnight so a held one never arrives on the day saying "tomorrow"
(the Fable review, 2026-11-25). Read only.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

EVENING_HOUR = 15  # from mid-afternoon: time left to pack and buy
SHOWN = 8
ALWAYS = "Tell someone where you're going and when you'll be back"
CHECKS = {
    "Hiking": ("water and a way to treat more", "a map that works without a signal", "a headlamp", "first aid"),
    "Camping": ("water and a way to treat more", "a headlamp and spare batteries", "fire starting kit", "first aid"),
    "Fishing": ("your fishing license", "the regulations for that water", "water", "a life jacket if you'll be in a "
                "boat", "first aid"),
    "Kayaking": ("a life jacket you'll wear", "water", "a dry bag for your phone", "the water's level and wind",
                 "first aid"),
    "Biking": ("a helmet", "a spare tube and pump", "lights", "first aid"),
}


def _trips_on(context, day: date, statuses=("planned",)) -> list:
    """The trips starting on a day with one of these statuses."""
    trips = getattr(context, "trips", None)
    if trips is None:
        return []
    return [t for t in trips.all_trips() if str(t.start_date or "")[:10] == day.isoformat() and t.status in statuses]


def _next_trip(context, today: date):
    """The next planned trip after tomorrow, or None."""
    trips = getattr(context, "trips", None)
    later = sorted((t for t in (trips.all_trips() if trips is not None else [])
                    if t.status == "planned" and str(t.start_date or "")[:10] > (today + timedelta(days=1)).isoformat()),
                   key=lambda t: str(t.start_date))
    return later[0] if later else None


def _found(trip) -> dict:
    """One trip's list: {trip_id, name, start, activity, unpacked, packed, total, checks}."""
    gear = list(trip.gear or [])
    return {"trip_id": trip.trip_id, "name": trip.name, "start": str(trip.start_date or "")[:10],
            "activity": trip.activity_type, "unpacked": [g.label for g in gear if not g.packed and g.label],
            "packed": sum(1 for g in gear if g.packed), "total": len(gear),
            "checks": [ALWAYS] + list(CHECKS.get(trip.activity_type, ("water", "first aid")))}


def plan(context, today: Optional[date] = None) -> list[dict]:
    """[{trip_id, name, start, activity, unpacked: [labels], packed, total, checks: [..]}] for each planned trip
    starting tomorrow."""
    today = today or date.today()
    return [_found(t) for t in _trips_on(context, today + timedelta(days=1))]


def _card(context) -> dict:
    """core/weather.card, or {} when it can't be read."""
    try:
        from core import weather

        return weather.card(context) or {}
    except Exception:  # noqa: BLE001 - the message goes without it
        return {}


def _sky(context, day: str = "tomorrow", got: Optional[dict] = None) -> str:
    """Tomorrow's (or today's) forecast here in a few words, or "" when there's none yet."""
    got = _card(context) if got is None else got
    t = got.get("tomorrow") if day == "tomorrow" else {"high": got.get("high"), "low": got.get("low"),
                                                         "words": got.get("today_words")}
    t = t or {}
    if t.get("high") is None:
        return ""
    unit = got.get("unit", "")
    what = f"{t['words'].lower()}, " if t.get("words") else ""
    rain = f", a {t['rain']}% chance of rain" if t.get("rain") is not None else ""
    return f"{day.capitalize()} here: {what}a high of {t['high']}{unit} and a low of {t['low']}{unit}{rain}."


def words(found: dict, sky: str = "", when: str = "tomorrow") -> str:
    """Pure logic. One trip's "before you go" in a few sentences ("is tomorrow", "is today", "is on Friday")."""
    parts = [f"{found['name']} is {when}."]
    if found["unpacked"]:
        shown = ", ".join(found["unpacked"][:SHOWN]) + (f" and {len(found['unpacked']) - SHOWN} more"
                                                         if len(found["unpacked"]) > SHOWN else "")
        parts.append(f"Not packed yet: {shown}.")
    elif found["total"] and found["packed"] >= found["total"]:
        parts.append("Everything on its packing list is packed.")
    elif found["total"]:
        parts.append(f"{found['packed']} of {found['total']} on its packing list packed.")
    else:
        parts.append("It has no packing list yet: add one on the trip's page.")
    if sky:
        parts.append(sky)
    parts.append("Before you go: " + "; ".join(found["checks"]) + ".")
    return " ".join(parts)


def say(context, today: Optional[date] = None) -> str:
    """For "what do I need for my trip?": a trip starting today (asked the morning of), else tomorrow's, else the
    next one planned; or that there's none."""
    today = today or date.today()
    now = [_found(t) for t in _trips_on(context, today, ("planned", "active"))]
    if now:
        sky = _sky(context, "today")
        return " ".join(words(f, sky, "today") for f in now)
    found = plan(context, today)
    if found:
        sky = _sky(context)
        return " ".join(words(f, sky) for f in found)
    later = _next_trip(context, today)
    if later is not None:
        day = date.fromisoformat(str(later.start_date)[:10])
        return words(_found(later), "", f"on {day:%A, %B} {day.day}")
    return "You don't have a trip planned. Plan one in Expeditions and I'll go over it the day before."


def offer(context, now: datetime) -> list:
    """The daily check's message: from EVENING_HOUR the day before a planned trip, TIMELY, once per trip and start
    date, ending at midnight; nothing while the forecast is first being fetched."""
    from core.communication_gate import TIMELY, Candidate

    if now.hour < EVENING_HOUR:
        return []
    try:
        found = plan(context, now.date())
    except Exception:  # noqa: BLE001 - a trip list that can't be read never breaks the check
        log.exception("Trip eve: the trips couldn't be read")
        return []
    if not found:
        return []
    got = _card(context)
    if got.get("loading"):
        return []  # the forecast is first being fetched: the next tick says it with the weather
    sky = _sky(context, "tomorrow", got)
    ends = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())  # midnight: never "tomorrow" on the day
    return [Candidate(topic="trip_eve", title=f"Tomorrow: {f['name']}", message=words(f, sky), urgency=TIMELY,
                      source="system", fingerprint=f"trip-eve-{f['trip_id']}-{f['start']}",
                      expires=ends.isoformat(timespec="seconds")) for f in found]
