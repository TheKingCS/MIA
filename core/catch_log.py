"""
core.catch_log
================

His fishing (Jarvis brainstorm, round 11: knowledgeable about his hobbies; fishing is one of his own, docs/VISION.md):
each fish he catches kept, and what his own catches say about what's biting.

**A catch** (`log`): the species, and what he says of it: length (inches), weight (pounds), where, the bait or lure,
kept or released; a model's placeholder ("unknown") is left out, and so is a length no fish of that weight could have
(`plausible_length`). A `fish_caught` life event in his own history (core/repertoire.py's way: dated, undone by "undo
that", never a second store); said as activity.logged, so the Angler achievements (core/rewards_manager.py) move at
once.

**What his catches say** (`catches`, `biting`, `bests`): the season's and all-time counts by species, the bait that
caught most, the hours of the day that did best (by when each was logged: log it when you land it), the place
that gave most, and his biggest of each species by length
(else weight): a personal best is said the moment he logs one. All from his own catches; nothing guessed about
species, the moon or the weather.

Used by the action `catch.log` (Expeditions, Log A Catch) and the tools `log_catch` and `whats_biting`.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from typing import Optional

from core.logger import get_logger

log_ = get_logger(__name__)


def _where(context):
    """His own history (the household's when there's no personal one)."""
    return getattr(context, "personal_life_events", None) or getattr(context, "life_events", None)


_BLANK = ("unknown", "none", "n/a", "na", "not specified", "unspecified", "null", "not given", "-")


def _clean(text, limit: int = 60) -> str:
    """Pure logic. Words tidied and cut short; a model's placeholder ("unknown", "none", "n/a") is nothing said."""
    words = " ".join(str(text or "").split())[:limit]
    return "" if words.lower().strip(".") in _BLANK else words


def plausible_length(length: Optional[float], weight: Optional[float]) -> Optional[float]:
    """Pure logic. The length, or None when no fish that long could weigh that much (over length³/400 lb: a 3-inch
    fish of 3 pounds is the model copying "3 pound" into the length, seen live 2026-11-24; an 18-inch 2.5 lb bass
    is well inside it)."""
    if length and weight and weight > length ** 3 / 400:
        return None
    return length


def _number(raw) -> Optional[float]:
    """Pure logic. A positive number from what he said ("18", "18 inch", "2.5 lb"), or None."""
    found = re.search(r"\d+(?:\.\d+)?", str(raw or ""))
    value = float(found.group(0)) if found else None
    return value if value and value > 0 else None


def catches(context) -> list[dict]:
    """Every catch, newest first: {species, length, weight, where, bait, kept, at}; an undone one left out."""
    from core import life_events

    try:
        events = life_events.events_for(context, types=("fish_caught", "undone"))
    except Exception:  # noqa: BLE001 - a history that can't be read lists nothing
        log_.exception("Couldn't read the catches")
        return []
    undone = life_events.reversed_ids(events)
    return [{**{k: e.payload.get(k) for k in ("species", "length", "weight", "where", "bait", "kept")}, "at": e.at}
            for e in events if e.type == "fish_caught" and e.event_id not in undone]


def count(context) -> float:
    """How many fish he's caught (the Angler stat)."""
    return float(len(catches(context)))


def _size(c: dict) -> tuple:
    """Pure logic. How a catch ranks for a personal best: length first, then weight."""
    return (c.get("length") or 0, c.get("weight") or 0)


def bests(rows: list[dict]) -> dict:
    """Pure logic. {species: its biggest catch} among those with a length or weight."""
    out: dict = {}
    for c in rows:
        if not (c.get("length") or c.get("weight")):
            continue
        name = (c.get("species") or "").lower()
        if name not in out or _size(c) > _size(out[name]):
            out[name] = c
    return out


def _measure(c: dict) -> str:
    """Pure logic. "18 in, 2.5 lb", or ""."""
    parts = [f"{c['length']:g} in" if c.get("length") else "", f"{c['weight']:g} lb" if c.get("weight") else ""]
    return ", ".join(p for p in parts if p)


