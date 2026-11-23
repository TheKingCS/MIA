"""
core.garden_plans
===================

A garden worked out in code (T-0060; Zac, 2026-11-22: "auto generated missions for plans we confirm together for
different builds or gardens"), the way core/build_calcs.py works out lumber: never by the model.

- **The crops** (`CROPS`): each common vegetable and herb with how it's started (indoors, direct, or either), when
  relative to the last spring frost (weeks before or after), how many fit a square foot (square-foot spacing), its
  days to harvest, how much frost it takes (hardy, half-hardy, tender), and how often to sow again for a steady
  harvest. General planting-chart figures (US extension services' vegetable planting calendars and square-foot
  spacing); a seed packet's own numbers come first, and the plan says so.
- **His dates** (`schedule`): his last spring frost and first fall frost are his to give (a plan holds them, and they
  are remembered in `garden.last_frost` / `garden.first_frost`); never assumed in code. From them, each crop's dates:
  start indoors, harden off, transplant or sow, first harvest; a tender crop that can't ripen before the first fall
  frost is said.
- **The beds** (`beds_needed`, `bed_soil`): how many plants fit the space each crop is given, and the soil to fill a
  raised bed (cubic feet and yards).
- **The stages** (`stages`): the garden as stages of steps (prepare the beds, start seeds, harden off and transplant,
  sow outside, care, harvest), each step with what to do, why, what to watch for and a check, and the date it falls
  on: what core/project_plans.py turns into missions once he confirms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

SOURCES = ("US land-grant extension vegetable planting calendars (dates relative to the average last frost)",
           "Square-foot gardening spacing (plants per square foot)")
NOTE = ("General planting-chart figures: the seed packet's own dates and spacing come first, and a local extension "
        "office knows your area best.")


@dataclass(frozen=True)
class Crop:
    """One crop: how it's started and when (weeks from the last spring frost; negative is before), how many fit a
    square foot, days to harvest (from sowing outside, or from transplanting), frost tolerance, and re-sowing."""
    id: str
    name: str
    start: str  # "indoors", "direct" or "either"
    indoor_weeks: int = 0  # weeks before the last frost to start indoors
    out_weeks: int = 0  # weeks from the last frost to transplant (indoors) or sow outside (direct)
    per_sqft: float = 1.0
    days: int = 60
    frost: str = "tender"  # "hardy", "half-hardy" or "tender"
    again_days: int = 0  # sow again every so many days for a steady harvest (0: once)
    note: str = ""


def _c(*args, **kw):
    """One crop row."""
    return Crop(*args, **kw)


CROPS: dict[str, Crop] = {c.id: c for c in (
    _c("tomato", "Tomatoes", "indoors", 7, 1, 1, 75, "tender", note="stake or cage them; pinch suckers if staked"),
    _c("pepper", "Peppers", "indoors", 8, 2, 1, 70, "tender", note="they want warm soil: wait if nights are cold"),
    _c("eggplant", "Eggplant", "indoors", 8, 2, 1, 75, "tender"),
    _c("basil", "Basil", "indoors", 6, 2, 4, 60, "tender", note="pinch the tips so it bushes out"),
    _c("okra", "Okra", "indoors", 4, 3, 1, 60, "tender"),
    _c("melon", "Melons", "indoors", 3, 2, 0.5, 85, "tender", note="trellised; the vines need the room"),
    _c("watermelon", "Watermelon", "indoors", 3, 2, 0.25, 85, "tender"),
    _c("cucumber", "Cucumbers", "either", 3, 2, 2, 60, "tender", note="on a trellis"),
    _c("zucchini", "Zucchini and summer squash", "either", 3, 1, 0.25, 50, "tender",
       note="one plant takes about a 2 by 2 foot space"),
    _c("winter_squash", "Winter squash", "direct", 0, 2, 0.25, 95, "tender"),
    _c("pumpkin", "Pumpkins", "direct", 0, 2, 0.11, 100, "tender", note="one takes about a 3 by 3 foot space"),
    _c("bean_bush", "Bush beans", "direct", 0, 1, 9, 55, "tender", 14),
    _c("bean_pole", "Pole beans", "direct", 0, 1, 8, 65, "tender", note="on a trellis or poles"),
    _c("corn", "Sweet corn", "direct", 0, 1, 4, 80, "tender", 14, note="plant in blocks, not one row, so it pollinates"),
    _c("sweet_potato", "Sweet potatoes (slips)", "indoors", 6, 3, 1, 100, "tender"),
    _c("lettuce", "Lettuce", "either", 4, -3, 4, 50, "half-hardy", 14, note="bolts in heat: give it afternoon shade"),
    _c("spinach", "Spinach", "direct", 0, -6, 9, 45, "hardy", 14),
    _c("chard", "Swiss chard", "either", 4, -2, 4, 55, "half-hardy"),
    _c("kale", "Kale", "either", 6, -3, 1, 60, "hardy"),
    _c("broccoli", "Broccoli", "indoors", 7, -2, 1, 70, "hardy"),
    _c("cabbage", "Cabbage", "indoors", 7, -3, 1, 75, "hardy"),
    _c("cauliflower", "Cauliflower", "indoors", 7, -2, 1, 75, "half-hardy"),
    _c("peas", "Peas", "direct", 0, -6, 8, 60, "hardy", note="on a trellis"),
    _c("carrot", "Carrots", "direct", 0, -3, 16, 70, "hardy", 21, note="keep the seedbed moist until they come up"),
    _c("beet", "Beets", "direct", 0, -3, 9, 55, "hardy", 21),
    _c("radish", "Radishes", "direct", 0, -4, 16, 25, "hardy", 10),
    _c("turnip", "Turnips", "direct", 0, -3, 9, 50, "hardy"),
    _c("onion", "Onions (sets)", "direct", 0, -4, 9, 100, "hardy"),
    _c("leek", "Leeks", "indoors", 10, -2, 9, 120, "hardy"),
    _c("potato", "Potatoes", "direct", 0, -2, 1, 90, "half-hardy", note="hill soil up around the stems as they grow"),
    _c("cilantro", "Cilantro", "direct", 0, -2, 9, 50, "half-hardy", 21),
    _c("parsley", "Parsley", "indoors", 10, -2, 4, 75, "hardy"),
    _c("dill", "Dill", "direct", 0, 0, 1, 60, "half-hardy"),
)}


def parse_day(text: str, year: int) -> Optional[date]:
    """Pure logic. A frost date as he gives it ("04-20", "2027-04-20", "April 20") in the given year; None if it
    won't read."""
    text = (text or "").strip()
    months = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    try:
        parts = text.replace("/", "-").split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            return date(year, int(parts[0]), int(parts[1]))
        words = text.lower().replace(",", " ").split()
        if len(words) >= 2 and words[0][:3] in months:
            return date(year, months.index(words[0][:3]) + 1, int(words[1]))
    except (ValueError, IndexError):
        return None
    return None


