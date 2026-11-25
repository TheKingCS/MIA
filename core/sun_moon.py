"""
core.sun_moon
===============

Sunrise, sunset and the moon's phase for a place and a day, in words (the
Navigation app's summary and the `get_sun_moon_info` tool), and the moon tonight in words (`moon_tonight`: how many
days to the full or new moon, core/fishing_times.phase_word, and its rise and set). Moved here from
`modules/navigation/module.py` on 2026-11-15 so the tool works without the
desktop's Qt screens (the MIA Runtime, DEC-0155). Pure formatting over
`astral`; nothing is stored.
"""

from __future__ import annotations

from datetime import date

from astral import Observer
from astral import moon as astral_moon
from astral.sun import sun as astral_sun


def format_moon_phase_name(phase: float) -> str:
    """
    astral.moon.phase() returns 0-27.99 (days into the ~29.5-day
    synodic month), documented by astral itself as exactly these four
    buckets — matched here as-is rather than inventing a finer 8-phase
    scale the underlying calculation doesn't actually support:
    0-6.99 New moon, 7-13.99 First quarter, 14-20.99 Full moon,
    21-27.99 Last quarter.
    """
    if phase < 7:
        return "New Moon"
    if phase < 14:
        return "First Quarter"
    if phase < 21:
        return "Full Moon"
    return "Last Quarter"


def moon_tonight(latitude: float, longitude: float, for_date: date, tz=None) -> str:
    """The moon for a day in words: "Moon: 1 day before the full moon; rises 4:24 pm, sets 7:07 am. Next full moon:
    Wednesday, November 25; next new moon: ..." (a rise or set the moon doesn't make that day is left out; `next_moons`).
    Times in the computer's own zone."""
    from datetime import datetime

    from core.fishing_times import _clock, phase_word

    tz = tz or datetime.now().astimezone().tzinfo
    where = Observer(latitude=latitude, longitude=longitude)
    words, _strong = phase_word(for_date)
    times = []
    for label, fn in (("rises", astral_moon.moonrise), ("sets", astral_moon.moonset)):
        try:
            when = fn(where, for_date, tz)
        except ValueError:
            continue
        if when is not None:
            times.append(f"{label} {_clock(when)}")
    ahead = next_moons(for_date)
    nexts = "; ".join(f"{kind} moon today" if when == for_date else
                      f"next {kind} moon around {when.strftime('%A, %B')} {when.day}" for kind, when in ahead)
    return f"Moon: {words}" + (f"; {', '.join(times)}" if times else "") + "." + (
        f" {nexts[0].upper()}{nexts[1:]}." if nexts else "")


def next_moons(for_date: date) -> list:
    """The next full and new moon on or after a day, soonest first: [(kind, date)], each the day the moon is nearest
    it (core/fishing_times.phase_word's "a full moon")."""
    from datetime import timedelta

    from core.fishing_times import LUNATION

    days = [for_date + timedelta(days=i) for i in range(32)]
    out = []
    for kind in ("full", "new"):
        gaps = []
        for day in days:
            p = astral_moon.phase(day)
            gaps.append(abs(p - LUNATION / 2) if kind == "full" else min(p, LUNATION - p))
        # the first day at its nearest: a gap no larger than the days either side (today counts when it's nearest)
        for i, gap in enumerate(gaps[:-1]):
            if gap < 1.5 and gap <= gaps[i + 1] and (i == 0 or gap <= gaps[i - 1]):
                out.append((kind, days[i]))
                break
    return sorted(out, key=lambda kv: kv[1])


def format_sun_moon_summary(latitude: float, longitude: float, for_date: date) -> str:
    """Pure formatting logic (astral calls only, no Qt) — testable, see tests/test_navigation_module.py."""
    observer = Observer(latitude=latitude, longitude=longitude)
    try:
        sun_times = astral_sun(observer, date=for_date)
    except ValueError as exc:
        # astral raises ValueError for latitudes with no sunrise/sunset
        # on a given date (inside the polar circles) — a real, not
        # hypothetical, edge case for a "survival/field device" tool.
        return f"Sun times unavailable for this location/date: {exc}"

    sunrise_local = sun_times["sunrise"].astimezone()
    sunset_local = sun_times["sunset"].astimezone()
    phase = astral_moon.phase(for_date)

    return "\n".join([
        f"Sunrise: {sunrise_local.strftime('%H:%M')}",
        f"Sunset: {sunset_local.strftime('%H:%M')}",
        f"Moon phase: {format_moon_phase_name(phase)}",
    ])