def log(context, species: str, length=None, weight=None, where: str = "", bait: str = "", kept=None) -> str:
    """Keeps one catch and says so, with a personal best named when it is one. ValueError without a species. A
    placeholder spot or bait is left out, and a length no fish of that weight could have (`plausible_length`)."""
    from core import life_events

    species = _clean(species, 40)
    if not species:
        raise ValueError("What did you catch?")
    weight = _number(weight)
    row = {"species": species, "length": plausible_length(_number(length), weight), "weight": weight,
           "where": _clean(where),
           "bait": _clean(bait), "kept": None if kept in (None, "") else str(kept).lower() in ("true", "yes", "kept", "1")}
    before = bests(catches(context)).get(species.lower())
    target = _where(context)
    if target is None:
        raise ValueError("Your catch log isn't on this MIA.")
    life_events.record(target, "fish_caught", f"Caught a {species}" + (f" ({_measure(row)})" if _measure(row) else ""),
                       [], row)
    events = getattr(context, "events", None)
    if events is not None:
        events.publish("activity.logged", source="catch_log", category="fish_caught")
    said = f"Logged: a {species}" + (f", {_measure(row)}" if _measure(row) else "") + (f", at {row['where']}" if row["where"] else "") + "."
    if (row["length"] or row["weight"]) and before is not None and _size(row) > _size(before):
        said += f" That's your biggest {species} yet (the last was {_measure(before)})."
    elif (row["length"] or row["weight"]) and before is None:
        said += f" Your first {species} with a size: that's the one to beat."
    return said + f" {int(count(context))} fish logged in all."


def biting(rows: list[dict], season: Optional[int] = None) -> dict:
    """Pure logic. What the catches say: {total, species [(name, n)], bait (name, n), hour (label, n), place (name, n)}
    over all of them or one year's."""
    rows = [c for c in rows if season is None or str(c.get("at", ""))[:4] == str(season)]

    def top(key):
        tally = Counter(str(c.get(key) or "").lower() for c in rows if c.get(key))
        return tally.most_common(1)[0] if tally else None

    hours = Counter()
    for c in rows:
        try:
            h = datetime.fromisoformat(str(c.get("at"))).hour
        except ValueError:
            continue
        hours["dawn (5-9)" if 5 <= h < 9 else "late morning (9-12)" if 9 <= h < 12 else
              "afternoon (12-17)" if 12 <= h < 17 else "evening (17-21)" if 17 <= h < 21 else "night"] += 1
    return {"total": len(rows), "species": Counter(str(c.get("species") or "").lower() for c in rows).most_common(4),
            "bait": top("bait"), "hour": hours.most_common(1)[0] if hours else None, "place": top("where")}


def say(context, today: Optional[date] = None) -> str:
    """"What's been biting?": this year's catches (else all of them) said from his own log, and his personal bests."""
    today = today or date.today()
    rows = catches(context)
    if not rows:
        return "No catches logged yet. Tell me when you land one: \"caught an 18 inch bass on a jig at the pond\"."
    found = biting(rows, today.year)
    span = f"this year" if found["total"] else "in all"
    if not found["total"]:
        found = biting(rows)
    parts = [f"You've logged {found['total']} fish {span}: " + ", ".join(f"{n} {s}" for s, n in found["species"]) + "."]
    if found["bait"]:
        parts.append(f"Most came on {found['bait'][0]} ({found['bait'][1]}).")
    if found["hour"] and found["total"] >= 3:
        parts.append(f"Your best time has been {found['hour'][0]} ({found['hour'][1]}).")
    if found["place"]:
        parts.append(f"Your best spot: {found['place'][0]} ({found['place'][1]}).")
    top = sorted(bests(rows).items(), key=lambda kv: -(kv[1].get("length") or 0))[:3]
    if top:
        parts.append("Personal bests: " + "; ".join(f"{s} {_measure(c)}" for s, c in top) + ".")
    return " ".join(parts)
