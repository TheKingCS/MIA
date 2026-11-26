"""
core.ready_kit
================

The 72-hour kit, checked against his own records (Jarvis brainstorm, round 3: survival and preparedness). "Check my
emergency kit" (`say`) goes down Ready.gov's basic disaster supplies kit and says which things his inventory or
pantry holds (its 14 things: water, food and `KIT`), which aren't in his records, a few of its additional supplies
said apart (`EXTRA`), and the few only he can check (medicine, glasses, cash, papers).

How: `KIT` is the list, each thing with the whole words that name it ("flashlight", "headlamp" or "lantern" is a
light). `check(names, water_days, food_days)` is pure: it matches the names of his inventory and pantry items, and
takes water and food as days (worked out by core/preparedness.py, a gallon a person a day and staples by weight)
against the kit's three days. Missing from his records is said as that, never as "you don't have it": he may own it
and not have logged it. Read-only: nothing is added or bought. A vehicle's kit is its own list (`VEHICLE`,
`say_vehicle`: Ready.gov's car kit), never the house's bag.
"""

from __future__ import annotations

import re
from typing import Optional

KIT_DAYS = 3  # Ready.gov: water and food for several days, at least three for an evacuation kit
# (key, how it's said, the whole words that name it in his records)
KIT = (  # Ready.gov's basic kit, besides water and food: 12 things, so 14 with them
    ("radio", "a battery or hand-crank radio (NOAA weather radio)", r"radios?(?! flyer)"),
    ("light", "a flashlight", r"flashlights?|headlamps?|lanterns?"),
    ("first_aid", "a first aid kit", r"first[- ]?aid|trauma kits?|ifak|med(?:ical)? kits?"),
    # not a car's, a drill's or a battery bank (that's the charger)
    ("batteries", "extra batteries", r"(?<!car )(?<!drill )(?<!mower )(?<!tractor )(?<!truck )(?<!12v )(?<!18v )"
                                     r"(?<!20v )(?<!backup )batter(?:y|ies)(?! banks?)(?! chargers?)|aa|aaa|18650s?"),
    ("whistle", "a whistle to signal for help", r"whistles?"),
    ("masks", "dust masks", r"dust masks?|n95s?|respirators?|face masks?"),
    ("sheeting", "plastic sheeting and duct tape to shelter in place",
     r"duct tape|plastic sheeting|tarps?(?! straps?)|visqueen"),
    ("sanitation", "wet wipes, garbage bags and plastic ties", r"wet wipes|baby wipes|towelettes|garbage bags?|"
                                                              r"trash bags?|contractor bags?|(?:zip|cable)[- ]?ties?"),
    ("tools", "a wrench or pliers to turn off utilities", r"wrench(?:es)?|pliers|multi[- ]?tools?|leatherman|"
                                                           r"channel ?locks?|vise[- ]?grips?"),
    ("can_opener", "a manual can opener", r"(?<!electric )can openers?|p-?38|p-?51"),
    ("maps", "local maps", r"maps?(?![- ]?pro)(?! app)|road atlas|gazetteer"),
    ("charger", "a phone charger and backup battery", r"power banks?|battery banks?|portable chargers?|"
                                                       r"backup batter(?:y|ies)|phone chargers?|usb chargers?|"
                                                       r"charging cables?"),
)
# From Ready.gov's additional supplies: said apart, never counted in the basic kit's number
EXTRA = (
    ("fire", "matches in a waterproof container, or a lighter",
     r"matches|matchbox(?:es)?|lighters?(?! fluid)|ferro rods?|fire ?starters?"),
    ("warmth", "a sleeping bag or warm blanket", r"sleeping bags?|emergency blankets?|mylar blankets?|"
                                                 r"space blankets?|wool blankets?|bivvy|bivy"),
    ("extinguisher", "a fire extinguisher", r"(?:fire )?extinguishers?"),
)
ONLY_HE_CAN = "your medicines and glasses, some cash, and copies of your important papers"
_WORDS = {key: re.compile(rf"\b(?:{words})\b", re.I) for key, _said, words in KIT + EXTRA}


def check(names: list, water_days: float, food_days: float) -> dict:
    """Pure logic. The kit against his records: {"have": [(key, said, the record that names it)], "missing":
    [(key, said)], "extra_have", "extra_missing" (the same for `EXTRA`), "water": days, "food": days, "short": the
    things under KIT_DAYS}."""
    def sort(items):
        """Which of `items` a name of his holds, and which none does."""
        have, missing = [], []
        for key, said, _words in items:
            found = next((n for n in names if _WORDS[key].search(str(n or ""))), None)
            (have.append((key, said, found)) if found else missing.append((key, said)))
        return have, missing

    have, missing = sort(KIT)
    extra_have, extra_missing = sort(EXTRA)
    short = [w for w, days in (("water", water_days), ("food", food_days)) if days < KIT_DAYS]
    return {"have": have, "missing": missing, "extra_have": extra_have, "extra_missing": extra_missing,
            "water": water_days, "food": food_days, "short": short}