def schedule(crop: Crop, last_frost: date, first_frost: Optional[date] = None) -> dict:
    """Pure logic. One crop's dates from his frosts: {start_indoors, harden_off, out (transplant or sow), how
    ("transplant" or "sow"), harvest, again_days, warning}."""
    indoors = crop.start == "indoors" or (crop.start == "either" and crop.indoor_weeks)
    out = last_frost + timedelta(weeks=crop.out_weeks)
    start = last_frost - timedelta(weeks=crop.indoor_weeks) if indoors else None
    harvest = out + timedelta(days=crop.days)
    warning = ""
    if first_frost is not None and crop.frost == "tender" and harvest > first_frost:
        warning = (f"it needs about {crop.days} days after going out, so it may not ripen before your first fall "
                   "frost: start it earlier indoors, choose a faster variety, or give it cover")
    return {"start_indoors": start, "harden_off": out - timedelta(days=10) if indoors else None, "out": out,
            "how": "transplant" if indoors else "sow", "harvest": harvest, "again_days": crop.again_days,
            "warning": warning}


def plants_for(crop: Crop, sqft: float) -> int:
    """Pure logic. How many of a crop fit a space (square feet), at least one."""
    return max(1, int(math.floor(crop.per_sqft * max(sqft, 0) + 1e-9)))


