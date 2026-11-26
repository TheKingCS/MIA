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
lab still keeps its harvests, once he says roughly when it was planted (never dated by a guess).

**This year** (`year`, `say_year`, the tool `harvest_this_year`): every harvest this calendar year, by crop and unit
(units read alike: "lbs" and "pounds" are pounds, `unit_of`), and what it would have cost at the cheapest price he's
recorded for that crop in the same unit in the last year (core/price_book.py), said beside what its plantings cost
(the batches' seeds and starts), so it's never called savings it isn't. A crop with no such price is said as not
valued, never guessed. The greenhouse node's harvests MIA kept (`greenhouse_harvest` life events,
core/greenhouse_link.keep_harvests) are in it too, its produce beside the garden's and its fish said on their own.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

_UNITS = {"lb": ("lb", "lbs", "pound", "pounds"), "oz": ("oz", "ounce", "ounces"), "kg": ("kg", "kgs", "kilo", "kilos",
          "kilogram", "kilograms"), "g": ("g", "gr", "gram", "grams"), "head": ("head", "heads"), "bunch": ("bunch", "bunches"), "quart": ("quart", "quarts",
          "qt"), "bushel": ("bushel", "bushels"), "dozen": ("dozen",), "each": ("", "each", "piece", "pieces", "whole")}


def unit_of(text: str) -> str:
    """Pure logic. A unit as one name ("Pounds" and "lbs" are "lb"); a unit not known is kept as said, lower case."""
    said = str(text or "").strip().lower().rstrip(".")
    return next((name for name, forms in _UNITS.items() if said in forms), said)


def _same_crop(a: str, b: str) -> bool:
    """Pure logic. Whether two crop names are the same crop: alike as one of each (`singular`: "tomatoes" and
    "Tomato", "strawberries" and "Strawberry", "green beans" and "Green bean")."""
    return bool(singular(a)) and singular(a) == singular(b)


def _one(word: str) -> str:
    """Pure logic. A word as one of it: "tomatoes" tomato, "radishes" radish, "peas" pea, "strawberries" strawberry,
    "leaves" leaf."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ves") and len(word) > 4:
        return word[:-3] + "f"
    if word.endswith(("oes", "shes", "ches", "xes", "zes", "sses")):
        return word[:-2]
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word


def singular(crop: str) -> str:
    """Pure logic. A crop's name as one of it, lower case ("Green Beans" is "green bean"): how harvests of one crop
    are kept together whatever it was called."""
    return " ".join(_one(w) for w in re.findall(r"[a-z]+", str(crop or "").lower()))


# Not a crop: what the grow lab doesn't keep, and where it goes instead
NOT_CROPS = {"egg": "Eggs go to the Chickens: say \"log 12 eggs\".",
             "honey": "Honey isn't a garden crop: it goes in the pantry (\"add 3 quarts of honey to the pantry\").",
             "milk": "Milk isn't a garden crop: it goes in the pantry.",
             "meat": "Meat isn't a garden crop: it goes in the pantry or the freezer."}


def growing(context, crop: str) -> list:
    """His grow lab's batches of this crop still growing (not harvested out or lost), newest first."""
    lab = getattr(context, "grow_lab", None)
    batches = [b for b in (lab.batches if lab is not None else []) if _same_crop(b.crop, crop)
               and b.status not in ("Harvested", "Lost")]
    return sorted(batches, key=lambda b: b.planted or "", reverse=True)


def log(context, crop: str, amount, unit: str = "", where: str = "", last: bool = False, planted: str = "") -> str:
    """Logs a harvest through the grow lab's own actions (see the module's opening); returns what happened, or what
    it needs (how much, which batch, when a crop not in the grow lab was planted: its batch is never dated by a
    guess). Eggs, honey and the like aren't crops (`NOT_CROPS`): it says where they go. A place named that none of
    its batches is in is a new batch there."""
    from core.actions import run_as_tool

    lab = getattr(context, "grow_lab", None)
    crop = str(crop or "").strip()
    if lab is None:
        return "The grow lab isn't on this MIA, so I can't keep harvests here."
    if not crop:
        return "What did you harvest?"
    for word in singular(crop).split():
        if word in NOT_CROPS:
            return NOT_CROPS[word]
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return f"How much {crop} did you harvest?"
    if amount <= 0:
        return f"How much {crop} did you harvest?"
    batches = growing(context, crop)
    if where:  # the place he named: its batch, or none (a new one there)
        batches = [b for b in batches if where.lower() in lab.place_name(b.asset_id or b.system).lower()]
    if len(batches) > 1:
        return (f"You have {len(batches)} batches of {crop} growing: "
                + ", ".join(f"{b.crop} in {lab.place_name(b.asset_id or b.system) or 'no place set'}" for b in batches)
                + ". Which one was it?")
    added = ""
    if not batches:
        if not str(planted or "").strip():
            return (f"There's no {crop} growing in the grow lab" + (f" in {where}" if where else "") + ". When did you "
                    "plant it, roughly? I'll add it with that date and log this harvest.")
        said = run_as_tool(context, "batch.add", {"crop": crop, "asset_id": where, "planted": planted,
                                                  "notes": "Added when a harvest was logged."})
        batches = growing(context, crop)
        if not batches:
            return said
        added = f"No {crop} was in the grow lab, so I added a batch of it. "
    return added + run_as_tool(context, "batch.harvest", {"batch_id": batches[0].batch_id, "amount": amount,
                                                         "unit": unit_of(unit) if unit else "",
                                                         "done": "yes" if last else ""})


