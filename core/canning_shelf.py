"""
core.canning_shelf
====================

The canning shelf (Jarvis brainstorm, round 2): the jars he puts up, kept as batches in his pantry, said by date
against the USDA's best-quality window. "I put up 7 quarts of tomatoes today" adds a batch (`put_up`); "what's on my
canning shelf?" reads them back (`shelf`, `say`), oldest first, with the ones nearing or past a year said first.

How: a batch is an ordinary pantry item (core/kitchen_manager.py), so the Kitchen screen shows and edits it, Undo
takes it back, and "how prepared am I?" already lists what's nearing its date (core/preparedness.rotate). Its name
holds the food and the month ("Tomatoes, quarts, Nov 2026") so each batch stays its own; its notes carry `MARK` and
the day it was put up; its expiration date is a year on, the National Center for Home Food Preservation's "use within
a year" for best quality. That date is about quality, not safety: what makes a jar unsafe is a seal that failed or
signs of spoiling, so the shelf's answer always says to throw such a jar out without tasting it. Nothing here is the
model's: the dates and counts are worked out in code and only phrased. What he said is read in code too:
`food_of` (the food without its count and jar words), `size_of` (the jar size, whole words only) and `count_of`
(a number or a spoken one, "a dozen").
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

MARK = "Home-canned"  # in a batch's notes: how the shelf knows its own jars from bought cans
BEST_DAYS = 365  # NCHFP: home-canned food is best used within a year
SOON_DAYS = 60  # a batch this close to its year is said as one to use next
SIZES = {"half-pint": "half-pints", "half pint": "half-pints", "pint": "pints", "pt": "pints", "quart": "quarts",
         "qt": "quarts", "half-gallon": "half-gallons", "half gallon": "half-gallons", "gallon": "gallons"}
# NCHFP's signs of spoiling, and its care with a jar that may hold botulism: never tasted, never opened carelessly.
SAFETY = ("A jar whose lid is unsealed or bulging, that leaks, spurts or foams when opened, or shows mold, cloudiness, "
          "odd colour or an off smell goes out without tasting, whatever its date: leave it closed, bag it, and wear "
          "gloves handling it.")
NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
           "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "a dozen": 12, "dozen": 12, "two dozen": 24,
           "a half dozen": 6, "half a dozen": 6}
_SIZE = "|".join(sorted((w.replace("-", "[- ]") for w in SIZES), key=len, reverse=True))
_SIZE_WORD = re.compile(rf"\b(?:{_SIZE})s?\b", re.I)
_COUNT = re.compile(r"^\s*(?:\d+(?:\.\d+)?|" + "|".join(sorted(map(re.escape, NUMBERS), key=len, reverse=True))
                    + r")\s+", re.I)
_LEAD = re.compile(rf"^\s*(?:(?:{_SIZE})s?\s+)?(?:jars?\s+)?of\s+", re.I)
_PUT_UP = re.compile(r"put up (\d{4}-\d{2}-\d{2})")


def size_of(said: str) -> str:
    """Pure logic. A jar size in its plural ("quarts"), from what he said ("quart jars", "pints", "qt"), whole
    words only, so "pinto beans" and "quartered peaches" name none; "" when it names none."""
    found = _SIZE_WORD.search(said or "")  # whole words: "pinto beans" and "quartered peaches" name no jar
    if not found:
        return ""
    word = found.group(0).lower().replace(" ", "-")
    word = word[:-1] if word not in SIZES and word.endswith("s") else word
    return SIZES.get(word, SIZES.get(word.replace("-", " "), ""))


def count_of(said) -> float:
    """Pure logic. A jar count from a number or spoken words ("7", "seven", "a dozen"); 0 when it names none."""
    if isinstance(said, (int, float)):
        return float(said)
    text = " ".join(str(said or "").lower().split())
    try:
        return float(text)
    except ValueError:
        return float(NUMBERS.get(text, 0))


def food_of(said: str) -> str:
    """Pure logic. The food from what he said, without the count or jar words before it ("7 quart jars of tomatoes"
    is "tomatoes"; "cream of mushroom soup" keeps its "of")."""
    text = _COUNT.sub("", said or "")
    text = _LEAD.sub("", text)
    text = _SIZE_WORD.sub(" ", re.sub(r"^\s*jars?\s+of\s+", "", text, flags=re.I))
    return " ".join(text.split()).strip(" ,.")


def batch_name(food: str, size: str, day: date) -> str:
    """Pure logic. A batch's pantry name: the food, the jar size and the month, so each batch stays its own."""
    food = " ".join((food or "").split()).strip(" ,.")
    food = food[:1].upper() + food[1:]
    return f"{food}, {size}, {day:%b %Y}" if size else f"{food}, {day:%b %Y}"


