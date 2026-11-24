"""
core.harvest_log
==================

Harvests by voice, and what the garden has produced (Jarvis brainstorm round 7, 2026-11-24; one intelligence: the
garden, the grow lab and his price book read together). The grow lab already keeps harvests on its batches
(core/grow_lab.py, the action `batch.harvest`); until now only its screen could log one.

**Logging** (`log`, the tool `log_harvest`): "I harvested 5 pounds of tomatoes" finds his growing batch of that crop
(by its words, a plural the same as one: `_same_crop`) and logs it through `batch.harvest`, as the Greenhouse page
does, undoable. Two batches of it: which one, by where it's growing, else he's asked. None: a batch of it is added
first (`batch.add`, the place he names or "garden"), then the harvest, so a garden that was never set up in the grow
lab still keeps its harvests.

**This year** (`year`, `say_year`, the tool `harvest_this_year`): every harvest this calendar year, by crop and unit
(units read alike: "lbs" and "pounds" are pounds, `unit_of`), and what it would have cost at the cheapest price he's
recorded for that crop in the same unit in the last year (core/price_book.py). A crop with no such price is said as
not valued, never guessed.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

_UNITS = {"lb": ("lb", "lbs", "pound", "pounds"), "oz": ("oz", "ounce", "ounces"), "kg": ("kg", "kgs", "kilo", "kilos",
          "kilogram", "kilograms"), "head": ("head", "heads"), "bunch": ("bunch", "bunches"), "quart": ("quart", "quarts",
          "qt"), "bushel": ("bushel", "bushels"), "dozen": ("dozen",), "each": ("", "each", "piece", "pieces", "whole")}


def unit_of(text: str) -> str:
    """Pure logic. A unit as one name ("Pounds" and "lbs" are "lb"); a unit not known is kept as said, lower case."""
    said = str(text or "").strip().lower().rstrip(".")
    return next((name for name, forms in _UNITS.items() if said in forms), said)


def _same_crop(a: str, b: str) -> bool:
    """Pure logic. Whether two crop names are the same crop: their words alike, a plural the same as one
    ("tomatoes" and "Tomato", "green beans" and "Green bean")."""
    def one(word: str) -> str:
        """A word as one of it: "tomatoes" tomato, "radishes" radish, "peas" pea."""
        if word.endswith(("oes", "shes", "ches", "xes", "zes", "sses")):
            return word[:-2]
        return word[:-1] if word.endswith("s") and not word.endswith("ss") else word

    words = lambda s: {one(w) for w in re.findall(r"[a-z]+", s.lower())}  # noqa: E731
    return bool(words(a)) and words(a) == words(b)


def growing(context, crop: str) -> list:
    """His grow lab's batches of this crop still growing (not harvested out or lost), newest first."""
    lab = getattr(context, "grow_lab", None)
    batches = [b for b in (lab.batches if lab is not None else []) if _same_crop(b.crop, crop)
               and b.status not in ("Harvested", "Lost")]
    return sorted(batches, key=lambda b: b.planted or "", reverse=True)


def log(context, crop: str, amount, unit: str = "", where: str = "", last: bool = False) -> str:
    """Logs a harvest through the grow lab's own actions (see the module's opening); returns what happened, or what
    it needs (how much, which batch)."""
    from core.actions import run_as_tool

    lab = getattr(context, "grow_lab", None)
    crop = str(crop or "").strip()
    if lab is None:
        return "The grow lab isn't on this MIA, so I can't keep harvests here."
    if not crop:
        return "What did you harvest?"
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return f"How much {crop} did you harvest?"
    if amount <= 0:
        return f"How much {crop} did you harvest?"
    batches = growing(context, crop)
    if where and len(batches) > 1:
        here = [b for b in batches if where.lower() in lab.place_name(b.asset_id or b.system).lower()]
        batches = here or batches
    if len(batches) > 1:
        return (f"You have {len(batches)} batches of {crop} growing: "
                + ", ".join(f"{b.crop} in {lab.place_name(b.asset_id or b.system) or 'no place set'}" for b in batches)
                + ". Which one was it?")
    added = ""
    if not batches:
        said = run_as_tool(context, "batch.add", {"crop": crop,
                                                  "notes": f"Added when a harvest was logged ({where or 'garden'})."})
        batches = growing(context, crop)
        if not batches:
            return said
        added = f"No {crop} was in the grow lab, so I added a batch of it. "
    return added + run_as_tool(context, "batch.harvest", {"batch_id": batches[0].batch_id, "amount": amount,
                                                         "unit": unit_of(unit) if unit else "",
                                                         "done": "yes" if last else ""})


