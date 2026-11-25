"""
core.fishing_times
====================

"When's the best time to fish?" (Jarvis brainstorm, round 12; fishing is his, docs/VISION.md): the day's (or the
week's) fishing windows for his town (core/weather.place), worked out offline from the sun and the moon (`astral`, as
core/sun_moon.py) and beside what his own catch log says (core/catch_log.biting).

- **Dawn and dusk** (an hour either side of sunrise and sunset): the surest feeding times, said first.
- **The solunar periods** (John Alden Knight's tables, the angler's tradition): the majors, about two hours around the
  moon overhead and underfoot (its highest and lowest, found by its elevation every `STEP_MINUTES`); the minors,
  about an hour around moonrise and moonset. A window that falls on dawn or dusk is said as the best of the day.
- **The moon's phase**: within `PHASE_DAYS` of a new or full moon is the tradition's strongest stretch.
- **The week** (`week`): each of the next seven days scored (a new or full moon, and solunar windows on dawn or dusk),
  the best two said with why.

Said honestly: the solunar idea is tradition with mixed evidence, dawn and dusk are the reliable part, and his own log
outranks both once it has a few catches with times. Times are in the computer's own time zone on each day (a clock change counted), never guessed
from the town. Without a town, he's asked for one.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

STEP_MINUTES = 10
PHASE_DAYS = 2  # days either side of new (0 / 29.5) or full (14.75) that count as the strong stretch
LUNATION = 28.0  # astral's moon.phase scale: 0 new, 14 full, 27.99 the end (its own docs), not the 29.53-day month


def _tz(day: Optional[date] = None):
    """The computer's own time zone on that day (noon's offset, so a clock change between now and then is counted:
    Windows gives a fixed offset for now, review 2026-11-24)."""
    day = day or date.today()
    return datetime(day.year, day.month, day.day, 12).astimezone().tzinfo or timezone.utc


def _sun_times(lat: float, lon: float, day: date, tz) -> dict:
    """{sunrise, sunset} that day, each left out when the sun doesn't rise or set (asked one at a time: astral's
    sun() fails whole when twilight never ends, far north in summer)."""
    from astral import Observer
    from astral.sun import sunrise, sunset

    where, out = Observer(lat, lon), {}
    for name, fn in (("sunrise", sunrise), ("sunset", sunset)):
        try:
            out[name] = fn(where, day, tzinfo=tz)
        except ValueError:
            continue
    return out


def _clock(when: datetime) -> str:
    """Pure logic. "5:40 am", "noon"."""
    if when.hour == 12 and when.minute == 0:
        return "noon"
    return f"{when.hour % 12 or 12}:{when.minute:02d} {'am' if when.hour < 12 else 'pm'}"


def moon_extremes(lat: float, lon: float, day: date, tz) -> dict:
    """The moon's highest (overhead) and lowest (underfoot) times that day: {overhead, underfoot} (datetimes in `tz`).
    astral's moon.elevation reads a time as UTC whatever its zone (seen 2026-11-24: local times gave the moon high at
    its own moonset), so each is converted to UTC first."""
    from astral import Observer, moon

    where = Observer(lat, lon)
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    samples = [(moon.elevation(where, (start + timedelta(minutes=m)).astimezone(timezone.utc)),
                start + timedelta(minutes=m)) for m in range(0, 24 * 60, STEP_MINUTES)]
    return {"overhead": max(samples)[1], "underfoot": min(samples)[1]}


def windows(lat: float, lon: float, day: date, tz=None) -> list[dict]:
    """The day's windows, in time order: each {kind (dawn, dusk, major, minor), what, start, end, on_light (a solunar
    window touching dawn or dusk)}.
    Dawn and dusk come from sunrise and sunset asked separately (`_sun_times`), so far north in summer they're still
    there."""
    from astral import Observer, moon

    tz = tz or _tz(day)
    where = Observer(lat, lon)
    out = []
    s = _sun_times(lat, lon, day, tz)
    for kind, name in (("dawn", "sunrise"), ("dusk", "sunset")):
        if name in s:
            out.append({"kind": kind, "what": kind, "start": s[name] - timedelta(hours=1),
                        "end": s[name] + timedelta(hours=1)})
    peaks = moon_extremes(lat, lon, day, tz)
    out += [{"kind": "major", "what": f"moon {name}", "start": t - timedelta(hours=1), "end": t + timedelta(hours=1)}
            for name, t in peaks.items()]
    for name, fn in (("moonrise", moon.moonrise), ("moonset", moon.moonset)):
        try:
            t = fn(where, day, tz)
        except ValueError:  # the moon doesn't rise or set that day
            continue
        if t is not None and t.date() == day:
            out.append({"kind": "minor", "what": name, "start": t - timedelta(minutes=30),
                        "end": t + timedelta(minutes=30)})
    light = [w for w in out if w["kind"] in ("dawn", "dusk")]
    for w in out:
        w["on_light"] = w["kind"] in ("major", "minor") and any(
            w["start"] < l["end"] and l["start"] < w["end"] for l in light)
    return sorted(out, key=lambda w: w["start"])


def gap(day: date, kind: str) -> float:
    """How far that day's moon is from full or new, on astral's scale (0 new, 14 full, 27.99 the end of the cycle;
    checked: 13.8 on 2026-11-24, that day's full moon)."""
    from astral import moon

    p = moon.phase(day)
    return abs(p - LUNATION / 2) if kind == "full" else min(p, LUNATION - p)


def is_the_day(day: date, kind: str) -> bool:
    """Whether this is the one day the moon is nearest full (or new): nearer than the day before and no further than
    the day after (so two days in a row never both are; review 2026-11-24)."""
    g = gap(day, kind)
    return g < 1.5 and g < gap(day - timedelta(days=1), kind) and g <= gap(day + timedelta(days=1), kind)


def moon_day(day: date, kind: str, ahead: bool) -> Optional[date]:
    """The nearest full (or new) moon day on or after `day` (ahead) or on or before it, within 16 days, or None."""
    for i in range(17):
        when = day + timedelta(days=i if ahead else -i)
        if is_the_day(when, kind):
            return when
    return None


def phase_word(day: date) -> tuple:
    """(words, strong): "a full moon" (only on the day, `is_the_day`), "2 days past the new moon"..., and whether
    it's the strong stretch (within PHASE_DAYS of one). The same rule as core/sun_moon.next_moons."""
    best = None
    for kind in ("full", "new"):
        for ahead in (True, False):
            when = moon_day(day, kind, ahead)
            if when is not None and (best is None or abs((when - day).days) < abs((best[1] - day).days)):
                best = (kind, when)
    if best is None:
        return "the moon between phases", False
    kind, when = best
    days = (when - day).days
    if days == 0:
        return f"a {kind} moon", True
    side = "before" if days > 0 else "past"
    n = abs(days)
    return f"{n} day{'s' if n != 1 else ''} {side} the {kind} moon", n <= PHASE_DAYS


def score(lat: float, lon: float, day: date, tz=None) -> tuple:
    """(score, why) for a day: 2 for the strong stretch of the moon, 1 for each solunar window on dawn or dusk."""
    words, strong = phase_word(day)
    on_light = [w for w in windows(lat, lon, day, tz) if w["on_light"]]
    why = ([words] if strong else []) + [f"the {w['what']} lines up with {_light_of(w, day, lat, lon, tz)}"
                                         for w in on_light]
    return (2 if strong else 0) + len(on_light), why


def _light_of(w: dict, day: date, lat: float, lon: float, tz) -> str:
    """Pure-ish. Whether a window touches dawn or dusk (by its hour)."""
    return "dawn" if w["start"].hour < 12 else "dusk"


def _say_day(found: list[dict], day: date) -> str:
    """Pure logic. The day's windows in words, the best first (each window said once)."""
    best = [w for w in found if w["on_light"]]
    light = [w for w in found if w["kind"] in ("dawn", "dusk")]
    out = []
    if best:
        out.append("Best, where the moon lines up with dawn or dusk: " + "; ".join(
            f"{_clock(w['start'])} to {_clock(w['end'])} ({w['what']})" for w in best) + ".")
    if light:
        out.append("Dawn and dusk: " + " and ".join(f"{_clock(w['start'])} to {_clock(w['end'])}" for w in light)
                   + ".")
    majors = [w for w in found if w["kind"] == "major" and not w["on_light"]]
    minors = [w for w in found if w["kind"] == "minor" and not w["on_light"]]
    if majors:
        out.append(("Other major periods: " if best else "Major periods: ") + ", ".join(f"{_clock(w['start'])} to {_clock(w['end'])} ({w['what']})"
                                                 for w in majors) + ".")
    if minors:
        out.append(("Other minor: " if best else "Minor: ") + ", ".join(f"{_clock(w['start'])} to {_clock(w['end'])} ({w['what']})"
                                         for w in minors) + ".")
    return " ".join(out)


def _his_log(context) -> str:
    """What his own catches say about the time of day, once there are three with times; "" before."""
    try:
        from core.catch_log import biting, catches

        found = biting(catches(context))
    except Exception:  # noqa: BLE001 - a log that can't be read leaves it out
        return ""
    if found.get("hour") and found["total"] >= 3:
        return f" Your own log says {found['hour'][0]} has been your best time ({found['hour'][1]} fish): trust that first."
    return ""


HONEST = (" The solunar periods are an old angler's tradition with mixed evidence; dawn and dusk are the reliable "
          "part.")


def say(context, when: str = "today", today: Optional[date] = None, tz=None) -> str:
    """The answer for today, tomorrow or the week (see the module's opening).
    Each day's times use that day's own offset (`_tz(day)`), so a week across a clock change is right."""
    from core import weather

    where = weather.place(context)
    if where is None:
        return "I don't know your town yet. Tell me which one, like \"my town is Springfield, Illinois\"."
    today = today or date.today()
    when = str(when or "today").strip().lower()
    lat, lon = where["lat"], where["lon"]
    if "week" in when or "weekend" in when:
        days = [today + timedelta(days=i) for i in range(7)]
        if "weekend" in when:
            days = [d for d in days if d.weekday() >= 5] or days
        scored = sorted(((score(lat, lon, d, tz), d) for d in days), key=lambda x: (-x[0][0], x[1]))
        top = [(s, d) for s, d in scored if s[0] > 0][:2] or scored[:1]
        best_day = top[0][1]
        if top[0][0][0] == 0:
            head = (f"Nothing stands out from the moon {'this weekend' if 'weekend' in when else 'this week'}, so "
                    f"go at dawn or dusk. {best_day.strftime('%A')}: ")
        else:
            head = "The best days: " + "; ".join(f"{d.strftime('%A')}, {', '.join(s[1])}" for s, d in top) + (
                f". {best_day.strftime('%A')}: ")
        return head + _say_day(windows(lat, lon, best_day, tz), best_day) + _his_log(context) + HONEST
    day = today + timedelta(days=1) if when.startswith("tom") else today
    words, strong = phase_word(day)
    head = f"{'Tomorrow' if day != today else 'Today'} in {where['name'] or 'your town'}, with {words}" + (
        " (the strong stretch)" if strong else "") + ": "
    return head + _say_day(windows(lat, lon, day, tz), day) + _his_log(context) + HONEST


def _tool(context, arguments: dict) -> str:
    """Tool best_time_to_fish: `say` for the day or week he asked about."""
    return say(context, str(arguments.get("when", "") or "today"))


def register_fishing_times_actions(registry) -> None:
    """Registers best_time_to_fish (offered by the fishing words, core/catch_actions.FISH_WORDS)."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="best_time_to_fish", domain="expeditions",
        description="When to go fishing today, tomorrow or this week: dawn and dusk, the solunar major and minor "
                    "periods from the moon, the moon's phase, and the best days of the week. What his own catch log "
                    "says is whats_biting.",
        parameters={"type": "object", "properties": {
            "when": {"type": "string", "description": "today, tomorrow, this week or this weekend"}}},
        handler=_tool, trigger_phrases=("best time to fish", "best time to go fishing", "solunar", "when should i fish",
                                        "good day to fish", "good day for fishing", "fishing times",
                                        "fish be biting", "fish biting today", "fish biting tomorrow"),
    ))
