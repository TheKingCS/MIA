"""
core.seed_check
=================

Seeds against the plan (Jarvis brainstorm round 2; Zac, 2026-11-23: "homestead skills ... aware"): the crops his
confirmed garden plans start in the next SOON_DAYS days (indoors or sown outside), checked against the seeds he keeps,
from his pantry and inventory records (any item whose name has "seed" and the crop's name or another name for it), so
he hears about a missing packet while there's still time to get one. Nothing is guessed: a crop he hasn't logged seeds
for is said as "none logged", not "you have none".

`check(context, today)` is the list; `words` says it. core/garden_week.py adds the missing ones to its weekly message
and its answer.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

SOON_DAYS = 30


def _seed_names(context) -> list[str]:
    """Every pantry and inventory item named as seeds, lowercased."""
    names = []
    for store, method in (("kitchen", "all_pantry_items"), ("inventory", "all_items")):
        book = getattr(context, store, None)
        if book is None:
            continue
        try:
            names += [str(i.name).lower() for i in getattr(book, method)() if "seed" in str(i.name).lower()]
        except Exception:  # noqa: BLE001 - one store that can't be read never stops the check
            log.exception("Seed check: %s couldn't be read", store)
    return names


def _words_for(crop) -> list[str]:
    """Pure logic. The words that name a crop's seeds: its id and name, singular too ("tomato", "tomatoes")."""
    words = {crop.id.replace("_", " "), crop.name.lower()}
    for w in list(words):
        words.add(w.rstrip("s"))
        if w.endswith("es"):
            words.add(w[:-2])
    first = crop.name.lower().split(" and ")[0].split(" (")[0]
    words.add(first)
    words.add(first.rstrip("s"))
    return sorted(w for w in words if len(w) > 2)


def check(context, today: Optional[date] = None) -> list[dict]:
    """The crops started in the next SOON_DAYS days: each {crop, start (date), have (bool)}, soonest first."""
    from core.garden_plans import CROPS, parse_day, schedule

    today = today or date.today()
    plans = getattr(context, "project_plans", None)
    if plans is None:
        return []
    seeds = _seed_names(context)
    found: dict = {}
    for plan in plans.listed():
        if plan.kind != "garden" or plan.status != "confirmed":
            continue
        for year in (today.year, today.year + 1):
            last = parse_day(plan.last_frost, year)
            if last is None:
                continue
            for item in plan.crops:
                crop = CROPS.get(str(item.get("crop") if isinstance(item, dict) else item))
                if crop is None:
                    continue
                when = schedule(crop, last)
                start = when["start_indoors"] or when["out"]
                if when["how"] == "transplant" and when["start_indoors"] is None:
                    continue
                if today <= start <= today + timedelta(days=SOON_DAYS) and crop.id not in found:
                    have = any(any(w in s for w in _words_for(crop)) for s in seeds)
                    found[crop.id] = {"crop": crop.name, "start": start, "have": have}
    return sorted(found.values(), key=lambda f: f["start"])


def words(found: list[dict]) -> str:
    """Pure logic. The crops starting soon with no seeds logged, in a sentence ("" when every one has seeds)."""
    missing = [f for f in found if not f["have"]]
    if not missing:
        return ""
    return ("No seeds logged for " + "; ".join(f"{f['crop'].lower()} (starts {f['start']:%b} {f['start'].day})"
                                               for f in missing[:6])
            + ": get them, or log the ones you have (Kitchen, Pantry, like \"tomato seeds\").")