def bed_soil(length_ft: float, width_ft: float, depth_in: float) -> dict:
    """Pure logic. The soil to fill a raised bed: {cubic_feet, cubic_yards, bags_1_5} (1.5 cubic foot bags)."""
    cubic_feet = max(length_ft, 0) * max(width_ft, 0) * max(depth_in, 0) / 12
    return {"cubic_feet": round(cubic_feet, 1), "cubic_yards": round(cubic_feet / 27, 2),
            "bags_1_5": int(math.ceil(cubic_feet / 1.5 - 1e-9))}


def _when(day: Optional[date]) -> str:
    """Pure logic. A date as a plan says it: "the week of March 15"."""
    return f"the week of {day.strftime('%B')} {day.day}" if day else ""


def layout(beds: list[dict], crops: list[dict]) -> list[dict]:
    """Pure logic. Each crop's place: the bed it's in, its square feet (given, else its share of the bed) and how
    many plants fit. `crops` are {crop, bed, sqft?}; an unknown crop is skipped."""
    by_bed: dict[str, list[dict]] = {}
    for c in crops:
        if c.get("crop") in CROPS:
            by_bed.setdefault(str(c.get("bed") or (beds[0]["name"] if beds else "")), []).append(c)
    placed = []
    for bed in beds:
        here = by_bed.get(bed["name"], [])
        area = float(bed.get("length_ft", 0)) * float(bed.get("width_ft", 0))
        given = sum(float(c.get("sqft") or 0) for c in here)
        share = (area - given) / max(1, sum(1 for c in here if not c.get("sqft"))) if here else 0
        for c in here:
            sqft = float(c.get("sqft") or 0) or max(share, 1)
            crop = CROPS[c["crop"]]
            placed.append({"crop": crop.id, "name": crop.name, "bed": bed["name"], "sqft": round(sqft, 1),
                           "plants": plants_for(crop, sqft)})
    return placed


