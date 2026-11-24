"""
core.power_ready
==================

Power in "how prepared am I?" (Jarvis brainstorm, round 3): how many days his generator can run on the fuel in his
records. It was the one thing the preparedness answer said it didn't count.

How: `fuel_on_hand(items)` (pure) reads gasoline, diesel, kerosene and propane from his inventory and pantry, by
whole word, in gallons: a pantry item's unit ("gallons", "quarts", "liters", or pounds for propane), else a size in
the name ("5 gal gas can", "20 lb propane tank": propane at about 4.24 lb a gallon) times how many. Equipment that
burns a fuel (a gas generator, a propane heater, a kerosene lamp's wick) and things that aren't fuel (diesel exhaust
fluid, gas line antifreeze) are never fuel (`_NOT_FUEL`). A record with none left is skipped; one with no size it can
read is named, never guessed. His generator's burn rate (`prepared.generator_gph`, gallons an hour at the load he runs
it, from its manual; a propane rate in pounds an hour is turned to gallons when it's set), its fuel
(`prepared.generator_fuel`, gasoline unless he says; "gas" and "petrol" are gasoline, "LP" propane) and how many hours
a day he'd run it (`prepared.generator_hours`, 8 unless he says: a fridge and freezer kept cold, not round the clock)
are his settings, set by voice (`set_preparedness`). `say(context)` is the line: days of running, or what it needs to
know. Nothing here is the model's: it only phrases the sentence.
"""

from __future__ import annotations

import re
from typing import Optional

FUELS = {
    "gasoline": r"gasoline|gas cans?|petrol|non[- ]ethanol|ethanol[- ]free|unleaded|"
                r"(?<!propane )(?<!natural )gas(?! grill)(?! station)(?! card)(?! bill)(?! masks?)",
    "diesel": r"diesel|off[- ]road diesel|red diesel",
    "kerosene": r"kerosene",
    "propane": r"propane|lp(?:g)? tanks?",
}
# What burns a fuel or only sounds like one: never fuel on hand
_NOT_FUEL = re.compile(r"\b(?:generators?|heaters?|torch(?:es)?|grills?|stoves?|dryers?|caps?|siphons?|pumps?|"
                       r"powered|antifreeze|exhaust fluid|def|mowers?|trimmers?|weed ?eaters?|chainsaws?|lamps?|"
                       r"lanterns?|wicks?|bulbs?|regulators?|hoses?|gauges?|smokers?|fryers?|water heaters?|"
                       r"fireplaces?|furnaces?|ranges?|ovens?|blowers?|tillers?)\b", re.I)
_FUEL = {fuel: re.compile(rf"\b(?:{words})\b", re.I) for fuel, words in FUELS.items()}
SAID_AS = {"gas": "gasoline", "gasoline": "gasoline", "petrol": "gasoline", "unleaded": "gasoline",
           "diesel": "diesel", "kerosene": "kerosene", "propane": "propane", "lp": "propane", "lpg": "propane"}
PROPANE_LB_A_GALLON = 4.24  # liquid propane, about 4.2 lb a gallon
HOURS_A_DAY = 8
_GALLONS = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(?:gal(?:lons?)?|gal\.)(?![a-z])", re.I)
_POUNDS = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(?:lbs?|pounds?)\b", re.I)
_UNIT = {"gal": 1.0, "gal.": 1.0, "gallon": 1.0, "gallons": 1.0, "quart": 0.25, "quarts": 0.25, "qt": 0.25,
         "liter": 0.264172, "liters": 0.264172, "litre": 0.264172, "litres": 0.264172, "l": 0.264172}
_LB_UNIT = {"lb", "lbs", "pound", "pounds"}


def fuel_of(name: str) -> str:
    """Pure logic. Which fuel a record is ("gasoline", "diesel", "kerosene", "propane"), or "" (no fuel named, or
    equipment that burns one: `_NOT_FUEL`)."""
    if not name or _NOT_FUEL.search(name):
        return ""
    for fuel in ("propane", "diesel", "kerosene", "gasoline"):  # "propane gas" is propane; "diesel" before "gas"
        if _FUEL[fuel].search(name):
            return fuel
    return ""


