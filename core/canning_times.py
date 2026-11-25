"""
core.canning_times
====================

"How long do I process quarts of green beans?" (Jarvis brainstorm, round 12; canning is one of his skills): processing
times from the USDA's Complete Guide to Home Canning (2015), with the pressure or the time adjusted for his altitude,
worked out in code and never from the model's memory. A food not in the table is never guessed: he's pointed to a
tested recipe.

- **Pressure canning** (`PRESSURE`: low-acid foods: vegetables, meat, poultry, fish, stock, beans): the minutes don't
  change with altitude; the pressure does (`pressure_for`): a weighted gauge at 10 lb up to 1,000 ft and 15 lb above;
  a dial gauge at 11 lb up to 2,000 ft, 12 to 4,000, 13 to 6,000, 14 to 8,000.
- **Boiling-water canning** (`WATER_BATH`: acid foods): each food's own minutes at each altitude band (0-1,000,
  1,001-3,000, 3,001-6,000, above 6,000 ft), as the USDA's tables give them.
- **His altitude**: the feet he says, else his town's elevation from the weather service (core/weather.card, kept
  with the forecast), else asked for.

Always with: follow a tested recipe for how the food is prepared and its headspace, and vent the canner 10 minutes
before pressure. Read-only.

**Checked** 2026-11-24 against the National Center for Home Food Preservation's pages of the USDA guide
(nchfp.uga.edu/how/can/...: each food's page, all 16 tables and both gauge tables matched). Their notes kept here:
potatoes, beets, dried beans, ground meat and stock are hot pack only; the fish time is tested only for fatty fish
(salmon, trout, steelhead, mackerel, bluefish), so a lean fish like bass or catfish gets no time; never white-flesh
peaches in a water bath; crushed tomatoes always acidified.
Foods are matched as whole words, a near miss of a tested food gets no time (NOT_THESE), and a bare number is an
altitude only when his town's elevation isn't known (`bare_feet`).
"""

from __future__ import annotations

import re
from typing import Optional

# food: (words that name it, pints minutes, quarts minutes or None when quarts aren't tested, the pack it's for)
PRESSURE = {
    "green beans": (("green bean", "snap bean", "string bean", "wax bean"), 20, 25, "raw or hot pack"),
    "corn": (("corn",), 55, 85, "whole kernel, raw or hot pack"),
    "carrots": (("carrot",), 25, 30, "sliced or diced"),
    "potatoes": (("potato",), 35, 40, "cubed, hot pack"),
    "beets": (("beet",), 30, 35, "hot pack"),
    "peas": (("green pea", "english pea", "pea"), 40, 40, "green or English, shelled, raw or hot pack"),
    "dry beans": (("dry bean", "dried bean", "pinto", "kidney bean", "navy bean", "black bean", "dried pea",
                   "dry pea", "chickpea", "garbanzo"), 75, 90, "beans or peas, dried: soaked and boiled first"),
    "meat": (("beef", "venison", "pork", "lamb", "meat", "stew meat", "ground"), 75, 90,
             "strips or cubes, hot or raw pack; ground, hot pack"),
    "chicken": (("chicken", "poultry", "turkey", "rabbit"), 75, 90, "boneless; bone-in is 65 minutes for pints and 75 for quarts"),
    "stock": (("stock", "broth", "chicken stock", "chicken broth", "beef stock", "beef broth", "bone broth",
               "turkey stock", "venison stock"), 20, 25, "beef or chicken"),
    "fish": (("trout", "salmon", "steelhead", "mackerel", "bluefish"), 100, None,
             "salmon, trout, steelhead, mackerel or bluefish, raw pack, pints only"),
}
# food: (words, {jar: (0-1000, 1001-3000, 3001-6000, above 6000 ft) minutes}, the pack)
WATER_BATH = {
    "crushed tomatoes": (("crushed tomato",), {"pints": (35, 40, 45, 50), "quarts": (45, 50, 55, 60)},
                         "crushed, with 1 tablespoon bottled lemon juice a pint (2 a quart)"),
    "peaches": (("peach",), {"pints": (20, 25, 30, 35), "quarts": (25, 30, 35, 40)},
                "yellow, hot pack in syrup or water; never white-flesh peaches"),
    "applesauce": (("applesauce", "apple sauce"), {"pints": (15, 20, 20, 25), "quarts": (20, 25, 30, 35)},
                   "hot"),
}
# Foods whose names come close to a tested one but whose times differ (review 2026-11-24: sweet potatoes got the
# potatoes' 35/40 against the USDA's 65/90, acorn squash and corned beef corn's, smoked salmon salmon's 100 against
# 110, whole tomatoes the crushed ones'): never a time; the tested-recipe answer instead.
NOT_THESE = re.compile(r"\b(sweet potato\w*|yams?|acorn|butternut|squash|pumpkins?|split peas?|black.?eyed|"
                       r"field peas?|cream.?style|corned|smoked|soups?|chili|salsa|pie filling|jams?|jelly|pickl\w*|"
                       r"ground cherr\w*)\b", re.I)
