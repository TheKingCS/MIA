"""
core.water_budget
===================

The whole property's water (Zac, 2026-11-24: "will manage ... my water systems"; docs/future/SMART_AG_PLAN.md phase
A2): what the place drinks a day and a month, what's stored, and what the roof brings in, from his own records.

**What it uses** (`uses`), each from a record and said with where it came from:
- the house: the people he plans for (`prepared.people`) at about 80 gallons a person a day (a US household's usual,
  an estimate he can beat);
- the garden: the beds of his confirmed garden plans (core/project_plans.py), an inch a week over their square feet;
- the orchard: his fruit trees (core/orchard.py) at about 10 gallons a tree a week in the growing season;
- the flock: his hens (core/flock.py) at about a pint a hen a day;
- the greenhouse: not counted until the node reports its top-ups (an aquaponics system loses 1 to 3% of its volume a
  day), said as missing.

**What's stored** (`stored`): every tank, cistern or barrel he logs a level for ("the cistern is at 800 gallons": the
tool `log_water_level`, kept in the data logger as `water:<name>`), each at its latest reading and its date.

**What comes in**: the roof he catches from (`water.roof_sqft`, set by voice) against his rain gauge's last 30 days
(core/rain_catchment.py).

Then the days the stored water carries the outdoor uses and the animals (the house is often on a well or the town's
water; with no other source it's said with the house too). Every estimate is marked as one. Read-only, but for the
level he logs.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

HOUSE_GAL_A_PERSON_DAY = 80.0
TREE_GAL_A_WEEK = 10.0
HEN_GAL_A_DAY = 0.125
SERIES = "water:"  # the data logger series a tank's levels are kept in: water:<tank>


def tank_series(name: str) -> str:
    """Pure logic. The data logger series a tank's level goes in ("The Cistern" is water:the cistern... minus the
    article): water:cistern."""
    words = [w for w in str(name or "").lower().split() if w not in ("the", "my", "our", "a")]
    return SERIES + " ".join(words)


def uses(context) -> list[dict]:
    """What the place drinks: [{use, gal_day, how}] for each use his records show; the greenhouse as missing."""
    from core import person_settings

    out = []
    try:
        people = max(1, int(person_settings.get(context, "prepared.people", 1) or 1))
    except (TypeError, ValueError, AttributeError):
        people = 1
    out.append({"use": "the house", "gal_day": people * HOUSE_GAL_A_PERSON_DAY,
                "how": f"{people} {'person' if people == 1 else 'people'} at about {HOUSE_GAL_A_PERSON_DAY:g} gallons "
                       "a day each (a usual household; an estimate)"})
    book = getattr(context, "project_plans", None)
    sqft = 0.0
    for plan in (book.listed() if book is not None else []):
        if plan.kind == "garden" and plan.status == "confirmed":
            sqft += sum(float(b.get("length_ft") or 0) * float(b.get("width_ft") or 0) for b in plan.beds or [])
    if sqft:
        out.append({"use": "the garden", "gal_day": round(sqft * 0.623 / 7, 1),
                    "how": f"{sqft:g} square feet of beds at an inch a week (in the growing season)"})
    try:
        from core.orchard import trees

        count = sum(t["count"] for t in trees(context))
    except Exception:  # noqa: BLE001 - the orchard is one line
        log.exception("The water budget couldn't read the orchard")
        count = 0
    if count:
        out.append({"use": "the orchard", "gal_day": round(count * TREE_GAL_A_WEEK / 7, 1),
                    "how": f"{count} fruit tree{'s' if count != 1 else ''} at about {TREE_GAL_A_WEEK:g} gallons a "
                           "week each in the growing season (an estimate; young trees and sandy soil take more)"})
    flock = getattr(context, "flock", None)
    hens = sum(max(0, int(f.hens)) for f in (getattr(flock, "flocks", None) or []))
    if hens:
        out.append({"use": "the flock", "gal_day": round(hens * HEN_GAL_A_DAY, 1),
                    "how": f"{hens} hens at about a pint a hen a day (more in heat)"})
    return out


def stored(context) -> list[dict]:
    """Each tank he logs: [{tank, gallons, on}] at its latest reading; [] without the data logger or levels."""
    logger = getattr(context, "data_logger", None)
    if logger is None:
        return []
    out = []
    for series in logger.list_series():
        if not str(series).startswith(SERIES):
            continue
        readings = logger.readings_for(series)
        if readings:
            last = readings[-1]
            out.append({"tank": series[len(SERIES):], "gallons": float(last.value), "on": str(last.timestamp)[:10]})
    return out


# Tanks that aren't the property's stored water
_NOT_WATER = re.compile(r"\b(propane|gas|gasoline|fuel|diesel|oil|kerosene|fish|aquarium|aquaponics|hot water|"
                        r"water heater|septic|pool)\b", re.I)


def log_level(context, tank: str, gallons) -> str:
    """Keeps a tank's level as he said it (the data logger, `water:<tank>`), undoable; says it back. A fuel, fish,
    hot water or septic tank isn't stored water: turned away (`_NOT_WATER`)."""
    logger = getattr(context, "data_logger", None)
    name = " ".join(str(tank or "").split())
    if logger is None:
        return "The data logger isn't on this MIA, so I can't keep tank levels here."
    if not name:
        return "Which tank or cistern?"
    if _NOT_WATER.search(name):
        return f"The {name} isn't stored water, so I don't keep it in the water budget."
    try:
        value = float(gallons)
    except (TypeError, ValueError):
        return f"How many gallons are in the {name}?"
    if value < 0:
        return "A tank can't hold less than nothing."
    logger.add_reading(tank_series(name), value, unit="gal", note="said")
    return f"Logged: the {tank_series(name)[len(SERIES):]} is at {value:g} gallons."