def _names(context) -> list:
    """The names of everything in his inventory and pantry (either may be missing)."""
    names = []
    inventory = getattr(context, "inventory", None)
    kitchen = getattr(context, "kitchen", None)
    if inventory is not None:
        names += [i.name for i in inventory.all_items()]  # a count of 0 there often means "not counted", not gone
    if kitchen is not None:
        names += [p.name for p in kitchen.all_pantry_items() if (p.quantity or 0) > 0]
    return names


def say(context, people: Optional[int] = None) -> str:
    """For "check my emergency kit": how many of Ready.gov's 14 basic things his records hold, water and food against
    three days (water whose bottle size couldn't be read is said as that, never as none), what isn't in his records,
    the additional supplies apart, and what only he can check."""
    from core import preparedness

    kitchen = getattr(context, "kitchen", None)
    pantry = kitchen.all_pantry_items() if kitchen is not None else []
    people = people or preparedness._setting(context, "prepared.people", 1)
    water, unread = preparedness.water_days(pantry, people)
    food, _counted, _uncounted = preparedness.food_days(pantry, people)
    got = check(_names(context), water, food)
    total = len(KIT) + 2
    held = len(got["have"]) + (2 - len(got["short"]))
    parts = [f"Of Ready.gov's basic emergency kit, your records hold {held} of {total} things."]
    if water:
        said_water = f"Water: about {water:g} days"
    elif unread:
        said_water = "Water: I couldn't read the size of " + ", ".join(unread[:3]) + " (give it, like \"16.9 oz bottles\")"
    else:
        said_water = "Water: none logged"
    said_food = f", food: about {food:g} days" if food else ", food: no staples logged by weight"
    parts.append(said_water + said_food + f" (the kit wants at least {KIT_DAYS} days of each"
                 + (f"; {' and '.join(got['short'])} short)." if got["short"] else ", met)."))
    if got["missing"]:
        parts.append("Not in your inventory or pantry: " + "; ".join(s for _k, s in got["missing"]) + ".")
    if got["extra_missing"]:
        parts.append("Of the additional supplies it suggests, not in your records: "
                     + "; ".join(s for _k, s in got["extra_missing"]) + ".")
    parts.append(f"Only you can check {ONLY_HE_CAN}. Anything you have and haven't logged, add it in Inventory and "
                 f"I'll count it.")
    return " ".join(parts)


# Ready.gov's emergency supply kit for a car (ready.gov/car), and its winter additions: (key, how it's said, the
# whole words that name it in his records)
VEHICLE = (
    ("jumper", "jumper cables (or a jump starter)", r"jumper cables?|booster cables?|jump (?:starter|box|pack)s?"),
    ("light", "a flashlight and extra batteries", r"flashlights?|headlamps?|lanterns?"),
    ("first_aid", "a first aid kit", r"first[- ]?aid|trauma kits?|ifak|med(?:ical)? kits?"),
    ("water_food", "water and non-perishable snacks", r"water bottles?|bottled water|granola bars?|protein bars?|"
                                                      r"energy bars?|mres?"),
    ("charger", "a phone charger for the car", r"car chargers?|phone chargers?|power banks?|battery banks?"),
    ("blanket", "a blanket", r"blankets?|sleeping bags?|mylar|space blankets?"),
    ("map", "a paper map", r"maps?(?![- ]?pro)(?! app)|road atlas|gazetteer"),
    ("signal", "flares or reflective triangles", r"flares?|reflective triangles?|road triangles?|warning triangles?"),
    ("tire", "a tire gauge, and a spare with a jack you've checked", r"tire (?:gauge|inflator|plug kit)s?|tyre "
                                                                     r"gauges?|air compressors?|spare tires?|jacks?"),
    ("winter", "for winter: an ice scraper, a small shovel, and sand or cat litter for traction",
     r"ice scrapers?|snow brush(?:es)?|shovels?|cat litter|kitty litter|traction (?:mats?|sand)"),
)
_VEHICLE_WORDS = {key: re.compile(rf"\b(?:{words})\b", re.I) for key, _said, words in VEHICLE}


def say_vehicle(context) -> str:
    """For "what should be in my truck's emergency kit?" (the full sweep, 2026-11-26: it had been given the house's
    72-hour bag): Ready.gov's car kit against his inventory, what his records hold and what they don't (said as not in
    his records, never as not owned). Read only."""
    names = _names(context)
    have, missing = [], []
    for key, said, _words in VEHICLE:
        found = next((n for n in names if _VEHICLE_WORDS[key].search(str(n or ""))), None)
        (have.append((said, found)) if found else missing.append(said))
    parts = [f"Ready.gov's kit for a vehicle has {len(VEHICLE)} things; your records hold {len(have)}."]
    if have:
        parts.append("In your records: " + "; ".join(f"{said} ({found})" for said, found in have) + ".")
    if missing:
        parts.append("Not in your records: " + "; ".join(missing) + ".")
    parts.append("Keep the tank at least half full in winter, and tell someone your route on a long drive.")
    return " ".join(parts)
