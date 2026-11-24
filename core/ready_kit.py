"""
core.ready_kit
================

The 72-hour kit, checked against his own records (Jarvis brainstorm, round 3: survival and preparedness). "Check my
emergency kit" (`say`) goes down Ready.gov's basic disaster supplies kit and says which things his inventory or
pantry holds, which aren't in his records, and the few only he can check (medicine, glasses, cash, papers).

How: `KIT` is the list, each thing with the whole words that name it ("flashlight", "headlamp" or "lantern" is a
light). `check(names, water_days, food_days)` is pure: it matches the names of his inventory and pantry items, and
takes water and food as days (worked out by core/preparedness.py, a gallon a person a day and staples by weight)
against the kit's three days. Missing from his records is said as that, never as "you don't have it": he may own it
and not have logged it. Read-only: nothing is added or bought.
"""

from __future__ import annotations

import re
from typing import Optional

KIT_DAYS = 3  # Ready.gov: water and food for several days, at least three for an evacuation kit
# (key, how it's said, the whole words that name it in his records)
KIT = (
    ("radio", "a battery or hand-crank radio (NOAA weather radio)", r"radios?"),
    ("light", "a flashlight", r"flashlights?|headlamps?|lanterns?"),
    ("first_aid", "a first aid kit", r"first[- ]aid|trauma kit|ifak"),
    ("batteries", "extra batteries", r"batter(?:y|ies)|aa|aaa|18650s?"),
    ("whistle", "a whistle to signal for help", r"whistles?"),
    ("masks", "dust masks", r"dust masks?|n95s?|respirators?|face masks?"),
    ("sheeting", "plastic sheeting and duct tape to shelter in place", r"duct tape|plastic sheeting|tarps?|visqueen"),
    ("sanitation", "wet wipes, garbage bags and plastic ties", r"wet wipes|baby wipes|towelettes|garbage bags?|"
                                                              r"trash bags?|contractor bags?|zip ties?"),
    ("tools", "a wrench or pliers to turn off utilities", r"wrench(?:es)?|pliers|multi[- ]?tools?|leatherman"),
    ("can_opener", "a manual can opener", r"can openers?|p-?38|p-?51"),
    ("maps", "local maps", r"maps?|atlas|gazetteer"),
    ("charger", "a phone charger and backup battery", r"power banks?|battery banks?|portable chargers?|"
                                                       r"backup batter(?:y|ies)|phone chargers?"),
    ("fire", "matches in a waterproof container, or a lighter", r"matches|lighters?|ferro rods?|fire ?starters?"),
    ("warmth", "a sleeping bag or warm blanket", r"sleeping bags?|emergency blankets?|mylar blankets?|"
                                                 r"space blankets?|wool blankets?|bivvy|bivy"),
    ("extinguisher", "a fire extinguisher", r"fire extinguishers?|extinguishers?"),
)
ONLY_HE_CAN = "your medicines and glasses, some cash, and copies of your important papers"
_WORDS = {key: re.compile(rf"\b(?:{words})\b", re.I) for key, _said, words in KIT}


def check(names: list, water_days: float, food_days: float) -> dict:
    """Pure logic. The kit against his records: {"have": [(key, said, the record that names it)], "missing":
    [(key, said)], "water": days, "food": days, "short": the things under KIT_DAYS}."""
    have, missing = [], []
    for key, said, _words in KIT:
        found = next((n for n in names if _WORDS[key].search(str(n or ""))), None)
        (have.append((key, said, found)) if found else missing.append((key, said)))
    short = [w for w, days in (("water", water_days), ("food", food_days)) if days < KIT_DAYS]
    return {"have": have, "missing": missing, "water": water_days, "food": food_days, "short": short}


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
    """For "check my emergency kit": how many of the kit's things his records hold, water and food against three
    days, what isn't in his records, and what only he can check."""
    from core import preparedness

    kitchen = getattr(context, "kitchen", None)
    pantry = kitchen.all_pantry_items() if kitchen is not None else []
    people = people or preparedness._setting(context, "prepared.people", 1)
    water, _unread = preparedness.water_days(pantry, people)
    food, _counted, _uncounted = preparedness.food_days(pantry, people)
    got = check(_names(context), water, food)
    total = len(KIT) + 2
    held = len(got["have"]) + (2 - len(got["short"]))
    parts = [f"Of Ready.gov's basic emergency kit, your records hold {held} of {total} things."]
    days = (f"Water: about {water:g} days" if water else "Water: none logged") + \
        (f", food: about {food:g} days" if food else ", food: no staples logged by weight")
    parts.append(days + f" (the kit wants at least {KIT_DAYS} of each"
                 + (f"; {' and '.join(got['short'])} short)." if got["short"] else ", met)."))
    if got["missing"]:
        parts.append("Not in your inventory or pantry: " + "; ".join(s for _k, s in got["missing"]) + ".")
    parts.append(f"Only you can check {ONLY_HE_CAN}. Anything you have and haven't logged, add it in Inventory and "
                 f"I'll count it.")
    return " ".join(parts)
