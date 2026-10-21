"""
core.goods
============

Homestead goods on hand (DEC-0036): what's made and not yet sold, batch
by batch. No store of its own: a batch is a finished build
(core/job_manager.py, with its recipe and `finished_at`), what it made
is its products_produced, what sold is the Ledger's sales tagged with
the batch (`job_id`), and what was tossed is the batch's `tossed`. So
the numbers can't drift from the books.

- `lots()`: each batch with something left: made, sell-by (made + the
  recipe's shelf_days), days left, and its freshness.
- `fifo()`: which batches a sale comes out of, oldest first.
- `market_summary()` / `demand()`: what a market day sold, and what
  usually sells, for how many to make.

Pure logic: no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class Lot:
    job_id: str
    recipe_id: str
    name: str
    made: str  # YYYY-MM-DD
    sell_by: str  # YYYY-MM-DD, "" when it keeps
    produced: float
    sold: float
    tossed: float
    unit_cost: float  # what one cost to make (the batch's materials ÷ what it made)

    @property
    def left(self) -> float:
        return round(max(0.0, self.produced - self.sold - self.tossed), 4)


def _day(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(str(text or "")[:10])
    except ValueError:
        return None


def lots(jobs: list, recipes: dict, sales: list, include_empty: bool = False) -> list[Lot]:
    """Pure logic. Every finished batch made from a recipe, oldest first
    (only those with some left, unless `include_empty`). `recipes` maps
    recipe_id → CraftRecipe."""
    sold_by_job: dict[str, float] = {}
    for s in sales:
        if s.job_id:
            sold_by_job[s.job_id] = sold_by_job.get(s.job_id, 0.0) + float(s.quantity_sold or 0)
    out = []
    for job in jobs:
        if not job.recipe_id or job.status != "Complete":
            continue
        recipe = recipes.get(job.recipe_id)
        produced = sum(float(p.quantity_produced or 0) for p in job.products_produced)
        if produced <= 0:
            continue
        made = (job.finished_at or job.updated_at or job.created_at or "")[:10]
        shelf = int(getattr(recipe, "shelf_days", 0) or 0) if recipe is not None else 0
        made_day = _day(made)
        sell_by = (made_day + timedelta(days=shelf)).isoformat() if shelf and made_day else ""
        materials = sum(e.quantity_used * (e.unit_cost or 0.0) for e in job.material_consumption)
        lot = Lot(job_id=job.job_id, recipe_id=job.recipe_id, name=recipe.name if recipe is not None else job.name,
                  made=made, sell_by=sell_by, produced=produced, sold=sold_by_job.get(job.job_id, 0.0),
                  tossed=float(job.tossed or 0), unit_cost=round(materials / produced, 4))
        if include_empty or lot.left > 0:
            out.append(lot)
    return sorted(out, key=lambda lot: (lot.made, lot.job_id))


def freshness(lot: Lot, today: date) -> dict:
    """Pure logic. "keeps" (no shelf life), "fresh", "sell first" (the
    last quarter of its shelf life, at least the last day) or "past"
    (past its sell-by), with the days left."""
    sell_by = _day(lot.sell_by)
    if sell_by is None:
        return {"state": "keeps", "days_left": None}
    days_left = (sell_by - today).days
    made = _day(lot.made) or today
    shelf = max(1, (sell_by - made).days)
    if days_left < 0:
        state = "past"
    elif days_left <= max(1, shelf // 4):
        state = "sell first"
    else:
        state = "fresh"
    return {"state": state, "days_left": days_left}


def fifo(lots_for_recipe: list[Lot], quantity: float) -> list[tuple[Lot, float]]:
    """Pure logic. Where `quantity` comes from, oldest batch first. Takes
    no more than what's left; the caller checks for a shortfall."""
    out, wanted = [], float(quantity)
    for lot in sorted(lots_for_recipe, key=lambda lot: (lot.made, lot.job_id)):
        if wanted <= 0:
            break
        take = min(lot.left, wanted)
        if take > 0:
            out.append((lot, round(take, 4)))
            wanted = round(wanted - take, 4)
    return out


def split_amount(amount: float, parts: list[float]) -> list[float]:
    """Pure logic. `amount` split in proportion to `parts`, in cents, the
    last part taking the rounding so the pieces add up exactly."""
    total = sum(parts)
    if not parts or total <= 0:
        return [round(amount, 2)] + [0.0] * (len(parts) - 1) if parts else []
    out, given = [], 0.0
    for i, p in enumerate(parts):
        if i == len(parts) - 1:
            out.append(round(amount - given, 2))
        else:
            piece = round(amount * p / total, 2)
            out.append(piece)
            given = round(given + piece, 2)
    return out


