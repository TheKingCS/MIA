"""
core.craft_recipes
====================

Crafting recipes (DEC-0030 phase B; DEC-0028 idea 9): a repeatable
physical project (a bench, a planter box, a refinished dresser) saved as
a recipe, like crafting in an RPG. Nothing is hardcoded: every recipe is
the person's own.

A recipe is what you'd write on a shop card: what it needs (one material
per line, "4 board 2x4 8ft @ 3.98"), dimensions, the cut list, tools,
steps, about how long it takes and what it sells for. It's built on the
Workshop that already exists, never beside it:

- **Materials** (core/material_manager.py) is the inventory. A recipe
  line matches a material by name; **check()** says what's on hand and
  what's short, and the short lines are the **shopping list**.
- **Receiving** what you bought adds it to Materials (creating the
  material the first time) at the price you paid (an average with what
  was there), and records the money as a workshop expense.
- **A build is a Job** (core/job_manager.py) with the recipe's id:
  starting one makes the job; finishing it uses up the materials (at
  their cost then), records the hours and makes the product
  (core/product_manager.py), which a sale (core/ledger_manager.py) sells.
- **A build's profit** = what it sold for − the materials it used − any
  expenses tagged to it. Hours are shown beside it (per hour), never
  folded in. Receiving materials is cash spent on inventory, so it's not
  counted against a build twice.

Batches (DEC-0036, homestead goods): a recipe can make more than one
("12 jars" of hot honey, "6 loaves"), and its lines can be in kitchen
units ("1 cup honey", "500 g flour"). A line is compared with the stock
in the stock's own unit (core/units.py), so the honey kept in cups and
the flour kept in pounds still add up; a line that can't convert (cups
against pounds) says so instead of guessing. `shelf_days` is how long
one keeps (0: it keeps), for the sell-by on each batch.

The store is a household's (both partners share recipes), and writes
through atomic_write_text so every change can be undone.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger
from core.units import WORDS as KITCHEN_UNITS
from core.units import amount_text, convert

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "craft_recipes.json"

UNITS = {"sheet", "sheets", "board", "boards", "ft", "foot", "feet", "in", "inch", "inches", "lb", "lbs", "oz",
         "gal", "gallon", "gallons", "qt", "quart", "box", "boxes", "pack", "packs", "pc", "pcs", "piece", "pieces",
         "bag", "bags", "can", "cans", "tube", "tubes", "roll", "rolls", "yd", "sqft", "set", "sets", "pair", "pairs",
         "bottle", "bottles", "stick", "sticks", "panel", "panels", "length", "lengths"} | KITCHEN_UNITS
# "4 board 2x4 8ft @ 3.98": a quantity only when a space follows it ("2x4"
# alone is a name), an optional "x", then the rest, then an optional "@ price".
_LINE = re.compile(r"^\s*(?:(?P<qty>\d+/\d+|\d+(?:\.\d+)?)\s+(?:x\s+)?)?(?P<rest>.*?)\s*"
                   r"(?:@\s*\$?(?P<cost>\d+(?:\.\d+)?))?\s*$", re.IGNORECASE)


@dataclass
class Line:
    """One thing a recipe needs."""
    quantity: float
    unit: str
    name: str
    unit_cost: Optional[float] = None  # the recipe's estimate, when written with "@ price"


def _qty(text: str) -> float:
    if "/" in text:
        top, bottom = text.split("/", 1)
        return float(top) / float(bottom) if float(bottom) else 0.0
    return float(text)


def parse_lines(text: str) -> list[Line]:
    """Pure logic. "4 board 2x4 8ft @ 3.98" → 4 × board of "2x4 8ft" at
    3.98 each; "Wood glue" → 1 of it. Blank lines and "#" notes skipped."""
    out = []
    for raw in (text or "").splitlines():
        raw = raw.strip().lstrip("-•*").strip()
        if not raw or raw.startswith("#"):
            continue
        m = _LINE.match(raw)
        qty = _qty(m.group("qty")) if m and m.group("qty") else 1.0
        rest = (m.group("rest") if m else raw).strip()
        unit = ""
        first, _, after = rest.partition(" ")
        second, _, after_two = after.partition(" ")
        if first.lower() in ("fl", "fl.") and second.lower().rstrip(".") == "oz" and after_two:
            unit, rest, after = "fl oz", after_two.strip(), ""
        if after and first.lower().rstrip(".") in UNITS:
            unit, rest = first.lower().rstrip("."), after.strip()
        cost = float(m.group("cost")) if m and m.group("cost") else None
        if rest:
            out.append(Line(quantity=qty, unit=unit, name=rest, unit_cost=cost))
    return out


def key(name: str) -> str:
    """Pure logic. How a line's name matches a material's: case and spacing ignored."""
    return " ".join(str(name or "").lower().split())


@dataclass
class CraftRecipe:
    recipe_id: str
    name: str
    category: str = ""  # furniture, planter, shelf... the person's own words
    description: str = ""
    dimensions: str = ""
    materials: str = ""  # one per line; parse_lines()
    cut_list: str = ""
    tools: str = ""
    steps: str = ""  # one per line
    est_hours: float = 0.0
    price: float = 0.0  # what one sells for (0: not for sale)
    notes: str = ""
    product_id: str = ""  # the finished-goods product its builds make
    # DEC-0036 (batches): one build or batch makes this many ("12" "jars"),
    # keeps this many days (0: it keeps), and its label's parts.
    makes: float = 1.0
    makes_unit: str = ""
    shelf_days: int = 0
    net_amount: str = ""  # on the label: "8 oz", "1 loaf (24 oz)"
    allergens: str = ""  # on the label: "Contains: wheat, milk"
    label_ingredients: str = ""  # on the label, when not the recipe's own lines
    created_at: str = ""
    updated_at: str = ""

    @property
    def lines(self) -> list[Line]:
        return parse_lines(self.materials)

    @property
    def step_list(self) -> list[str]:
        return [s.strip().lstrip("-•*").strip() for s in (self.steps or "").splitlines() if s.strip()]

    @staticmethod
    def from_dict(d: dict) -> "CraftRecipe":
        known = CraftRecipe.__dataclass_fields__
        return CraftRecipe(**{k: v for k, v in d.items() if k in known})


class CraftRecipeBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._recipes: list[CraftRecipe] = []
        self._load()

    def _load(self) -> None:
        self._recipes = []
        if not self._file.exists():
            return
        try:
            self._recipes = [CraftRecipe.from_dict(d) for d in json.loads(self._file.read_text(encoding="utf-8"))]
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("craft_recipes.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps([asdict(r) for r in self._recipes], indent=2))

    def all_recipes(self) -> list[CraftRecipe]:
        return sorted(self._recipes, key=lambda r: r.name.lower())

    def get_recipe(self, recipe_id: str) -> Optional[CraftRecipe]:
        return next((r for r in self._recipes if r.recipe_id == recipe_id), None)

    def add_recipe(self, name: str, **fields) -> CraftRecipe:
        if not str(name or "").strip():
            raise ValueError("A recipe needs a name.")
        now = datetime.now().isoformat(timespec="seconds")
        recipe = CraftRecipe(recipe_id=uuid.uuid4().hex[:10], name=name.strip(), created_at=now, updated_at=now)
        self._apply(recipe, fields)
        self._recipes.append(recipe)
        self._save()
        return recipe

    def update_recipe(self, recipe_id: str, **fields) -> CraftRecipe:
        recipe = self.get_recipe(recipe_id)
        if recipe is None:
            raise ValueError("That recipe isn't there anymore.")
        self._apply(recipe, fields)
        recipe.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return recipe

    def delete_recipe(self, recipe_id: str) -> None:
        self._recipes = [r for r in self._recipes if r.recipe_id != recipe_id]
        self._save()

    @staticmethod
    def _apply(recipe: CraftRecipe, fields: dict) -> None:
        for name, value in fields.items():
            if name in ("recipe_id", "created_at", "updated_at") or not hasattr(recipe, name):
                raise ValueError(f"A recipe has no '{name}'.")
            if name in ("est_hours", "price"):
                value = max(0.0, float(value or 0))
            elif name == "makes":
                value = float(value or 0) or 1.0
                if value <= 0:
                    raise ValueError("A recipe makes at least one.")
            elif name == "shelf_days":
                value = max(0, int(float(value or 0)))
            setattr(recipe, name, value if value is not None else "")


# ---------------------------------------------------------------- the math (pure)


def _stock_amount(line: Line, quantity: float, material) -> Optional[float]:
    """Pure logic. `quantity` of the line in the material's own unit, or
    None when they can't be compared (cups against pounds)."""
    if material is None:
        return quantity
    return convert(quantity, line.unit, material.unit or "")


