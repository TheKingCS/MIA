"""
tools.make_food_table
=======================

Builds data/foods.tsv, MIA's built-in food table (DEC-0020), from the
USDA's FoodData Central "SR Legacy" download: about 7,800 everyday foods,
public domain (CC0, https://fdc.nal.usda.gov). Kept per 100 g: calories,
protein, fat, carbohydrate, fiber, sugars, sodium; plus each food's
household measures in grams ("cup", "tbsp", "large"...), so "2 cups
rice" can become grams. core/food_table.py reads it.

Run by the "Food table" workflow (GitHub can reach the USDA; MIA's own
development machine can't): `python -m tools.make_food_table <unzipped folder> data/foods.tsv`.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# FoodData Central nutrient ids -> MIA's columns.
NUTRIENTS = {
    "1008": "kcal", "1003": "protein_g", "1004": "fat_g", "1005": "carbs_g",
    "1079": "fiber_g", "2000": "sugar_g", "1093": "sodium_mg",
}
COLUMNS = ["fdc_id", "name", "category", *NUTRIENTS.values(), "portions"]


def _find(folder: Path, name: str) -> Path:
    found = sorted(folder.rglob(name))
    if not found:
        raise SystemExit(f"{name} isn't in {folder}")
    return found[0]


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def _number(text: str) -> str:
    """Rounded for a small file: 1 decimal (3 significant digits is plenty)."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return ""
    return f"{value:.1f}".rstrip("0").rstrip(".") if value else "0"


def _portion_name(row: dict, units: dict) -> str:
    """ "1 cup, chopped" -> "cup"; "1 large" -> "large". Lowercase, the
    first words before a comma or parenthesis."""
    unit = units.get(row.get("measure_unit_id", ""), "")
    text = (row.get("modifier") or row.get("portion_description") or "").strip()
    if unit and unit.lower() not in ("undetermined", ""):
        text = unit
    text = text.split(",")[0].split("(")[0].strip().lower()
    return text.replace("\t", " ").replace("|", "/").replace(":", " ")[:30]


def build(folder: Path) -> list[dict]:
    foods: dict[str, dict] = {}
    categories = {r["id"]: r["description"] for r in _rows(_find(folder, "food_category.csv"))}
    for r in _rows(_find(folder, "food.csv")):
        foods[r["fdc_id"]] = {"fdc_id": r["fdc_id"], "name": r["description"].replace("\t", " "),
                              "category": categories.get(r.get("food_category_id", ""), "")}
    for r in _rows(_find(folder, "food_nutrient.csv")):
        column = NUTRIENTS.get(r["nutrient_id"])
        food = foods.get(r["fdc_id"])
        if column and food is not None:
            food[column] = _number(r["amount"])
    units = {}
    unit_file = sorted(folder.rglob("measure_unit.csv"))
    if unit_file:
        units = {r["id"]: r["name"] for r in _rows(unit_file[0])}
    portions: dict[str, dict] = {}
    for r in _rows(_find(folder, "food_portion.csv")):
        try:
            amount = float(r.get("amount") or 1) or 1
            grams = float(r["gram_weight"]) / amount  # grams for ONE of the measure
        except (KeyError, ValueError):
            continue
        name = _portion_name(r, units)
        if name and grams > 0:
            portions.setdefault(r["fdc_id"], {}).setdefault(name, round(grams, 1))
    out = []
    for fdc_id, food in foods.items():
        if "kcal" not in food:
            continue  # no energy value: not useful for MIA
        food["portions"] = "|".join(f"{n}:{g:g}" for n, g in portions.get(fdc_id, {}).items())
        out.append({c: food.get(c, "") for c in COLUMNS})
    return sorted(out, key=lambda f: f["name"].lower())


def main(folder: str, out: str) -> int:
    rows = build(Path(folder))
    with open(out, "w", newline="", encoding="utf-8") as f:
        f.write("# MIA's food table (DEC-0020): USDA FoodData Central SR Legacy, public domain (CC0).\n")
        f.write("# Per 100 g. Built by tools/make_food_table.py; don't edit by hand.\n")
        writer = csv.DictWriter(f, COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} foods -> {out}")
    return 0 if len(rows) > 1000 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
