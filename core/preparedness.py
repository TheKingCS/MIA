"""
core.preparedness
===================

How ready he is if things go wrong (Jarvis brainstorm 4.3, first part; Zac, 2026-11-23: "survival skills, homestead
skills ... offline"), worked out in code from his own pantry (core/kitchen_manager.py), never guessed:

- **Water** (`water_days`): the drinking water he's logged in the pantry (an item named water, in gallons, liters,
  quarts or bottles of a stated size) against the Red Cross and FEMA guide of one gallon a person a day, for the
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
              "litres": 0.264172, "l": 0.264172, "quart": 0.25, "quarts": 0.25, "qt": 0.25}
_BOTTLE = re.compile(r"(\d+(?:\.\d+)?)\s*(oz|ounce|ounces|ml|l|liter|litre)\b", re.I)


def gallons_of(item) -> Optional[float]:
    """Pure logic. How many gallons of drinking water a pantry item holds, or None when it isn't water or its unit
    can't be read ("24 bottles" needs the bottle's size: "16.9 oz bottles")."""
    name = str(getattr(item, "name", "")).lower()
    if "water" not in name or any(w in name for w in ("chestnut", "cress", "melon", "softener", "heater")):
        return None
    qty = float(getattr(item, "quantity", 0) or 0)
    unit = str(getattr(item, "unit", "")).lower().strip()
    if unit in TO_GALLONS:
        return qty * TO_GALLONS[unit]
    size = _BOTTLE.search(f"{name} {unit}")
    if size:
        amount, what = float(size.group(1)), size.group(2).lower()
        each = amount / 128 if what in ("oz", "ounce", "ounces") else amount / 1000 * 0.264172 if what == "ml" \
            else amount * 0.264172
        return qty * each
    return None


def water_days(items: list, people: int) -> tuple[float, list]:
    """Pure logic. (days of water for that many people, the water items it couldn't read)."""
    total, unread = 0.0, []
    for item in items:
        got = gallons_of(item)
        if got is None:
            if "water" in str(getattr(item, "name", "")).lower():
                unread.append(item.name)
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