def check(recipe: CraftRecipe, materials: list, times: int = 1) -> dict:
    """Pure logic. Each line against the inventory: needed, on hand,
    short, and what the short part costs (the material's cost, else the
    recipe's estimate). `materials` are Material records. Amounts are in
    the material's unit when it's in stock (converted from the recipe's
    unit); a line whose unit can't convert is a `mismatch` and counts as
    neither had nor short."""
    by_name = {key(m.name): m for m in materials}
    rows, est_total, short_total, unpriced, mismatched = [], 0.0, 0.0, 0, 0
    for i, line in enumerate(recipe.lines):
        material = by_name.get(key(line.name))
        recipe_need = round(line.quantity * max(1, times), 4)
        converted = _stock_amount(line, recipe_need, material)
        mismatch = converted is None
        need = round(recipe_need if mismatch else converted, 4)
        unit = line.unit if (mismatch or material is None) else (material.unit or line.unit)
        have = float(material.quantity_on_hand) if material is not None else 0.0
        short = 0.0 if mismatch else round(max(0.0, need - have), 4)
        stock_priced = material is not None and bool(material.unit_cost) and not mismatch
        price = material.unit_cost if stock_priced else line.unit_cost  # else the recipe's estimate, per its unit
        if price is None:
            unpriced += 1
        # A stock price is per the stock's unit; the recipe's own is per the line's.
        est_total += (need if stock_priced else recipe_need) * (price or 0.0)
        short_total += (short if stock_priced else (short / need * recipe_need if need else 0.0)) * (price or 0.0)
        mismatched += 1 if mismatch else 0
        status = "check" if mismatch else ("ok" if short == 0 else ("short" if material is not None and have > 0 else "missing"))
        rows.append({"index": i, "name": line.name, "unit": unit, "need": need, "have": have, "short": short,
                     "unit_cost": price if stock_priced or price is None or need == recipe_need
                     else round(price * recipe_need / need, 4),
                     "material_id": material.material_id if material is not None else "",
                     "recipe_text": amount_text(recipe_need, line.unit),
                     "have_text": amount_text(have, material.unit if material is not None else unit),
                     "after": round(have - need, 4) if material is not None and not mismatch else None,
                     "mismatch": mismatch, "status": status})
    makes = max(float(getattr(recipe, "makes", 1) or 1), 0.0001) * max(1, times)
    return {"times": max(1, times), "rows": rows, "ready": all(r["short"] == 0 for r in rows) and not mismatched,
            "est_material_cost": round(est_total, 2), "shopping_cost": round(short_total, 2), "unpriced": unpriced,
            "mismatched": mismatched, "makes": makes,
            "per_piece": round(est_total / makes, 2) if est_total else 0.0,
            "shopping": [r for r in rows if r["short"] > 0]}


