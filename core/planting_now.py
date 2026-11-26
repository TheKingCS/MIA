"""
core.planting_now
===================

What to plant now, and when to plant one crop (Jarvis brainstorm, round 5), for crops he hasn't planned yet: "what
can I plant now?", "when should I plant potatoes?", "is it too late for tomatoes?". The Planner's crop calendar
(core/garden_plans.py `CROPS`, from US land-grant extension planting calendars) dated from his last spring frost
(`garden.last_frost`, kept when he plans a garden or says it), never an assumed date: without it, she asks.

How: `window(crop, last_frost, today)` (pure) says where today falls for a crop: start indoors, transplant or sow,
coming up (with its date), or past its spring window. `now(last_frost, today)` lists the crops whose step falls in
the next DUE_DAYS days or the last LATE_DAYS (still fine). A crop is named by whole words (`crop_named`: "sweet
potatoes" are never potatoes, "peanuts" never peas); a crop sown again and again is still sowable through the summer,
until its days to harvest before his first frost (`garden.first_frost`). `say_now` and `say_crop` read his frost date and put it in
words; `say_garlic` is fall's garlic, from his first frost. Read-only.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

DUE_DAYS = 14  # a step this soon is "now"
LATE_DAYS = 14  # and one this recent is still fine to do
SEASON_AFTER_DAYS = 90  # this long after the last frost, the spring that counts is next year's


_WORDS = {  # what he'd call each crop, whole words; several words before one ("sweet potato" before "potato")
    "tomato": ("tomato", "tomatoes"), "pepper": ("pepper", "peppers", "bell pepper", "hot peppers", "chili", "chilies"),
    "eggplant": ("eggplant", "eggplants"), "basil": ("basil",), "okra": ("okra",), "melon": ("melon", "melons",
    "cantaloupe", "cantaloupes", "muskmelon"), "watermelon": ("watermelon", "watermelons"),
    "cucumber": ("cucumber", "cucumbers", "cukes"), "zucchini": ("zucchini", "summer squash", "yellow squash"),
    "winter_squash": ("winter squash", "acorn squash", "butternut", "butternut squash", "squash"),
    "pumpkin": ("pumpkin", "pumpkins"), "bean_bush": ("bush beans", "bush bean", "green beans", "snap beans",
    "string beans", "beans", "bean"), "bean_pole": ("pole beans", "pole bean"), "corn": ("sweet corn", "corn"),
    "sweet_potato": ("sweet potato", "sweet potatoes", "slips"), "lettuce": ("lettuce", "salad greens"),
    "spinach": ("spinach",), "chard": ("swiss chard", "chard"), "kale": ("kale",), "broccoli": ("broccoli",),
    "cabbage": ("cabbage", "cabbages"), "cauliflower": ("cauliflower",), "peas": ("peas", "pea", "snap peas",
    "snow peas", "sugar snap peas"), "carrot": ("carrot", "carrots"), "beet": ("beet", "beets"),
    "radish": ("radish", "radishes"), "turnip": ("turnip", "turnips"), "onion": ("onion", "onions", "onion sets",
    "scallions", "green onions"), "leek": ("leek", "leeks"), "potato": ("potato", "potatoes", "seed potatoes"),
    "cilantro": ("cilantro", "coriander"), "parsley": ("parsley",), "dill": ("dill",),
}


def crop_named(said: str):
    """Pure logic. The crop his words name, by whole words, the longest name first ("sweet potatoes" is never
    potatoes, "peppermint" never peppers, "acorn squash" never corn), or None."""
    from core.garden_plans import CROPS

    text = " " + " ".join(re.sub(r"[^a-z ]", " ", str(said or "").lower()).split()) + " "
    pairs = sorted(((w, cid) for cid, words in _WORDS.items() for w in words), key=lambda p: -len(p[0]))
    for words, cid in pairs:
        if f" {words} " in text and cid in CROPS:
            return CROPS[cid]
    return None


def _frost(context, today: date) -> Optional[date]:
    """His last spring frost for the season ahead, from `garden.last_frost`, or None: this year's until three months
    after it, then the same day next year (in November the spring that counts is the coming one), a date saved with
    its year moved on too."""
    from core.garden_plans import parse_day

    config = getattr(context, "config", None)
    said = str(config.get("garden.last_frost", "") if config is not None else "")
    found = parse_day(said, today.year) if said else None
    if found is not None and (today - found).days > SEASON_AFTER_DAYS:
        try:  # "2026-04-20" as saved, or "April 20": the same day, next year (parse_day keeps a year it's given)
            found = found.replace(year=today.year + 1)
        except ValueError:  # Feb 29
            found = found.replace(year=today.year + 1, day=28)
    return found


def _first_frost(context, today: date) -> Optional[date]:
    """His first fall frost this year, from `garden.first_frost`, or None."""
    from core.garden_plans import parse_day

    config = getattr(context, "config", None)
    said = str(config.get("garden.first_frost", "") if config is not None else "")
    found = parse_day(said, today.year) if said else None
    return found.replace(year=today.year) if found is not None else None


def window(crop, last_frost: date, today: date) -> dict:
    """Pure logic. Where today falls for one crop: {"step", "on", "days"} for its next step (start indoors,
    transplant or sow; `days` from today, negative when it was that many days ago), or {"step": "past"} when its
    spring sowing is more than LATE_DAYS behind; `missed_indoors` when the seed-starting date has gone by (buy
    transplants instead)."""
    from core.garden_plans import schedule

    when = schedule(crop, last_frost)
    steps = [("start indoors", when["start_indoors"]), (when["how"], when["out"])]
    missed = False
    for step, on in steps:
        if on is None:
            continue
        days = (on - today).days
        if days >= -LATE_DAYS:
            return {"step": step, "on": on, "days": days, "missed_indoors": missed}
        missed = missed or step == "start indoors"
    return {"step": "past", "on": when["out"], "days": (when["out"] - today).days, "missed_indoors": False}


def now(last_frost: date, today: date) -> list[dict]:
    """Pure logic. The crops whose next step falls from LATE_DAYS ago to DUE_DAYS ahead: [{name, step, on, days}],
    soonest first."""
    from core.garden_plans import CROPS

    out = []
    for crop in CROPS.values():
        w = window(crop, last_frost, today)
        if w["step"] != "past" and w["days"] <= DUE_DAYS:
            out.append({"name": crop.name, **w})
    return sorted(out, key=lambda x: (x["days"], x["name"]))


def _when(days: int, on: date) -> str:
    """Pure logic. "today", "in 5 days (Mar 3)", "now (it was due Feb 20)"."""
    if days < 0:
        return f"now (it was due {on:%b} {on.day})"
    if days == 0:
        return "today"
    return f"in {days} day{'s' if days != 1 else ''} ({on:%b} {on.day})"


_ASK = ("When's your last spring frost? Tell me (\"my last frost is April 20\") and I'll work it out; your local "
        "extension office or a frost-date lookup by zip code has it.")


def say_now(context, today: Optional[date] = None) -> str:
    """For "what can I plant now?": the crops due now or just past, by step, from his last frost."""
    today = today or date.today()
    frost = _frost(context, today)
    if frost is None:
        return _ASK
    found = now(frost, today)
    if not found:
        return (f"Nothing on the spring calendar is due in the next two weeks (your last frost is {frost:%b} "
                f"{frost.day}). Ask me about one crop, like \"when do I plant tomatoes?\"")
    lines = [f"{x['name']}: {x['step']} {_when(x['days'], x['on'])}" for x in found]
    return f"From your last frost ({frost:%b} {frost.day}): " + "; ".join(lines) + "."


def say_garlic(context, today: Optional[date] = None) -> str:
    """For "when should I plant garlic?" (the skills sweep, 2026-11-26: the model said 6 to 8 weeks before frost):
    garlic goes in in the fall, from about his first fall frost to four weeks after, so the cloves root before the
    ground freezes (land-grant extension garlic guides); without his first frost, said as the rule and asked for."""
    today = today or date.today()
    first = _first_frost(context, today)
    how = ("Plant the cloves pointed end up, 2 in deep and 6 in apart, and mulch them with 4 to 6 in of straw once "
           "the ground cools; harvest next summer when about half the leaves have browned.")
    if first is None:
        return ("Garlic goes in in the fall, from about your first fall frost to a few weeks after, so it roots before "
                "the ground freezes. " + how + " Tell me your first fall frost date and I'll put dates on it.")
    end = first + timedelta(days=28)
    if today > end:
        return (f"Garlic's window this fall was about {first:%b} {first.day} to {end:%b} {end.day}, after your first "
                f"frost; if the ground isn't frozen yet, you can still get it in now. " + how)
    return (f"Garlic goes in this fall, from about your first frost ({first:%b} {first.day}) to {end:%b} {end.day}, so "
            f"the cloves root before the ground freezes. " + how)


def say_crop(context, said: str, today: Optional[date] = None) -> str:
    """For "when should I plant potatoes?": that crop (`crop_named`, whole words) and its next step and date; a
    seed-starting date gone by said (buy transplants); once this spring is well behind, next spring's said as that,
    and a crop sown again and again still sowable until its days before his first frost; or its window passed."""
    from core.garden_plans import CROPS

    today = today or date.today()
    crop = crop_named(said)
    if crop is None:
        return "Which crop? I have the planting dates for " + ", ".join(sorted(c.name.lower() for c in CROPS.values())) + "."
    frost = _frost(context, today)
    if frost is None:
        return _ASK
    rolled = frost.year > today.year  # this spring's well behind: the dates are next spring's
    if rolled and crop.again_days:
        first = _first_frost(context, today)
        if first is not None:
            last_sow = first - timedelta(days=crop.days)
            if today <= last_sow:
                return (f"{crop.name}: you can still sow them, every {crop.again_days} days for a steady harvest, "
                        f"until about {last_sow:%b} {last_sow.day} ({crop.days} days before your first frost).")
        elif today.month <= 8:
            return (f"{crop.name} can still be sown through the summer. Tell me your first fall frost and I'll say "
                    f"until when.")
    w = window(crop, frost, today)
    if w["step"] == "past":
        return f"The spring window for {crop.name.lower()} has passed: it was {w['on']:%b} {w['on'].day}."
    note = f" {crop.note[0].upper()}{crop.note[1:]}." if crop.note else ""
    late = (" It's too late to start them from seed indoors: buy transplants." if w.get("missed_indoors") else "")
    lead = "This year's spring window has passed; next spring: " if rolled and today.month >= 5 else ""
    return (f"{lead}{crop.name}: {w['step']} {_when(w['days'], w['on'])}, from your last frost "
            f"({frost:%b} {frost.day}).{late}{note}")
