"""
core.power_ready
==================

Power in "how prepared am I?" (Jarvis brainstorm, round 3): how many days his generator can run on the fuel in his
records. It was the one thing the preparedness answer said it didn't count.

How: `fuel_on_hand(items)` (pure) reads gasoline, diesel, kerosene and propane from his inventory and pantry, by
whole word, in gallons: a pantry item's unit ("gallons"), else a size in the name ("5 gal gas can", "20 lb propane
tank": propane at about 4.24 lb a gallon) times how many. What has no size it can read is named, never guessed. His
generator's burn rate (`prepared.generator_gph`, gallons an hour at the load he runs it, from its manual), its fuel
(`prepared.generator_fuel`, gasoline unless he says) and how many hours a day he'd run it (`prepared.generator_hours`,
8 unless he says: a fridge and freezer kept cold, not round the clock) are his settings, set by voice
(`set_preparedness`). `say(context)` is the line: days of running, or what it needs to know. Nothing here is the
model's: it only phrases the sentence.
"""

from __future__ import annotations

import re
from typing import Optional

FUELS = {
    "gasoline": r"gasoline|gas cans?|petrol|non[- ]ethanol|ethanol[- ]free|(?<!propane )(?<!natural )gas(?! grill)"
                r"(?! station)(?! card)(?! bill)(?! masks?)",
    "diesel": r"diesel|off[- ]road diesel|red diesel",
    "kerosene": r"kerosene|k-?1",
    "propane": r"propane|lp(?:g)? tanks?",
}
_FUEL = {fuel: re.compile(rf"\b(?:{words})\b", re.I) for fuel, words in FUELS.items()}
PROPANE_LB_A_GALLON = 4.24  # liquid propane, about 4.2 lb a gallon
HOURS_A_DAY = 8
_GALLONS = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(?:gal(?:lons?)?|gal\.)\b", re.I)
_POUNDS = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(?:lbs?|pounds?)\b", re.I)
_UNIT_GALLONS = {"gal", "gal.", "gallon", "gallons"}


def fuel_of(name: str) -> str:
    """Pure logic. Which fuel a record names ("gasoline", "diesel", "kerosene", "propane"), or ""."""
    for fuel in ("propane", "diesel", "kerosene", "gasoline"):  # "propane gas" is propane; "diesel" before "gas"
        if _FUEL[fuel].search(name or ""):
            return fuel
    return ""


def gallons_in(name: str, unit: str, quantity: float, fuel: str) -> Optional[float]:
    """Pure logic. How many gallons one record holds: its unit if that's gallons, else a size in its name times how
    many (propane in pounds turned to gallons); None when it can't be read."""
    qty = float(quantity or 0)
    if qty <= 0:
        return None
    if str(unit or "").strip().lower() in _UNIT_GALLONS:
        return qty
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
    a quantity and maybe a unit."""
    found, unread = {}, []
    for item in items:
        name = str(getattr(item, "name", "") or "")
        fuel = fuel_of(name)
        if not fuel:
            continue
        gallons = gallons_in(name, getattr(item, "unit", ""), getattr(item, "quantity", 0), fuel)
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


def say(context) -> str:
    """The power line for "how prepared am I?": the fuel he has, and how many days his generator runs on it at his
    hours a day; or, without his burn rate, what to tell her."""
    found, unread = fuel_on_hand(_records(context))
    gph = _number(context, "prepared.generator_gph", None)
    hours = _number(context, "prepared.generator_hours", HOURS_A_DAY) or HOURS_A_DAY
    try:
        from core import person_settings

        fuel = str(person_settings.get(context, "prepared.generator_fuel", "gasoline") or "gasoline").lower()
    except Exception:  # noqa: BLE001 - no settings to read: the usual fuel
        fuel = "gasoline"
    have = ", ".join(f"about {g:g} gallons of {f}" for f, g in sorted(found.items()))
    parts = []
    if not found:
        parts.append("Power: no fuel in your records (log it in Inventory, like \"gas cans, 5 gal\", 3).")
    elif not gph:
        parts.append(f"Power: {have} on hand. Tell me your generator's burn rate (gallons an hour, in its manual) and "
                     f"I'll count the days.")
    else:
        days = run_days(found.get(fuel, 0.0), gph, hours)
        parts.append(f"Power: {have} on hand; your generator, at {gph:g} gallons an hour for {hours:g} hours a day, "
                     f"runs about {days:g} days on the {fuel}." if days else
                     f"Power: {have} on hand, but no {fuel} for your generator.")
    if unread:
        parts.append("I couldn't read how much is in " + ", ".join(unread[:3]) + " (give a size, like \"5 gal\").")
    return " ".join(parts)
