"""
core.units
============

Kitchen and shop units, and converting between them (DEC-0036). A
recipe can say "500 g flour" while the flour is kept in pounds, or
"1 cup honey" while the honey is kept in cups: an amount converts when
both units measure the same thing (weight to weight, volume to volume,
a count to a count). Weight to volume ("cups of flour" against pounds of
flour) needs a density: MIA uses one only for a material on the measured
table (`DENSITIES`, 2026-11-09: King Arthur Baking's ingredient weight
chart, and glycerin's handbook density), matched by the material's name;
anything else she doesn't guess: convert() says None, and the caller
says so plainly.

Any other word is its own count: "3 cloves" against garlic kept in
cloves, "1 jar" against jars. Plurals match ("jar" = "jars"), a count
with no unit matches any count one for one, and a dozen is 12 of
whatever's counted. US measures (a cup is 236.6 ml).

kitchen_amount() says an amount as a cook reads it ("1 ½ cups", "⅓ cup",
"450 g"), for a recipe scaled to more or fewer servings.

Pure logic: no I/O.
"""

from __future__ import annotations

from typing import Optional

# Per unit, in the base unit of its kind (grams, millilitres, each).
_MASS = {"g": 1.0, "kg": 1000.0, "mg": 0.001, "oz": 28.349523125, "lb": 453.59237}
_VOLUME = {"ml": 1.0, "l": 1000.0, "tsp": 4.92892159375, "tbsp": 14.78676478125, "cup": 236.5882365,
           "fl oz": 29.5735295625, "pint": 473.176473, "quart": 946.352946, "gallon": 3785.411784}
_COUNT = {"each": 1.0, "dozen": 12.0}
# Grams per millilitre for materials measured both ways, from King Arthur Baking's Ingredient Weight Chart (grams in a
# US cup, divided by 236.6 ml) and, for glycerin, its handbook density. Matched by a word in the material's name, the
# longest first, so "brown sugar" isn't "sugar". Only what's on this table converts weight to volume.
DENSITIES = {
    "all-purpose flour": 0.507, "bread flour": 0.507, "whole wheat flour": 0.478, "flour": 0.507,
    "brown sugar": 0.900, "powdered sugar": 0.478, "confectioners sugar": 0.478, "sugar": 0.837,
    "honey": 1.420, "maple syrup": 1.319, "molasses": 1.437,
    "water": 1.000, "milk": 0.959, "butter": 0.959,
    "olive oil": 0.845, "coconut oil": 0.917, "vegetable oil": 0.837, "oil": 0.837,
    "table salt": 1.217, "salt": 1.217, "cocoa": 0.355, "rolled oats": 0.376, "oats": 0.376, "rice": 0.837,
    "glycerin": 1.261, "glycerine": 1.261,
}

_ALIASES = {
    "gram": "g", "grams": "g", "gs": "g", "kilogram": "kg", "kilograms": "kg", "kgs": "kg",
    "milligram": "mg", "milligrams": "mg",
    "ounce": "oz", "ounces": "oz", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml", "mls": "ml",
    "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsps": "tsp", "t": "tsp",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsps": "tbsp", "tbs": "tbsp", "tbl": "tbsp",
    "cups": "cup", "c": "cup",
    "floz": "fl oz", "fluid ounce": "fl oz", "fluid ounces": "fl oz", "fl. oz": "fl oz", "fl oz.": "fl oz",
    "pints": "pint", "pt": "pint", "pts": "pint",
    "quarts": "quart", "qt": "quart", "qts": "quart",
    "gallons": "gallon", "gal": "gallon", "gals": "gallon",
    "": "each", "ea": "each", "pc": "each", "pcs": "each", "piece": "each", "pieces": "each",
    "count": "each", "ct": "each", "dozens": "dozen", "doz": "dozen",
}

# Every word that reads as a unit in front of a name, for recipe lines
# ("2 cups honey"). Workshop words stay in core/craft_recipes.UNITS.
WORDS = set(_MASS) | set(_VOLUME) | set(_COUNT) | {a for a in _ALIASES if a and " " not in a and a not in ("t", "c")} | {
    "clove", "cloves", "jar", "jars", "loaf", "loaves", "stick", "sticks", "pinch", "pinches", "dash", "dashes",
    "slice", "slices", "head", "heads", "bunch", "bunches", "sprig", "sprigs", "tin", "tins", "lid", "lids",
    "label", "labels", "bulb", "bulbs", "tray", "trays", "packet", "packets"}


def canonical(unit: str) -> str:
    """The unit's standard spelling ("Cups" → "cup", "lbs" → "lb", "" → "each");
    any other word in its singular form ("jars" → "jar")."""
    u = " ".join(str(unit or "").lower().replace(".", " ").split())
    u = {"fl oz": "fl oz", "fl  oz": "fl oz"}.get(u, u)
    u = _ALIASES.get(u, u)
    if u in _MASS or u in _VOLUME or u in _COUNT:
        return u
    return _singular(u)