def stages(beds: list[dict], crops: list[dict], last_frost: date, first_frost: Optional[date] = None) -> list[dict]:
    """Pure logic. The garden as stages of steps (each {do, why, watch, check, when}), in the order they come, only
    the stages it needs; with the beds' soil and every crop's dates from his frosts."""
    placed = layout(beds, crops)
    timed = [(p, CROPS[p["crop"]], schedule(CROPS[p["crop"]], last_frost, first_frost)) for p in placed]
    out: list[dict] = []
    earliest = min([s["start_indoors"] or s["out"] for _p, _c, s in timed], default=last_frost)
    prep = []
    for bed in beds:
        soil = bed_soil(float(bed.get("length_ft", 0)), float(bed.get("width_ft", 0)), float(bed.get("depth_in", 0)))
        fill = (f" Fill it: {soil['cubic_feet']} cubic feet ({soil['cubic_yards']} cubic yards, about "
                f"{soil['bags_1_5']} bags of 1.5 cubic feet) of topsoil mixed with compost.") if bed.get("depth_in") else ""
        prep.append({"do": f"Get {bed['name']} ready ({bed.get('length_ft')} by {bed.get('width_ft')} feet).{fill}",
                     "why": "Loose, rich soil is most of a garden's success; it's easiest to fix before planting.",
                     "watch": ["full sun: six to eight hours a day for most vegetables",
                               "water close by", "no standing water after rain"],
                     "check": "The soil crumbles in your hand and drains after watering.",
                     "when": _when(earliest - timedelta(weeks=2))})
    if prep:
        prep.insert(0, {"do": "Test the soil (a home kit or the extension office's test) for pH and nutrients.",
                        "why": "Most vegetables want a pH of about 6 to 7; the test says what to add instead of "
                               "guessing.", "watch": ["take samples from a few spots, 4 to 6 inches down"],
                        "check": "You have the pH and what the test says to add.",
                        "when": _when(earliest - timedelta(weeks=4))})
        out.append({"name": "Prepare the beds", "steps": prep, "ask": "preparing garden bed soil compost"})
    indoor = sorted([t for t in timed if t[2]["start_indoors"]], key=lambda t: t[2]["start_indoors"])
    if indoor:
        out.append({"name": "Start seeds indoors", "ask": "starting vegetable seeds indoors", "steps": [
            {"do": f"Start {p['name'].lower()} indoors: {p['plants']} for {p['bed']}, plus a few spares.",
             "why": f"It needs a head start: about {c.indoor_weeks} weeks before your last frost.",
             "watch": ["seed-starting mix, not garden soil", "light right above them once they sprout, or they "
                       "stretch", "keep it moist, never soggy"] + ([c.note] if c.note else []),
             "check": "The seedlings have their first true leaves.", "when": _when(s["start_indoors"])}
            for p, c, s in indoor]})
        out.append({"name": "Harden off and transplant", "ask": "hardening off transplanting seedlings", "steps": [
            {"do": f"Harden off the {p['name'].lower()}, then plant {p['plants']} in {p['bed']} "
                   f"({p['sqft']} square feet).",
             "why": "A week or so of outdoor time, a little more each day, keeps them from shock.",
             "watch": ["start in shade and out of wind", "water them in well after planting"]
             + (["warning: " + s["warning"]] if s["warning"] else []),
             "check": "They're in, watered, and standing up the next morning.", "when": _when(s["out"])}
            for p, c, s in sorted(indoor, key=lambda t: t[2]["out"])]})
    direct = sorted([t for t in timed if not t[2]["start_indoors"]], key=lambda t: t[2]["out"])
    if direct:
        out.append({"name": "Sow outside", "ask": "direct sowing vegetable seeds garden", "steps": [
            {"do": f"Sow {p['name'].lower()} in {p['bed']}: {p['sqft']} square feet, about {p['plants']} plants.",
             "why": ("It grows best sown where it will stay" + (f"; sow more every {s['again_days']} days for a "
                     "steady harvest" if s["again_days"] else "") + "."),
             "watch": ["sow at the depth on the packet (about two to three times the seed's size)",
                       "keep the seedbed moist until they come up", "thin to the spacing once they're up"]
             + ([c.note] if c.note else []) + (["warning: " + s["warning"]] if s["warning"] else []),
             "check": "They've come up; thinned to the spacing.", "when": _when(s["out"])} for p, c, s in direct]})
    if timed:
        out.append({"name": "Care through the season", "ask": "vegetable garden watering mulching pests", "steps": [
            {"do": "Mulch around the plants once they're up and the soil is warm.",
             "why": "Mulch holds water in and keeps weeds down.", "watch": ["keep it off the stems"],
             "check": "Two to three inches of mulch, clear of the stems.", "when": _when(last_frost + timedelta(weeks=4))},
            {"do": "Water deeply about once or twice a week (about an inch a week, rain included).",
             "why": "Deep watering grows deep roots; a little every day keeps them shallow.",
             "watch": ["water the soil, not the leaves", "more in heat, less in rain"],
             "check": "A finger pushed into the soil comes out damp a couple of inches down.", "when": ""},
            {"do": "Walk the garden every few days and look under leaves for pests and disease.",
             "why": "Caught early, most problems are a hand-picking, not a lost crop.",
             "watch": ["yellow or spotted leaves", "holes and droppings", "wilting in the morning"],
             "check": "You know what you saw, and what to do about it.", "when": ""}]})
        out.append({"name": "Harvest", "ask": "when to harvest vegetables", "steps": [
            {"do": f"Harvest the {p['name'].lower()} from about {s['harvest'].strftime('%B')} {s['harvest'].day}.",
             "why": f"About {c.days} days after it went out.", "watch": ["pick often: many plants make more when "
                                                                       "picked"],
             "check": "Picked at its best.", "when": _when(s["harvest"])}
            for p, c, s in sorted(timed, key=lambda t: t[2]["harvest"])]})
    return out
