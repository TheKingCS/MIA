"""
core.sun_moon
===============

Sunrise, sunset and the moon's phase for a place and a day, in words (the
Navigation app's summary and the `get_sun_moon_info` tool). Moved here from
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