def year(context, today: Optional[date] = None) -> list[dict]:
    """This calendar year's harvests, by crop (`singular`: "Tomato" and "tomatoes" together) and unit, heaviest
    first: each {crop, unit, amount, times, cost (what its batches cost: seeds, starts), value (None without a price,
    never for fish), price_from, fish}. Read from the grow lab and the greenhouse node's kept harvests
    (`_node_harvests`); prices from his price book, the cheapest per
    unit for that crop (by `_same_crop`) in the same unit, each store's latest in the last year.
    The garden's and the greenhouse's rows of a crop are one (both keyed with fish False), and a node's count is
    said as each."""
    today = today or date.today()
    lab = getattr(context, "grow_lab", None)
    totals: dict = {}
    for b in (lab.batches if lab is not None else []):
        for h in b.harvests or []:
            if not str(h.get("date", "")).startswith(str(today.year)):
                continue
            key = (singular(b.crop), unit_of(h.get("unit", "")), False)
            row = totals.setdefault(key, {"crop": key[0].capitalize(), "unit": key[1], "amount": 0.0, "times": 0,
                                          "batches": set(), "fish": False})
            row["amount"] += float(h.get("amount") or 0)
            row["times"] += 1
            row["batches"].add(b.batch_id)
    for e in _node_harvests(context, today):
        fish = e.payload.get("kind") == "harvest_fish"
        unit = unit_of(str(e.payload.get("unit") or ""))
        key = (singular(str(e.payload.get("item") or "produce")), "each" if unit in ("count", "counts") else unit,
               fish)
        row = totals.setdefault(key, {"crop": key[0].capitalize(), "unit": key[1], "amount": 0.0, "times": 0,
                                      "batches": set(), "fish": fish})
        try:
            row["amount"] += float(e.payload.get("quantity") or 0)
        except (TypeError, ValueError):
            continue
        row["times"] += 1
    costs = {b.batch_id: float(b.cost or 0) for b in (lab.batches if lab is not None else [])}
    book = getattr(context, "prices", None)
    for row in totals.values():
        row["cost"] = round(sum(costs.get(i, 0.0) for i in row.pop("batches")), 2)
        row["value"], row["price_from"] = None, ""
        row.setdefault("fish", False)
        if book is None or row["fish"]:
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


def _node_harvests(context, today: date) -> list:
    """This calendar year's greenhouse harvests MIA kept from the node (`greenhouse_harvest` life events), dated by
    the node's own time, else when she kept it; [] when none or the history can't be read."""
    from core import life_events

    try:
        found = life_events.events_for(context, types=("greenhouse_harvest",))
    except Exception:  # noqa: BLE001 - a history that can't be read leaves the node's part out
        log.exception("Couldn't read the greenhouse harvests")
        return []
    return [e for e in found if str(e.payload.get("at") or e.at).startswith(str(today.year))]


def _amount(row: dict) -> str:
    """Pure logic. "12.5 lb", "3 heads", "2 cups", "3 dozen", "4" for a count (a unit already ending in s, or dozen,
    never gets another)."""
    unit = row["unit"]
    if unit == "each":
        return f"{row['amount']:g}"
    plural = row["amount"] != 1 and unit not in ("lb", "oz", "kg", "dozen") and not unit.endswith("s")
    return f"{row['amount']:g} {unit}{'es' if plural and unit.endswith('h') else 's' if plural else ''}"


def say_year(context, today: Optional[date] = None) -> str:
    """This year's harvest in words, with what it would cost at his recorded store prices beside what its plantings
    cost (never called savings when their cost isn't recorded), and what isn't valued; the greenhouse's fish said on
    their own, never as produce or priced. With none logged, an example to say, worded so a bare "ok" never logs it."""
    from core.region import money

    today = today or date.today()
    if getattr(context, "grow_lab", None) is None and not _node_harvests(context, today):
        return "The grow lab isn't on this MIA, so there are no harvests to add up."
    every = year(context, today)
    rows = [r for r in every if not r["fish"]]
    fish = [r for r in every if r["fish"]]
    if fish and not rows:
        return (f"So far in {today.year} the greenhouse has given you " + "; ".join(
            f"{r['crop']}: {_amount(r)}" for r in fish) + " of fish, and no produce is logged yet.")
    if not rows:
        return (f"No harvests logged in {today.year} yet. Say one, like \"I harvested 3 pounds of beans\", to keep "
                "it with that crop.")
    said = "; ".join(f"{r['crop']}: {_amount(r)}" + (f" (about {money(r['value'])} at {r['price_from']}'s price)"
                                                    if r["value"] is not None else "") for r in rows)
    valued = [r for r in rows if r["value"] is not None]
    out = f"So far in {today.year} the garden has given you {said}."
    if valued:
        spent = sum(r["cost"] for r in valued)
        out += (f" What's priced would cost about {money(sum(r['value'] for r in valued))} at store prices you "
                "recorded" + (f", before the {money(spent)} its plantings cost in seeds and starts." if spent else
                              "; no cost for their seeds or starts is recorded, so that isn't what it saved."))
    unvalued = [r["crop"] for r in rows if r["value"] is None]
    if unvalued:
        out += (" No store price recorded in the same unit for " + ", ".join(unvalued) + ": record one and I'll "
                "count it.")
    if fish:
        out += " The greenhouse's fish: " + "; ".join(f"{r['crop']}: {_amount(r)}" for r in fish) + "."
    return out
