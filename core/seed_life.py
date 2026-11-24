"""
core.seed_life
================

How long his seeds stay good (Jarvis brainstorm, round 4: seed saving). "Are my tomato seeds still good?" or "how long
do onion seeds last?" says how many years that kind of seed usually keeps its germination stored cool and dry (the
common extension figures, `YEARS`), and, for each packet in his pantry or inventory whose name gives a year ("tomato
seeds 2023", "saved 2024 bean seed"), whether it's still inside that span, or getting old and worth a germination test
(ten seeds on a damp paper towel). Read-only; nothing here is the model's.

`years_for(crop)` and `packets(names, crop, today)` are pure; `say(context, crop, today)` reads his records.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

# Years a kind of seed usually stays viable, stored cool and dry (common extension guidance)
YEARS = {
    "bean": 3, "beet": 4, "broccoli": 3, "brussels sprout": 4, "cabbage": 4, "carrot": 3, "cauliflower": 4,
    "celery": 3, "chard": 4, "collard": 5, "corn": 2, "cucumber": 5, "eggplant": 4, "kale": 4, "kohlrabi": 4,
    "leek": 2, "lettuce": 3, "melon": 5, "okra": 2, "onion": 1, "parsley": 1, "parsnip": 1, "pea": 3, "pepper": 2,
    "pumpkin": 4, "radish": 5, "spinach": 2, "squash": 4, "tomato": 4, "turnip": 4, "watermelon": 4, "basil": 5,
    "cilantro": 2, "dill": 3, "sunflower": 3, "zinnia": 3, "marigold": 2,
}
_PLURAL = {"tomatoes": "tomato", "potatoes": "potato", "beans": "bean", "peas": "pea", "peppers": "pepper",
           "onions": "onion", "carrots": "carrot", "beets": "beet", "radishes": "radish", "squashes": "squash",
           "cucumbers": "cucumber", "melons": "melon", "leeks": "leek", "turnips": "turnip", "pumpkins": "pumpkin",
           "sprouts": "brussels sprout", "zucchini": "squash", "cukes": "cucumber"}
_YEAR = re.compile(r"\b(20\d{2})\b")


def crop_of(said: str) -> str:
    """Pure logic. The kind of seed named ("tomatoes", "zucchini" is squash), or ""."""
    text = " ".join(str(said or "").lower().split())
    for word, crop in sorted(_PLURAL.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"\b{re.escape(word)}\b", text):
            return crop
    for crop in sorted(YEARS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(crop)}s?\b", text):
            return crop
    return ""


def years_for(crop: str) -> Optional[int]:
    """Pure logic. How many years that seed usually keeps, or None for one not in `YEARS`."""
    return YEARS.get(crop)


def packets(names: list, crop: str, today: date) -> list[dict]:
    """Pure logic. His seed packets of `crop` whose names give a year: [{name, year, age, state}], state "good"
    (inside its span), "test" (its last year, or one past: worth a germination test) or "old"."""
    span = YEARS.get(crop)
    out = []
    for name in names:
        low = str(name).lower()
        if "seed" not in low or crop_of(low) != crop:
            continue
        found = _YEAR.search(low)
        if not found or span is None:
            continue
        year = int(found.group(1))
        age = today.year - year
        state = "good" if age < span else "test" if age <= span + 1 else "old"
        out.append({"name": str(name), "year": year, "age": age, "state": state})
    return out


def _names(context) -> list:
    """His pantry and inventory item names (either may be missing)."""
    names = []
    for store, method in (("kitchen", "all_pantry_items"), ("inventory", "all_items")):
        owner = getattr(context, store, None)
        if owner is not None:
            names += [getattr(i, "name", "") for i in getattr(owner, method)()]
    return names


def say(context, crop_said: str, today: Optional[date] = None) -> str:
    """For "are my tomato seeds still good?": the kind's usual span, then each of his dated packets of it."""
    today = today or date.today()
    crop = crop_of(crop_said)
    if not crop:
        return "Which seeds? Say the vegetable or flower, like tomato, bean or onion."
    span = years_for(crop)
    if span is None:
        return f"I don't have a shelf life for {crop} seed."
    said = (f"{crop.capitalize()} seed usually stays good about {span} year{'s' if span != 1 else ''}, stored cool "
            f"and dry.")
    found = packets(_names(context), crop, today)
    for p in found:
        if p["state"] == "good":
            said += f" Your {p['name']} should still be good."
        elif p["state"] == "test":
            said += (f" Your {p['name']} is getting old: test ten seeds on a damp paper towel and "
                     f"sow thicker if fewer than about seven sprout.")
        else:
            said += f" Your {p['name']} is past its usual span: test it before you count on it."
    if not found:
        said += " None of your seed records for it give a year; put the year in the name (\"tomato seeds 2024\")."
    return said
