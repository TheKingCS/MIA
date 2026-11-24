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
model's: the dates and counts are worked out in code and only phrased.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

MARK = "Home-canned"  # in a batch's notes: how the shelf knows its own jars from bought cans
BEST_DAYS = 365  # NCHFP: home-canned food is best used within a year
SOON_DAYS = 60  # a batch this close to its year is said as one to use next
SIZES = {"half-pint": "half-pints", "half pint": "half-pints", "pint": "pints", "quart": "quarts",
         "half-gallon": "half-gallons", "half gallon": "half-gallons"}
SAFETY = ("A jar whose lid has come unsealed, bulges, leaks, spurts when opened or smells off goes out without "
          "tasting, whatever its date.")
_PUT_UP = re.compile(r"put up (\d{4}-\d{2}-\d{2})")


def size_of(said: str) -> str:
    """Pure logic. A jar size in its plural ("quarts"), from what he said ("quart jars", "pints"); "" when it names
    none."""
    lowered = (said or "").lower()
    for word, plural in sorted(SIZES.items(), key=lambda kv: -len(kv[0])):  # "half-pint" before "pint"
        if word in lowered:
            return plural
    return ""


def batch_name(food: str, size: str, day: date) -> str:
    """Pure logic. A batch's pantry name: the food, the jar size and the month, so each batch stays its own."""
    food = " ".join((food or "").split()).strip(" ,.")
    food = food[:1].upper() + food[1:]
    return f"{food}, {size}, {day:%b %Y}" if size else f"{food}, {day:%b %Y}"


def put_up(kitchen, food: str, jars: float, size: str = "", day: Optional[date] = None):
    """Adds one batch of home-canned jars to the pantry (the jar count as its quantity, a year on as its date, `MARK`
    and the day in its notes) and returns the new pantry item. A second batch of the same food the same month is
    added to that batch instead of making a twin."""
    day = day or date.today()
    if not str(food or "").strip():
        raise ValueError("What did you put up?")
    if not jars or jars <= 0:
        raise ValueError("How many jars?")
    size = size_of(size) or size_of(food) or ""
    food = re.sub(r"\b(?:half[- ])?(?:pints?|quarts?|gallons?)\b|\bjars?\b|\bof\b", " ", food, flags=re.I)
    name = batch_name(food, size, day)
    same = next((p for p in kitchen.all_pantry_items() if p.name.lower() == name.lower()), None)
    if same is not None:
        kitchen.update_pantry_item(same.item_id, quantity=(same.quantity or 0) + jars)
        return kitchen.get_pantry_item(same.item_id)
    return kitchen.add_pantry_item(name, quantity=jars, unit="jars", category="Pantry/Dry Goods",
                                   expiration_date=(day + timedelta(days=BEST_DAYS)).isoformat(),
                                   notes=f"{MARK}, put up {day.isoformat()}.")


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