def market_summary(market, sales: list, lots_all: list[Lot]) -> dict:
    """Pure logic. One market day: per recipe, how many were brought, sold
    and left, the money, and what the sold ones cost to make (their
    batches' cost each). `sales` are the Ledger's revenue entries; the
    day's are the ones noted with its tag."""
    tag = market_tag(market.market_id)
    by_job = {lot.job_id: lot for lot in lots_all}
    rows: dict[str, dict] = {}
    for recipe_id, brought in (market.brought or {}).items():
        rows[recipe_id] = {"recipe_id": recipe_id, "brought": float(brought), "sold": 0.0, "revenue": 0.0, "cost": 0.0}
    for s in sales:
        if (s.notes or "") != tag:
            continue
        lot = by_job.get(s.job_id)
        recipe_id = lot.recipe_id if lot is not None else ""
        row = rows.setdefault(recipe_id, {"recipe_id": recipe_id, "brought": 0.0, "sold": 0.0, "revenue": 0.0, "cost": 0.0})
        row["sold"] += float(s.quantity_sold or 0)
        row["revenue"] += float(s.amount or 0)
        row["cost"] += float(s.quantity_sold or 0) * (lot.unit_cost if lot is not None else 0.0)
    for row in rows.values():
        row["left"] = round(max(0.0, row["brought"] - row["sold"]), 4) if row["brought"] else 0.0
        row["revenue"], row["cost"] = round(row["revenue"], 2), round(row["cost"], 2)
    revenue = round(sum(r["revenue"] for r in rows.values()), 2)
    cost = round(sum(r["cost"] for r in rows.values()), 2)
    return {"rows": list(rows.values()), "revenue": revenue, "cost": cost, "profit": round(revenue - cost, 2),
            "sold": round(sum(r["sold"] for r in rows.values()), 4)}


def market_tag(market_id: str) -> str:
    return f"market:{market_id}"


def demand(markets: list, summaries: dict) -> dict:
    """Pure logic. Per recipe over the closed market days it was brought
    to: how many it sold on average, how often it sold out, and how many
    to bring (the average, plus a little when it sold out, rounded up)."""
    import math

    seen: dict[str, list[dict]] = {}
    for market in markets:
        if market.status != "closed":
            continue
        for row in summaries.get(market.market_id, {}).get("rows", []):
            if row["brought"]:
                seen.setdefault(row["recipe_id"], []).append(row)
    out = {}
    for recipe_id, rows in seen.items():
        avg = sum(r["sold"] for r in rows) / len(rows)
        sold_out = sum(1 for r in rows if r["left"] <= 0)
        bring = math.ceil(avg * (1.25 if sold_out * 2 >= len(rows) else 1.0))
        out[recipe_id] = {"markets": len(rows), "avg_sold": round(avg, 1), "sold_out": sold_out, "bring": bring}
    return out


# What's packaging, not an ingredient, when a label lists ingredients.
_PACKAGING = ("jar", "lid", "label", "bag", "box", "bottle", "tin", "wrap", "sticker", "ribbon", "carton", "tag")


def label_ingredients(recipe) -> dict:
    """Pure logic. The ingredients for a label: the recipe's own list when
    it has one, else its lines minus packaging, heaviest first when every
    line is a weight (or every one a volume), else as written. `ordered`
    says whether MIA could put them in order."""
    from core.units import convert, kind

    own = str(getattr(recipe, "label_ingredients", "") or "").strip()
    if own:
        return {"text": own, "ordered": True, "own": True}
    lines = [line for line in recipe.lines if not any(word in line.name.lower() or word in (line.unit or "").lower()
                                                       for word in _PACKAGING)]
    kinds = {kind(line.unit) for line in lines}
    ordered = len(kinds) == 1 and kinds <= {"mass", "volume"}
    if ordered:
        base = "g" if kinds == {"mass"} else "ml"
        lines = sorted(lines, key=lambda line: -(convert(line.quantity, line.unit, base) or 0))
    names, seen = [], set()
    for line in lines:
        if line.name.lower() not in seen:
            seen.add(line.name.lower())
            names.append(line.name)
    return {"text": ", ".join(names), "ordered": ordered or len(names) <= 1, "own": False}


def label(recipe, made: str, settings: dict) -> dict:
    """Pure logic. A product label from what the person entered: product
    name, ingredients, allergens, net amount, the date it was made, the
    business's name and address, and their statement (their state's
    required wording, in their own words). `missing` names what's blank."""
    ingredients = label_ingredients(recipe)
    parts = {
        "name": recipe.name,
        "ingredients": ingredients["text"],
        "allergens": str(getattr(recipe, "allergens", "") or ""),
        "net": str(getattr(recipe, "net_amount", "") or ""),
        "made": made,
        "business": str(settings.get("business") or ""),
        "address": str(settings.get("address") or ""),
        "statement": str(settings.get("statement") or ""),
    }
    names = {"ingredients": "ingredients", "net": "net amount", "business": "business name",
             "address": "address", "statement": "statement"}
    missing = [said for key, said in names.items() if not parts[key]]
    return {**parts, "ordered": ingredients["ordered"], "missing": missing}
