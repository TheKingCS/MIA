"""
core.trip_eve
===============

"Before you go" (brainstorm round 16, 2026-11-25): the afternoon before a planned trip (core/trip_manager.py, a
trip starting tomorrow and still planned), one message through the gate: what on its packing list isn't packed yet,
tomorrow's forecast here (core/weather.card: his town, not the trip's), and the few checks for that kind of trip,
with the one that matters on every trip first: tell someone where you're going and when you'll be back. A market day
has its own day-before message (core/market_eve.py).

`plan(context, today)` gives the trips and their lists; `say` words them for "what do I need for my trip?";
`offer(context, now)` is the daily check `trip_eve`, from EVENING_HOUR on, TIMELY, once per trip. Read only.
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
    "Fishing": ("your fishing license", "the regulations for that water", "sunscreen", "first aid"),
    "Kayaking": ("a life jacket you'll wear", "a dry bag for your phone", "the water's level and wind", "first aid"),
    "Biking": ("a helmet", "a spare tube and pump", "lights", "first aid"),
}


def _tomorrows_trips(context, today: date) -> list:
    """The trips starting tomorrow that are still planned."""
    trips = getattr(context, "trips", None)
    if trips is None:
        return []
    tomorrow = (today + timedelta(days=1)).isoformat()
    return [t for t in trips.all_trips() if str(t.start_date or "")[:10] == tomorrow and t.status == "planned"]


def plan(context, today: Optional[date] = None) -> list[dict]:
    """[{trip_id, name, activity, unpacked: [labels], packed, total, checks: [..]}] for each trip starting tomorrow."""
    today = today or date.today()
    out = []
    for trip in _tomorrows_trips(context, today):
        gear = list(trip.gear or [])
        out.append({"trip_id": trip.trip_id, "name": trip.name, "activity": trip.activity_type,
                    "unpacked": [g.label for g in gear if not g.packed and g.label],
                    "packed": sum(1 for g in gear if g.packed), "total": len(gear),
                    "checks": [ALWAYS] + list(CHECKS.get(trip.activity_type, ("water", "first aid")))})
    return out


def _sky(context) -> str:
    """Tomorrow's forecast here in a few words, or "" when there's none yet."""
    try:
        from core import weather

        got = weather.card(context)
    except Exception:  # noqa: BLE001 - the message goes without it
        return ""
    t = (got or {}).get("tomorrow") or {}
    if not t or t.get("high") is None:
        return ""
    unit = got.get("unit", "")
    rain = f", a {t['rain']}% chance of rain" if t.get("rain") is not None else ""
    return f"Tomorrow here: {t.get('words') or 'the forecast'}, {t['high']}{unit} and {t['low']}{unit}{rain}."


def words(found: dict, sky: str = "") -> str:
    """Pure logic. One trip's "before you go" in a few sentences."""
    parts = [f"{found['name']} is tomorrow."]
    if found["unpacked"]:
        shown = ", ".join(found["unpacked"][:SHOWN]) + (f" and {len(found['unpacked']) - SHOWN} more"
                                                         if len(found["unpacked"]) > SHOWN else "")
        parts.append(f"Not packed yet: {shown}.")
    elif found["total"]:
        parts.append("Everything on its packing list is packed.")
    else:
        parts.append("It has no packing list yet: add one on the trip's page.")
    if sky:
        parts.append(sky)
    parts.append("Before you go: " + "; ".join(found["checks"]) + ".")
    return " ".join(parts)


def say(context, today: Optional[date] = None) -> str:
    """For "what do I need for my trip?": each trip starting tomorrow, or that there's none."""
    found = plan(context, today)
    if not found:
        return "You don't have a trip starting tomorrow. Plan one in Expeditions and I'll go over it the day before."
    sky = _sky(context)
    return " ".join(words(f, sky) for f in found)


def offer(context, now: datetime) -> list:
    """The daily check's message: from EVENING_HOUR the day before a planned trip, TIMELY, once per trip, ending at
    the trip's own start."""
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
    sky = _sky(context)
    ends = (datetime.combine(now.date() + timedelta(days=1), datetime.min.time()) + timedelta(hours=12))
    return [Candidate(topic="trip_eve", title=f"Tomorrow: {f['name']}", message=words(f, sky), urgency=TIMELY,
                      source="system", fingerprint=f"trip-eve-{f['trip_id']}",
                      expires=ends.isoformat(timespec="seconds")) for f in found]
