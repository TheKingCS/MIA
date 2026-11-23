"""
core.preparedness
===================

How ready he is if things go wrong (Jarvis brainstorm 4.3, first part; Zac, 2026-11-23: "survival skills, homestead
skills ... offline"), worked out in code from his own pantry (core/kitchen_manager.py), never guessed:

- **Water** (`water_days`): the drinking water he's logged in the pantry (an item named water and meant for drinking,
  `is_drinking_water`: not coconut or tonic water, a water filter or a canner; in gallons, liters, quarts, ounces or
  containers of a stated size: "16.9 fl oz bottles", "5-gallon jugs") against the Red Cross and FEMA guide of one gallon a person a day, for the
  people he says (`prepared.people`, 1 unless he says otherwise; said in the answer). Against his target of days
  (`prepared.target_days`, 14 unless set: FEMA's two weeks at home).
- **Rotate** (`rotate`): what's in the pantry and expires in the next ROTATE_DAYS days, soonest first, so it's eaten
  instead of thrown out.
- **Not counted** (said plainly): days of food need what each item feeds, which the pantry doesn't hold yet; power
  needs his batteries and generator. Both wait for him (brainstorm 4.1, 4.3).

`say(context)` answers "how prepared am I?" / "how many days of water do I have?".
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

GALLON_A_DAY = 1.0  # a person, drinking and a little washing (Red Cross, FEMA)
TARGET_DAYS = 14
ROTATE_DAYS = 30
TO_GALLONS = {"gallon": 1.0, "gallons": 1.0, "gal": 1.0, "liter": 0.264172, "liters": 0.264172, "litre": 0.264172,
              "litres": 0.264172, "l": 0.264172, "quart": 0.25, "quarts": 0.25, "qt": 0.25, "oz": 1 / 128,
              "fl oz": 1 / 128, "floz": 1 / 128, "ounce": 1 / 128, "ounces": 1 / 128, "ml": 0.000264172,
              "cup": 1 / 16, "cups": 1 / 16, "pint": 0.125, "pints": 0.125}
# A container's size in its name or unit: "16.9 fl oz bottles", "5-gallon jugs", "1 gal jug", "water 5 gal".
_SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(fl\.?\s*oz|oz|ounces?|ml|liters?|litres?|l|gal(?:lons?)?|quarts?|qt)\b",
                   re.I)
# Not water you drink, though the name says water.
_NOT_DRINKING = ("chestnut", "cress", "melon", "softener", "heater", "coconut", "tonic", "rose water", "rosewater",
                 "filter", "canner", "bath", "pitcher", "hose", "pump", "kefir", "bottle opener", "repellent")
# A unit that's a container of some size: worth asking for the size when it isn't given.
_CONTAINER = re.compile(r"\b(?:bottles?|jugs?|cases?|packs?|cans?|totes?|barrels?|drums?|containers?|jerry ?cans?)\b"
                        r"|^$", re.I)


def gallons_of(item) -> Optional[float]:
    """Pure logic. How many gallons of drinking water a pantry item holds, or None when it isn't drinking water or
    its unit can't be read ("24 bottles" needs the bottle's size: "16.9 fl oz bottles", "5-gallon jugs")."""
    if not is_drinking_water(item):
        return None
    name = str(getattr(item, "name", "")).lower()
    qty = float(getattr(item, "quantity", 0) or 0)
    unit = " ".join(re.sub(r"\.(?!\d)", " ", str(getattr(item, "unit", "")).lower()).split())  # "gal." not "16.9"
    if unit in TO_GALLONS:
        return qty * TO_GALLONS[unit]
    size = _SIZE.search(f"{name} {unit}")
    if size:
        what = size.group(2).lower().replace(".", "").replace(" ", "")
        what = "fl oz" if what == "floz" else what
        factor = TO_GALLONS.get(what) or TO_GALLONS.get(what.rstrip("s")) or (1.0 if what.startswith("gal") else None)
        return qty * float(size.group(1)) * factor if factor else None
    return None


def is_drinking_water(item) -> bool:
    """Pure logic. Whether a pantry item is water to drink (named water, and none of `_NOT_DRINKING`)."""
    name = str(getattr(item, "name", "")).lower()
    return "water" in name and not any(w in name for w in _NOT_DRINKING)


def water_days(items: list, people: int) -> tuple[float, list]:
    """Pure logic. (days of water for that many people, the drinking water in containers whose size it couldn't
    read)."""
    total, unread = 0.0, []
    for item in items:
        got = gallons_of(item)
        if got is None:
            if is_drinking_water(item) and _CONTAINER.search(str(getattr(item, "unit", "")).strip().lower()):
                unread.append(item.name)  # water in containers of an unknown size: ask for it
            continue
        total += got
    return round(total / (GALLON_A_DAY * max(1, people)), 1), unread


def rotate(items: list, today: date, days: int = ROTATE_DAYS) -> list[tuple[str, date]]:
    """Pure logic. Pantry items expiring from today to `days` out, soonest first: (name, date)."""
    out = []
    for item in items:
        try:
            when = date.fromisoformat(str(getattr(item, "expiration_date", ""))[:10])
        except ValueError:
            continue
        if today <= when <= today + timedelta(days=days):
            out.append((item.name, when))
    return sorted(out, key=lambda x: x[1])


def _setting(context, key: str, default: int) -> int:
    """A whole-number setting of his, or the default."""
    try:
        from core import person_settings

        return max(1, int(person_settings.get(context, key, default) or default))
    except (TypeError, ValueError, AttributeError):
        return default


def say(context, today: Optional[date] = None) -> str:
    """For "how prepared am I?": water against his target, what to rotate, and what isn't counted yet."""
    today = today or date.today()
    kitchen = getattr(context, "kitchen", None)
    items = kitchen.all_pantry_items() if kitchen is not None else []
    people = _setting(context, "prepared.people", 1)
    target = _setting(context, "prepared.target_days", TARGET_DAYS)
    days, unread = water_days(items, people)
    who = "you" if people == 1 else f"{people} people"
    parts = []
    if days > 0:
        short = f" That's {round(target - days, 1):g} days short of your {target}-day target." if days < target else \
            f" That meets your {target}-day target."
        parts.append(f"Water: about {days:g} days of drinking water for {who}, at a gallon a person a day.{short}")
    else:
        parts.append(f"Water: none logged in the pantry. A gallon a person a day; {target} days for {who} is "
                     f"{target * people} gallons. Log it in Kitchen, Pantry, like \"water, 10 gallons\".")
    if unread:
        parts.append("I couldn't count " + ", ".join(unread[:3]) + ": give the bottle size, like \"16.9 oz bottles\".")
    soon = rotate(items, today)
    if soon:
        parts.append("Use soon, before it expires: " + ", ".join(f"{n} ({d:%b} {d.day})" for n, d in soon[:5]) + ".")
    parts.append("Not counted yet: days of food (the pantry doesn't say what each thing feeds) and power.")
    return " ".join(parts)
