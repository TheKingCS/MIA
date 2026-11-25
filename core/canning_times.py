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
    "peas": (("green pea", "peas", "pea "), 40, 40, "shelled, raw or hot pack"),
    "dry beans": (("dry bean", "dried bean", "pinto", "kidney bean", "navy bean", "black bean"), 75, 90,
                  "soaked and boiled first"),
    "meat": (("beef", "venison", "pork", "lamb", "meat", "stew meat", "ground"), 75, 90, "strips, cubes or ground"),
    "chicken": (("chicken", "poultry", "turkey", "rabbit"), 75, 90, "boneless; bone-in is 65 minutes for pints and 75 for quarts"),
    "stock": (("stock", "broth", "chicken stock", "chicken broth", "beef stock", "beef broth", "bone broth",
               "turkey stock", "venison stock"), 20, 25, "beef or chicken"),
    "fish": (("fish", "trout", "salmon", "bass", "catfish"), 100, None, "pints only"),
}
# food: (words, {jar: (0-1000, 1001-3000, 3001-6000, above 6000 ft) minutes}, the pack)
WATER_BATH = {
    "crushed tomatoes": (("crushed tomato", "tomato"), {"pints": (35, 40, 45, 50), "quarts": (45, 50, 55, 60)},
                         "crushed, with 1 tablespoon bottled lemon juice a pint (2 a quart)"),
    "peaches": (("peach",), {"pints": (20, 25, 30, 35), "quarts": (25, 30, 35, 40)}, "hot pack in syrup or water"),
    "applesauce": (("applesauce", "apple sauce"), {"pints": (15, 20, 20, 25), "quarts": (20, 25, 30, 35)},
                   "hot"),
}
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
    """Pure logic. ("pressure" or "water", the food's name) for the food his words name, longest name first, or None."""
    said = f" {str(words or '').lower()} "
    found = [(len(w), "water", name) for name, (ws, _t, _p) in WATER_BATH.items() for w in ws if w in said]
    found += [(len(w), "pressure", name) for name, (ws, *_rest) in PRESSURE.items() for w in ws if w in said]
    if not found:
        return None
    _n, how, name = max(found)
    return how, name


def jar_in(words: str) -> str:
    """Pure logic. "pints" or "quarts" (half-pints count as pints), else "" when not said: which to say first."""
    said = str(words or "").lower()
    return "quarts" if "quart" in said else "pints" if "pint" in said else ""


def feet_in(words: str) -> Optional[float]:
    """Pure logic. An altitude he said ("at 1,200 feet", "2500 ft elevation", "800 m"), in feet, or None; a bare number
    of three to five digits with no unit after it is feet too (the model passes "chicken, 1500": live check
    2026-11-24), never a count of jars or minutes."""
    got = re.search(r"(\d[\d,]*)\s*(feet|foot|ft|meters?|metres?|m)\b", str(words or ""), re.I)
    if got:
        value = float(got.group(1).replace(",", ""))
        return value * 3.28084 if got.group(2).lower().startswith("m") else value
    bare = re.search(r"(?<![\d.])(\d{1,2},\d{3}|\d{3,5})(?![\d.]|\s*(?:%|lb|pounds?|minutes?|min|jars?|quarts?|pints?))",
                     str(words or ""), re.I)
    return float(bare.group(1).replace(",", "")) if bare else None


def _altitude(context, words: str) -> tuple:
    """(feet, where it came from) from his words, else his town's elevation, else (None, "")."""
    said = feet_in(words)
    if said is not None:
        return said, "the altitude you said"
    try:
        from core import weather

        got = weather.card(context)
        if got.get("elevation") is not None:
            return float(got["elevation"]) * 3.28084, f"{got.get('place') or 'your town'}'s elevation"
    except Exception:  # noqa: BLE001 - no forecast: asked
        pass
    return None, ""


TESTED = ("Follow a tested recipe (the USDA's or the National Center for Home Food Preservation's) for preparing the "
          "food and its headspace.")


def say(context, words: str) -> str:
    """The answer for what he said (see the module's opening)."""
    found = food_in(words)
    if found is None:
        return ("I only give processing times I have from the USDA's tested tables (green beans, corn, carrots, "
                "potatoes, beets, peas, dry beans, meat, chicken, stock, fish, crushed tomatoes, peaches, applesauce). "
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
    """Registers canning_time."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="canning_time", domain="kitchen",
        description="How long to process home-canned jars and at what pressure, from the USDA's tested tables, "
                    "adjusted for his altitude: pressure canning (green beans, corn, meat, chicken, stock...) or a "
                    "boiling-water bath (tomatoes, peaches, applesauce). Logging jars he put up is put_up_jars.",
        parameters={"type": "object", "properties": {
            "question": {"type": "string", "description": "his words: the food, pints or quarts, any altitude"}},
            "required": ["question"]},
        handler=_tool, trigger_phrases=("how long do i process", "how long to process", "processing time",
                                        "process time", "pressure can", "pressure canner", "water bath",
                                        "water-bath", "how long to can", "how long do i can", "canning time",
                                        "what pressure", "how many pounds of pressure"),
    ))