BANDS = ((1000, "up to 1,000 ft"), (3000, "1,001 to 3,000 ft"), (6000, "3,001 to 6,000 ft"), (None, "above 6,000 ft"))
DIAL = ((2000, 11), (4000, 12), (6000, 13), (8000, 14))


def pressure_for(feet: float) -> tuple:
    """Pure logic. (weighted gauge lb, dial gauge lb or None above 8,000 ft) at an altitude."""
    weighted = 10 if feet <= 1000 else 15
    dial = next((lb for top, lb in DIAL if feet <= top), None)
    return weighted, dial


def band(feet: float) -> int:
    """Pure logic. Which water-bath altitude column (0 to 3)."""
    return next(i for i, (top, _w) in enumerate(BANDS) if top is None or feet <= top)


def food_in(words: str) -> Optional[tuple]:
    """Pure logic. ("pressure" or "water", the food's name) for the food his words name first (a follow-up's own words
    first: "and corn? (after: ...green beans?)"), as whole words, the longer name where two start together ("chicken
    stock" over "chicken"); None for a food not in the table or a near miss of one (`NOT_THESE`)."""
    text = str(words or "").lower()
    own, _sep, before = text.partition(" (after:")
    for said in (own, before):
        if NOT_THESE.search(said) or ("tomato" in said and "crushed" not in said):
            return None  # a near miss of a tested food (or tomatoes not crushed): no time from this table
        found = []
        for how, table in (("water", WATER_BATH), ("pressure", PRESSURE)):
            for name, (ws, *_rest) in table.items():
                for w in ws:  # whole words, a plural allowed ("potatoes", "peas"), never inside another
                    hit = re.search(rf"\b{re.escape(w)}(?:e?s)?\b", said)
                    if hit:
                        found.append((hit.start(), -len(w), how, name))
        if found:
            _at, _n, how, name = min(found)
            return how, name
    return None


def jar_in(words: str) -> str:
    """Pure logic. "pints" or "quarts" (half-pints count as pints), else "" when not said: which to say first."""
    said = str(words or "").lower()
    return "quarts" if "quart" in said else "pints" if "pint" in said else ""


def feet_in(words: str) -> Optional[float]:
    """Pure logic. An altitude he said with its unit ("at 1,200 feet", "2500 ft elevation", "800 m"), in feet, or None.
    A bare number is `bare_feet`'s, used only when his town's elevation isn't known."""
    got = re.search(r"(\d[\d,]*)\s*(feet|foot|ft|meters?|metres?|m)\b", str(words or ""), re.I)
    if got:
        value = float(got.group(1).replace(",", ""))
        return value * 3.28084 if got.group(2).lower().startswith("m") else value
    return None


def bare_feet(words: str) -> Optional[float]:
    """Pure logic. A bare number of three to five digits read as feet (the model passes "chicken, 1500": live check
    2026-11-24); never a year (1900 to 2099), a temperature ("240 degrees"), a count of jars, minutes or pounds."""
    for hit in re.finditer(r"(?<![\d.])(\d{1,2},\d{3}|\d{3,5})(?![\d.]|\s*(?:%|°|degrees?|lb|pounds?|minutes?|min|"
                           r"jars?|quarts?|pints?))", str(words or ""), re.I):
        value = float(hit.group(1).replace(",", ""))
        if not 1900 <= value <= 2099:
            return value
    return None


def _altitude(context, words: str) -> tuple:
    """(feet, where it came from) from an altitude he said with its unit, else his town's elevation, else a bare
    number (`bare_feet`), else (None, ""): a bare number never overrides a known elevation (review 2026-11-24:
    "in my 921" gave 10 lb where a town at 5,000 ft needs 15)."""
    said = feet_in(words)
    if said is not None:
        return said, "the altitude you said"
    try:
        from core import weather

        got = weather.card(context)
        if got.get("elevation") is not None:
            return float(got["elevation"]) * 3.28084, f"{got.get('place') or 'your town'}'s elevation"
    except Exception:  # noqa: BLE001 - no forecast: a bare number, else asked
        pass
    bare = bare_feet(words)
    return (bare, "the altitude you said") if bare is not None else (None, "")