def gallons_in(name: str, unit: str, quantity: float, fuel: str) -> Optional[float]:
    """Pure logic. How many gallons one record holds (quantity above 0): its unit if that's a volume (or pounds for
    propane), else a size in its name times how many (propane in pounds turned to gallons); None when it can't be
    read."""
    qty = float(quantity or 0)
    unit = str(unit or "").strip().lower()
    if unit in _UNIT:
        return qty * _UNIT[unit]
    if fuel == "propane" and unit in _LB_UNIT:
        return qty / PROPANE_LB_A_GALLON
    said = f"{name} {unit}"
    size = _GALLONS.search(said)
    if size:
        return qty * float(size.group(1))
    if fuel == "propane":
        pounds = _POUNDS.search(said)
        if pounds:
            return qty * float(pounds.group(1)) / PROPANE_LB_A_GALLON
    return None


def fuel_on_hand(items: list) -> tuple[dict, list]:
    """Pure logic. ({fuel: gallons}, the fuel records whose amount couldn't be read) from records that have a name,
    a quantity and maybe a unit. A record with none left (quantity 0) is skipped; one whose quantity isn't a number
    is unread."""
    found, unread = {}, []
    for item in items:
        name = str(getattr(item, "name", "") or "")
        fuel = fuel_of(name)
        if not fuel:
            continue
        try:
            qty = float(getattr(item, "quantity", 0) or 0)
        except (TypeError, ValueError):
            unread.append(name)
            continue
        if qty <= 0:
            continue
        gallons = gallons_in(name, getattr(item, "unit", ""), qty, fuel)
        if gallons is None:
            unread.append(name)
        else:
            found[fuel] = round(found.get(fuel, 0.0) + gallons, 2)
    return found, unread


def run_days(gallons: float, gph: float, hours: float) -> float:
    """Pure logic. Days a generator runs on `gallons` at `gph` gallons an hour, `hours` a day (one decimal)."""
    if gallons <= 0 or gph <= 0 or hours <= 0:
        return 0.0
    return round(gallons / (gph * hours), 1)


def _number(context, key: str, default: Optional[float]) -> Optional[float]:
    """One of his number settings, or the default."""
    try:
        from core import person_settings

        value = person_settings.get(context, key, default)
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError, AttributeError):
        return default


def _records(context) -> list:
    """His inventory and pantry records (either may be missing)."""
    items = []
    for store, method in (("inventory", "all_items"), ("kitchen", "all_pantry_items")):
        owner = getattr(context, store, None)
        if owner is not None:
            items += list(getattr(owner, method)())
    return items


def _gallons(n: float) -> str:
    """Pure logic. "1 gallon", "0.6 gallons"."""
    return f"{n:g} gallon" if n == 1 else f"{n:g} gallons"


def say(context) -> str:
    """The power line for "how prepared am I?": the fuel he has, and how many days his generator runs on its fuel at
    his hours a day (less than a day said in hours; other fuel on hand said when his generator's isn't); or, without
    his burn rate, what to tell her."""
    found, unread = fuel_on_hand(_records(context))
    gph = _number(context, "prepared.generator_gph", None)
    hours = _number(context, "prepared.generator_hours", HOURS_A_DAY) or HOURS_A_DAY
    try:
        from core import person_settings

        fuel = SAID_AS.get(str(person_settings.get(context, "prepared.generator_fuel", "gasoline") or "").lower(),
                           "gasoline")
    except Exception:  # noqa: BLE001 - no settings to read: the usual fuel
        fuel = "gasoline"
    have = ", ".join(f"about {_gallons(g)} of {f}" for f, g in sorted(found.items()))
    parts = []
    if not found and unread:
        parts.append("Power: fuel in your records, but no amounts I can read: " + ", ".join(unread[:3])
                     + " (give a size, like \"5 gal\").")
        return " ".join(parts)
    if not found:
        return "Power: no fuel in your records (log it in Inventory, like \"gas cans, 5 gal\", 3)."
    if not gph:
        parts.append(f"Power: {have} on hand. Tell me your generator's burn rate (gallons an hour, or pounds an hour "
                     f"for propane, in its manual) and I'll count the days.")
    elif found.get(fuel, 0) > 0:
        days = run_days(found[fuel], gph, hours)
        running = round(found[fuel] / gph, 1)  # hours, for less than a day
        runs = f"about {days:g} days" if days >= 1 else f"less than a day (about {running:g} hours of running)"
        parts.append(f"Power: {have} on hand; your generator, at {_gallons(gph)} an hour for {hours:g} hours a day, "
                     f"runs {runs} on the {fuel}.")
    else:
        parts.append(f"Power: {have} on hand, but no {fuel}, which your generator is set to burn.")
    if unread:
        parts.append("I couldn't read how much is in " + ", ".join(unread[:3]) + " (give a size, like \"5 gal\").")
    return " ".join(parts)
