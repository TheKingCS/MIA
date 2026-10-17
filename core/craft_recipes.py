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

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "craft_recipes.json"

UNITS = {"sheet", "sheets", "board", "boards", "ft", "foot", "feet", "in", "inch", "inches", "lb", "lbs", "oz",
         "gal", "gallon", "gallons", "qt", "quart", "box", "boxes", "pack", "packs", "pc", "pcs", "piece", "pieces",
         "bag", "bags", "can", "cans", "tube", "tubes", "roll", "rolls", "yd", "sqft", "set", "sets", "pair", "pairs",
         "bottle", "bottles", "stick", "sticks", "panel", "panels", "length", "lengths"}
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
            setattr(recipe, name, value if value is not None else "")


# ---------------------------------------------------------------- the math (pure)


def check(recipe: CraftRecipe, materials: list, times: int = 1) -> dict:
    """Pure logic. Each line against the inventory: needed, on hand,
    short, and what the short part costs (the material's cost, else the
    recipe's estimate). `materials` are Material records."""
    by_name = {key(m.name): m for m in materials}
    rows, est_total, short_total, unpriced = [], 0.0, 0.0, 0
    for i, line in enumerate(recipe.lines):
        material = by_name.get(key(line.name))
        need = round(line.quantity * max(1, times), 4)
        have = float(material.quantity_on_hand) if material is not None else 0.0
        short = round(max(0.0, need - have), 4)
        price = material.unit_cost if material is not None and material.unit_cost else line.unit_cost
        if price is None:
            unpriced += 1
        cost = need * (price or 0.0)
        est_total += cost
        short_total += short * (price or 0.0)
        rows.append({"index": i, "name": line.name, "unit": line.unit or (material.unit if material else ""),
                     "need": need, "have": have, "short": short, "unit_cost": price,
                     "material_id": material.material_id if material is not None else "",
                     "status": "ok" if short == 0 else ("short" if material is not None and have > 0 else "missing")})
    return {"times": max(1, times), "rows": rows, "ready": all(r["short"] == 0 for r in rows),
            "est_material_cost": round(est_total, 2), "shopping_cost": round(short_total, 2), "unpriced": unpriced,
            "shopping": [r for r in rows if r["short"] > 0]}


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