TESTED = ("Follow a tested recipe (the USDA's or the National Center for Home Food Preservation's) for preparing the "
          "food and its headspace.")


def say(context, words: str) -> str:
    """The answer for what he said (see the module's opening).
    A lean fish (bass, catfish) isn't in the USDA's tested fish time, so it gets the tested-recipe answer, never 100
    minutes.
    The altitude: one he said with its unit, else his town's, else a bare number."""
    found = food_in(words)
    if found is None:
        return ("I only give processing times I have from the USDA's tested tables (green beans, corn, carrots, "
                "potatoes, beets, green peas, dried beans or peas, meat, chicken, stock, salmon or trout, crushed "
                "tomatoes, peaches, applesauce). "
                "For anything else, use a tested recipe from the National Center for Home Food Preservation; never "
                "guess a time.")
    how, name = found
    jar = jar_in(words)
    feet, source = _altitude(context, words)
    if how == "pressure":
        _ws, pints, quarts, pack = PRESSURE[name]
        # both sizes always (the model names a jar he never said: live check 2026-11-24), the one asked first
        times = (f"{pints} minutes for pints" + (f" and {quarts} for quarts" if quarts else ", pints only: quarts "
                                                 "aren't tested"))
        if jar == "quarts" and quarts:
            times = f"{quarts} minutes for quarts and {pints} for pints"
        out = f"{name.capitalize()} ({pack}) go in the pressure canner: {times}."
        if feet is None:
            out += (" The pressure depends on your altitude: a weighted gauge at 10 lb up to 1,000 ft, 15 above; a "
                    "dial gauge at 11 lb up to 2,000 ft, more above. Tell me your elevation and I'll say yours.")
        else:
            weighted, dial = pressure_for(feet)
            out += (f" At {feet:,.0f} ft ({source}): {weighted} lb on a weighted gauge"
                    + (f", or {dial} lb on a dial gauge." if dial else "; above 8,000 ft, check your canner's manual "
                       "for a dial gauge."))
        out += " Vent the canner 10 minutes before you bring it to pressure, and let it come down on its own."
        return out + " " + TESTED
    _ws, table, pack = WATER_BATH[name]
    jars = sorted(table, key=lambda j: j != jar)  # both sizes, the one asked first
    if feet is None:
        said = "; ".join(f"{j}: {table[j][0]} minutes up to 1,000 ft, {table[j][1]} to 3,000, {table[j][2]} to "
                         f"6,000, {table[j][3]} above" for j in jars)
        return f"{name.capitalize()} ({pack}) go in a boiling-water canner: {said}. " + TESTED
    i = band(feet)
    said = " and ".join(f"{table[j][i]} minutes for {j}" for j in jars)
    return (f"{name.capitalize()} ({pack}) go in a boiling-water canner: at {feet:,.0f} ft ({source}, "
            f"{BANDS[i][1]}), {said}, counted from when the water's at a full boil over the jars. " + TESTED)


def _tool(context, arguments: dict) -> str:
    """Tool canning_time: `say` on his words."""
    return say(context, " ".join(str(arguments.get(k) or "") for k in ("question", "food", "jar", "altitude")))


def register_canning_time_actions(registry) -> None:
    """Registers canning_time.
    Reached by "what pressure to can...", never a bare "what pressure" (tires).
    His own words, never the model's (`prompt_arg`)."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="canning_time", domain="kitchen",
        description="How long to process home-canned jars and at what pressure, from the USDA's tested tables, "
                    "adjusted for his altitude: pressure canning (green beans, corn, meat, chicken, stock...) or a "
                    "boiling-water bath (tomatoes, peaches, applesauce). Logging jars he put up is put_up_jars.",
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "his words: the food, pints or quarts, any altitude"}},
            "required": ["question"]},
        handler=_tool, prompt_arg="question",  # his own words, never the model's (live check 2026-11-25: it sent the tool's description)
        trigger_phrases=("how long do i process", "how long to process", "processing time",
                                        "process time", "pressure can", "pressure canner", "water bath",
                                        "water-bath", "how long to can", "how long do i can", "canning time",
                                        "pressure to can", "pressure for canning", "pressure should i can",
                                        "pressure do i can", "pounds of pressure for"),
    ))
