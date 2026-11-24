"""
core.preparedness
===================

How ready he is if things go wrong (Jarvis brainstorm 4.3, first part; Zac, 2026-11-23: "survival skills, homestead
skills ... offline"), worked out in code from his own pantry (core/kitchen_manager.py), never guessed:

- **Water** (`water_days`): the drinking water he's logged in the pantry (an item named water and meant for drinking,
  `is_drinking_water`: not coconut or tonic water, a water filter or a canner; in gallons, liters, quarts, ounces or
  containers of a stated size: "16.9 fl oz bottles", "5-gallon jugs") against the Red Cross and FEMA guide of one gallon a person a day, for the
  people he says (`prepared.people`, 1 unless he says otherwise; said in the answer). Against his target of days
  (`prepared.target_days`, 14 unless set: FEMA's two weeks at home). Both are set by voice (`set_preparedness`).
- Power: his generator's days on the fuel in his records (core/power_ready.py).
- **Rotate** (`rotate`): what's in the pantry and expires in the next ROTATE_DAYS days, soonest first, so it's eaten
  instead of thrown out.
- **Food** (`food_days`): the dry staples he's logged by weight (rice, beans, lentils, flour, oats, pasta, cornmeal,
  wheat, sugar, honey, peanut butter, powdered milk, oil, potatoes), at their calories a pound (`STAPLES`: USDA
  FoodData Central's figures for the dry or raw food), against 2,000 calories a person a day (the FDA's reference
  for daily values). What has no weight, or isn't a known staple (canned goods, frozen meals), is named as not
  counted, never guessed.
- **Not counted** (said plainly): power needs his batteries and generator; it waits for him (brainstorm 4.1).

`say(context)` answers "how prepared am I?" / "how many days of water do I have?".
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

GALLON_A_DAY = 1.0  # a person, drinking and a little washing (Red Cross, FEMA)
CALORIES_A_DAY = 2000  # a person (the FDA's reference for daily values)
# Calories a pound, dry or raw, from USDA FoodData Central (per 100 g x 4.536), first matching words win.
STAPLES = (("peanut butter", 2667), ("powdered milk", 1642), ("dry milk", 1642), ("milk powder", 1642),
           ("vegetable oil", 4010), ("olive oil", 4010), ("cooking oil", 4010), ("shortening", 4010), ("lard", 4105),
           ("rice", 1656), ("lentil", 1597), ("bean", 1574), ("flour", 1651), ("oat", 1719), ("pasta", 1683),
           ("spaghetti", 1683), ("macaroni", 1683), ("noodle", 1683), ("cornmeal", 1678), ("wheat", 1483),
           ("sugar", 1755), ("honey", 1379), ("potato", 349))
# Sold wet, canned, fresh or as a drink or sauce: never counted as the dry staple its name holds ("green beans", "oat
# milk", "rice vinegar", "pasta sauce", "collard greens", "bean sprouts").
_NOT_STAPLE = re.compile(r"\b(?:green|sprouts?|canned|can|cans|coffee|vanilla|vinegar|sauce|soup|dew|snap|sweet|"
                         r"cheese|juice|drink|chips|crackers|cereal|bars?|greens)\b|\b(?:oat|rice|almond|soy|coconut|"
                         r"goat)\s+milk\b", re.I)
TO_POUNDS = {"lb": 1.0, "lbs": 1.0, "pound": 1.0, "pounds": 1.0, "kg": 2.20462, "kgs": 2.20462, "kilogram": 2.20462,
             "kilograms": 2.20462, "oz": 1 / 16, "ounce": 1 / 16, "ounces": 1 / 16, "g": 0.00220462, "gram": 0.00220462,
             "grams": 0.00220462}
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


def food_days(items: list, people: int) -> tuple[float, list, list]:
    """Pure logic. (days of food for that many people at CALORIES_A_DAY, the staples counted, the food not counted:
    no weight, or not a known staple). A staple is matched by whole word ("collard" isn't lard, "goat" isn't oat), and
    what's sold wet, canned, fresh or as a drink is never one (`_NOT_STAPLE`). Drinking water isn't food."""
    calories, counted, uncounted = 0.0, [], []
    for item in items:
        name = str(getattr(item, "name", "")).lower()
        if not name or is_drinking_water(item):
            continue
        per_lb = None if _NOT_STAPLE.search(name) else next(
            (c for words, c in STAPLES if re.search(rf"\b{re.escape(words)}s?\b", name)), None)
        unit = str(getattr(item, "unit", "")).lower().strip().rstrip(".")
        pounds = float(getattr(item, "quantity", 0) or 0) * TO_POUNDS[unit] if unit in TO_POUNDS else None
        if per_lb is None or pounds is None:
            uncounted.append(item.name)
            continue
        calories += pounds * per_lb
        counted.append(item.name)
    return round(calories / (CALORIES_A_DAY * max(1, people)), 1), counted, uncounted


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
    """For "how prepared am I?": water against his target, days of food from the staples, what to rotate, what
    isn't counted, and power: his generator's days on the fuel in his records (core/power_ready.py)."""
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
    food, counted, uncounted = food_days(items, people)
    if counted:
        parts.append(f"Food: about {food:g} days for {who} at 2,000 calories a day, from the staples by weight ("
                     + ", ".join(counted[:5]) + (f" and {len(counted) - 5} more" if len(counted) > 5 else "") + ").")
    else:
        parts.append("Food: no staples logged by weight yet (rice, beans, flour, oats...): log them in Kitchen, Pantry, "
                     "like \"rice, 20 lb\", and I'll count the days.")
    if uncounted:
        parts.append("Not counted: " + ", ".join(uncounted[:4]) + (f" and {len(uncounted) - 4} more" if len(uncounted) > 4
                                                                    else "") + " (no weight, or not a staple I know).")
    from core import power_ready

    parts.append(power_ready.say(context))  # the generator's days on the fuel in his records
    return " ".join(parts)