def year(context, today: Optional[date] = None) -> list[dict]:
    """This calendar year's harvests, by crop and unit, heaviest first: each {crop, unit, amount, times,
    value (None without a price), price_from}. Read from the grow lab; prices from his price book, the cheapest per
    unit for that crop (by `_same_crop`) in the same unit, each store's latest in the last year."""
    today = today or date.today()
    lab = getattr(context, "grow_lab", None)
    totals: dict = {}
    for b in (lab.batches if lab is not None else []):
        for h in b.harvests or []:
            if not str(h.get("date", "")).startswith(str(today.year)):
                continue
            name = re.sub(r"\s+", " ", b.crop.strip()).capitalize()
            key = (name.lower(), unit_of(h.get("unit", "")))
            row = totals.setdefault(key, {"crop": name, "unit": key[1], "amount": 0.0, "times": 0})
            row["amount"] += float(h.get("amount") or 0)
            row["times"] += 1
    book = getattr(context, "prices", None)
    for row in totals.values():
        row["value"], row["price_from"] = None, ""
        if book is None:
            continue
        try:
            since = (today - timedelta(days=365)).isoformat()
            latest = {}  # each store's latest price for it, in its unit
            for o in sorted(book.observations, key=lambda o: o.at):
                if o.at[:10] >= since and _same_crop(o.item, row["crop"]) and unit_of(o.unit) == row["unit"]:
                    latest[o.store.lower()] = o
            seen = sorted(latest.values(), key=lambda o: o.unit_price())
        except Exception:  # noqa: BLE001 - a price book that can't be read leaves it unvalued
            log.exception("Couldn't read the prices for %s", row["crop"])
            seen = []
        if seen:
            row["value"] = round(row["amount"] * seen[0].unit_price(), 2)
            row["price_from"] = seen[0].store
    return sorted(totals.values(), key=lambda r: -r["amount"])


def _amount(row: dict) -> str:
    """Pure logic. "12.5 lb", "3 heads", "4" for a count."""
    unit = row["unit"]
    if unit == "each":
        return f"{row['amount']:g}"
    plural = row["amount"] != 1 and unit not in ("lb", "oz", "kg")
    return f"{row['amount']:g} {unit}{'es' if plural and unit.endswith('h') else 's' if plural else ''}"


def say_year(context, today: Optional[date] = None) -> str:
    """This year's harvest in words, with what it would have cost at his recorded prices and what isn't valued."""
    from core.region import money

    today = today or date.today()
    if getattr(context, "grow_lab", None) is None:
        return "The grow lab isn't on this MIA, so there are no harvests to add up."
    rows = year(context, today)
    if not rows:
        return (f"No harvests logged in {today.year} yet. Say \"I harvested 3 pounds of beans\" and I'll keep it with "
                "that crop.")
    said = "; ".join(f"{r['crop']}: {_amount(r)}" + (f" (about {money(r['value'])} at {r['price_from']}'s price)"
                                                    if r["value"] is not None else "") for r in rows)
    valued = [r for r in rows if r["value"] is not None]
    out = f"So far in {today.year} the garden has given you {said}."
    if valued:
        out += f" What's priced comes to about {money(sum(r['value'] for r in valued))} at store prices you recorded."
    unvalued = [r["crop"] for r in rows if r["value"] is None]
    if unvalued:
        out += (" No store price recorded in the same unit for " + ", ".join(unvalued) + ": record one and I'll "
                "count it.")
    return out