def _singular(word: str) -> str:
    """Pure logic. A unit or item word without its plural (loaves to loaf, boxes to box, berries to berry, cups to cup); a word that isn't plural comes back as it is."""
    irregular = {"loaves": "loaf", "halves": "half", "leaves": "leaf", "knives": "knife", "shelves": "shelf"}
    if word in irregular:
        return irregular[word]
    if word.endswith(("ches", "shes", "sses", "xes")):
        return word[:-2]
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        return word[:-1]
    return word


def kind(unit: str) -> str:
    """"mass", "volume", "count" (each/dozen), or the unit's own word for any other count."""
    u = canonical(unit)
    if u in _MASS:
        return "mass"
    if u in _VOLUME:
        return "volume"
    if u in _COUNT:
        return "count"
    return u


def density(material: str) -> Optional[float]:
    """Grams per millilitre for a material named on `DENSITIES` (the longest name it contains), or None."""
    name = " ".join(str(material or "").lower().replace("-", " ").split())
    found = [k for k in DENSITIES if k.replace("-", " ") in name]
    return DENSITIES[max(found, key=len)] if found else None


def convert(quantity: float, from_unit: str, to_unit: str, material: str = "") -> Optional[float]:
    """`quantity` of `from_unit` in `to_unit`, or None when they measure
    different things (cups and pounds, jars and lids). Weight and volume
    convert only for a `material` on the density table (cups of flour
    against pounds of flour)."""
    a, b = canonical(from_unit), canonical(to_unit)
    if a == b:
        return float(quantity)
    for table in (_MASS, _VOLUME, _COUNT):
        if a in table and b in table:
            return float(quantity) * table[a] / table[b]
    per_ml = density(material) if material else None
    if per_ml is not None:
        if a in _VOLUME and b in _MASS:
            return float(quantity) * _VOLUME[a] * per_ml / _MASS[b]
        if a in _MASS and b in _VOLUME:
            return float(quantity) * _MASS[a] / per_ml / _VOLUME[b]
    # A plain count against a named one ("3" jars against "jars", a dozen
    # eggs against "eggs"): one each, since people often leave the unit off.
    named = lambda u: u not in _MASS and u not in _VOLUME and u not in _COUNT  # noqa: E731
    if a in _COUNT and named(b):
        return float(quantity) * _COUNT[a]
    if named(a) and b in _COUNT:
        return float(quantity) / _COUNT[b]
    return None


def grams(quantity: float, unit: str) -> Optional[float]:
    """The weight in grams, when the unit is a weight."""
    return convert(quantity, unit, "g") if kind(unit) == "mass" else None


def amount_text(quantity: float, unit: str) -> str:
    """"2 cups", "0.5 lb", "3 jars", "12": a quantity with its unit, rounded for reading."""
    q = round(float(quantity), 2)
    q_text = f"{q:g}"
    u = str(unit or "").strip()
    if not u or canonical(u) == "each":
        return q_text
    c = canonical(u)
    if c == "cup":
        u = "cup" if q == 1 else "cups"
    elif kind(u) == c and c != "dozen":  # a named count, said as "1 loaf", "3 loaves" however it was typed
        u = c if q == 1 else _plural(c)
    return f"{q_text} {u}"


_FRACTIONS = ((0, ""), (1 / 8, "⅛"), (1 / 4, "¼"), (1 / 3, "⅓"), (1 / 2, "½"), (2 / 3, "⅔"), (3 / 4, "¾"), (1, ""))


def kitchen_amount(quantity: float, unit: str) -> str:
    """A cooking amount as a cook reads it: cups, spoons, pounds, ounces and counts to the nearest kitchen fraction
    ("1 ½ cups", "⅓ cup", "2 ¾ lb", "3 eggs" stays "3"), grams and millilitres as whole numbers ("450 g"), and anything
    over 20 as a whole number. Under ⅛ of a spoon or cup reads "a pinch" for spoons, else the decimal."""
    q = float(quantity)
    u = str(unit or "").strip()
    c = canonical(u)
    if c in ("g", "ml", "mg") or q >= 20:
        return amount_text(round(q), u)
    whole, part = int(q), q - int(q)
    frac, glyph = min(_FRACTIONS, key=lambda f: abs(f[0] - part))
    if frac == 1:
        whole, glyph = whole + 1, ""
    if whole == 0 and not glyph:
        return "a pinch" if c in ("tsp", "tbsp") and q > 0 else amount_text(q, u)
    number = (f"{whole} {glyph}" if whole and glyph else glyph or str(whole)).strip()
    many = whole + frac if glyph else whole
    text = amount_text(many if many > 1 else 1, u)  # the unit, said for this many (one for a fraction under one)
    unit_part = text.split(" ", 1)[1] if " " in text else ""
    return f"{number} {unit_part}".strip()


def _plural(word: str) -> str:
    """Pure logic. A unit or item word's plural (loaf to loaves, knife to knives, box to boxes, berry to berries, cup to cups)."""
    if word in ("loaf", "half", "leaf", "shelf"):
        return word[:-1] + "ves"
    if word == "knife":
        return "knives"
    if word.endswith(("ch", "sh", "s", "x")):
        return word + "es"
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"