def put_up(kitchen, food: str, jars: float, size: str = "", day: Optional[date] = None):
    """Adds one batch of home-canned jars to the pantry (the jar count as its quantity, a year on as its date, `MARK`
    and the day in its notes) and returns the new pantry item. The food is read from what he said (`food_of`:
    "7 quart jars of tomatoes" is tomatoes, in quarts). A second batch of the same food the same month is added to
    that batch instead of making a twin.
    Each batch is also a `canned` life event with its jar count (`_record`), so the jars ever canned count toward
    the achievements after they're eaten."""
    day = day or date.today()
    if not food_of(str(food or "")):
        raise ValueError("What did you put up?")
    if not jars or jars <= 0:
        raise ValueError("How many jars?")
    size = size_of(size) or size_of(food) or ""
    name = batch_name(food_of(food), size, day)
    same = next((p for p in kitchen.all_pantry_items() if p.name.lower() == name.lower()), None)
    if same is not None:
        kitchen.update_pantry_item(same.item_id, quantity=(same.quantity or 0) + jars)
        item = kitchen.get_pantry_item(same.item_id)
    else:
        item = kitchen.add_pantry_item(name, quantity=jars, unit="jars", category="Pantry/Dry Goods",
                                       expiration_date=(day + timedelta(days=BEST_DAYS)).isoformat(),
                                       notes=f"{MARK}, put up {day.isoformat()}.")
    _record(kitchen, item, jars, food_of(food))
    return item


def _record(kitchen, item, jars: float, food: str) -> None:
    """A `canned` life event for the jars just put up (their count and food), so the jars he has ever canned are
    counted after they're eaten (core/life_milestones.jars_canned), and the achievements hear of it."""
    from core import life_events

    jar_word = "jar" if jars == 1 else "jars"
    life_events.record(kitchen, "canned", f"Put up {jars:g} {jar_word} of {food}",
                       refs=[f"pantry:{item.item_id}"] if item is not None else [],
                       payload={"jars": jars, "food": food})
    events = getattr(getattr(kitchen, "context", None), "events", None)
    if events is not None:
        events.publish("activity.logged", source="canning", category="jars_put_up")


def shelf(items: list, today: date) -> list[dict]:
    """Pure logic. The home-canned batches still on hand, oldest first: name, jars, the day put up, the best-by date,
    days left (negative once past) and its state: "past" (over a year), "soon" (within SOON_DAYS) or "fine"."""
    out = []
    for item in items:
        notes = str(getattr(item, "notes", "") or "")
        if MARK.lower() not in notes.lower() or not (getattr(item, "quantity", 0) or 0) > 0:
            continue
        found = _PUT_UP.search(notes)
        try:
            put = date.fromisoformat(found.group(1)) if found else None
            best = date.fromisoformat(str(item.expiration_date)[:10]) if item.expiration_date else None
        except ValueError:
            put, best = None, None
        best = best or (put + timedelta(days=BEST_DAYS) if put else None)
        if best is None:
            continue
        left = (best - today).days
        out.append({"name": item.name, "jars": item.quantity, "put_up": put.isoformat() if put else "",
                    "best_by": best.isoformat(), "days_left": left,
                    "state": "past" if left < 0 else "soon" if left <= SOON_DAYS else "fine"})
    return sorted(out, key=lambda b: (b["best_by"], b["name"]))


def _jars(n) -> str:
    """Pure logic. A jar count in words: "1 jar", "7 jars", "2.5 jars" as said."""
    n = int(n) if float(n).is_integer() else n
    return f"{n} jar" if n == 1 else f"{n} jars"


def say(context, today: Optional[date] = None) -> str:
    """The shelf in a few sentences: how many jars in how many batches, the ones past a year or nearing it first
    (use those next), and the safety line. Says so when there's nothing put up yet."""
    today = today or date.today()
    kitchen = getattr(context, "kitchen", None)
    batches = shelf(kitchen.all_pantry_items() if kitchen is not None else [], today)
    if not batches:
        return ("Nothing home-canned is on the shelf yet. Tell me when you put some up (\"I put up 7 quarts of "
                "tomatoes\") and I'll keep each batch by its date.")
    total = sum(b["jars"] for b in batches)
    lines = [f"{_jars(total)} on the canning shelf, in {len(batches)} batch{'es' if len(batches) != 1 else ''}."]
    past = [b for b in batches if b["state"] == "past"]
    soon = [b for b in batches if b["state"] == "soon"]
    if past:
        lines.append("Past a year, so use these first (past their best quality; a sealed jar from a tested "
                     "recipe doesn't turn unsafe on that date): "
                     + "; ".join(f"{b['name']} ({_jars(b['jars'])})" for b in past) + ".")
    if soon:
        lines.append("Nearing a year: " + "; ".join(f"{b['name']} ({_jars(b['jars'])}, best by {b['best_by']})"
                                                     for b in soon) + ".")
    if not past and not soon:
        first = batches[0]
        lines.append(f"The oldest is {first['name']}, best by {first['best_by']}.")
    lines.append(SAFETY)
    return " ".join(lines)