def say(context, today: Optional[date] = None) -> str:
    """The water budget in words: each use a day, the total a day and a month, what's stored and when it was read,
    what the roof brought in the last 30 days, and how many days the stored water carries the outdoor uses."""
    from core import person_settings

    today = today or date.today()
    used = uses(context)
    parts = ["A day: " + "; ".join(f"{u['use']} about {u['gal_day']:g} gallons ({u['how']})" for u in used) + "."]
    total = sum(u["gal_day"] for u in used)
    parts.append(f"About {total:g} gallons a day in all, {total * 30:,.0f} a month, if every use runs at once.")
    parts.append("The greenhouse isn't counted: its top-ups aren't reported yet (an aquaponics system loses about 1 to "
                 "3% of its volume a day).")
    tanks = stored(context)
    if tanks:
        held = sum(t["gallons"] for t in tanks)
        parts.append("Stored: " + "; ".join(f"the {t['tank']} {t['gallons']:g} gallons (read {t['on']})"
                                            for t in tanks) + ".")
        outdoor = sum(u["gal_day"] for u in used if u["use"] != "the house")
        if outdoor:
            parts.append(f"That carries the garden, orchard and animals about {held / outdoor:.0f} days with no rain; "
                         f"with the house on it too, about {held / total:.0f}.")
        else:
            parts.append(f"With the house on it, about {held / total:.0f} days.")
    else:
        parts.append("No tank levels logged: say \"the cistern is at 800 gallons\" and I'll keep it.")
    roof = person_settings.get(context, "water.roof_sqft", 0) if getattr(context, "config", None) is not None else 0
    if roof:
        from core.rain_catchment import _rain_30, gallons

        rain = _rain_30(context, today)
        if rain is not None:
            parts.append(f"Your {float(roof):g} square foot roof caught about {gallons(float(roof), rain):g} gallons "
                         f"from the {rain:g} inches logged in the last 30 days.")
    else:
        parts.append("No catchment roof set: tell me its size (\"my catchment roof is 600 square feet\").")
    return " ".join(parts)