def uses(recipe: CraftRecipe, materials: list, times: int = 1) -> dict:
    """Pure logic. What a batch takes out of stock: (material, amount in
    its unit) for each line that's in stock and converts; the names of
    lines not in stock, and of lines whose units can't convert."""
    by_name = {key(m.name): m for m in materials}
    used, missing, mismatched = [], [], []
    for line in recipe.lines:
        material = by_name.get(key(line.name))
        if material is None:
            missing.append(line.name)
            continue
        amount = _stock_amount(line, line.quantity * max(1, times), material)
        if amount is None:
            mismatched.append(f"{line.name} ({line.unit or 'count'} vs {material.unit or 'count'})")
        else:
            used.append((material, round(amount, 4)))
    return {"used": used, "missing": missing, "mismatched": mismatched}


def makes_count(recipe: CraftRecipe, times: int = 1) -> float:
    return float(getattr(recipe, "makes", 1) or 1) * max(1, times)


def makes_text(recipe: CraftRecipe, times: int = 1) -> str:
    """"24 jars", "2 × Bench": what this many builds or batches make."""
    count = makes_count(recipe, times)
    unit = getattr(recipe, "makes_unit", "") or ""
    if unit:
        return amount_text(count, unit)
    return f"{count:g} × {recipe.name}" if count != 1 else recipe.name


def average_cost(have: float, old_cost: float, bought: float, paid_each: float) -> float:
    """Pure logic. The material's cost after buying more: the average of
    what was there and what came in (just the new price when none was)."""
    if have <= 0 or old_cost <= 0:
        return round(paid_each, 4)
    if bought <= 0:
        return old_cost
    return round((have * old_cost + bought * paid_each) / (have + bought), 4)


def build_result(job, sales: list, expenses: list) -> dict:
    """Pure logic. One build's money: what it sold for, the materials it
    used (at their cost when used), other expenses tagged to it, profit,
    and per hour."""
    materials = round(sum(e.quantity_used * (e.unit_cost or 0.0) for e in job.material_consumption), 2)
    other = round(sum(x.amount for x in expenses if x.job_id == job.job_id), 2)
    sold = round(sum(s.amount for s in sales if s.job_id == job.job_id), 2)
    cost = round(materials + other, 2)
    profit = round(sold - cost, 2)
    hours = float(job.labor_hours or 0.0)
    return {"sold": sold, "materials": materials, "other": other, "cost": cost, "profit": profit,
            "hours": hours, "per_hour": round(profit / hours, 2) if hours and sold else None, "is_sold": bool(sold)}
