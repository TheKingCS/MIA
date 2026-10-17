"""
core.receipt_match
====================

A scanned receipt fills in a recipe's Bought It (Zac, 2026-10-17; the
next step after crafting recipes, DEC-0030). The inbox already reads a
receipt's lines (core/inbox_classify.receipt_items: description, amount,
quantity, unit price) and keeps them on the expense it files into the
Budget. Here each recipe material is matched to the receipt line that
names it best, so Bought It opens filled in for the person to check:
how many, and what was paid.

Matching is by words, made forgiving for store receipts: case and
punctuation ignored, "2X4X8" read as "2x4" and "8", "8FT" as "8", plurals
folded, and store abbreviations understood ("PLYWD" ~ "plywood").
Each receipt line is used once. Nothing is guessed when nothing fits:
those materials stay blank, and the receipt lines that matched nothing
are listed.
"""

from __future__ import annotations

import re
from typing import Optional

MIN_SCORE = 0.5


_UNIT = re.compile(r"^(\d+(?:/\d+)?)(ft|in|inch|lb|lbs|oz|gal|qt|pk|ct|mm|cm|m)$")
_STOP = {"x", "and", "the", "of", "for", "pc", "pcs", "ea", "each", "with"}


def _tokens(text: str) -> set[str]:
    """Pure logic. A name's words, store-receipt style: "2X4X8 STUD" →
    {"2x4", "2", "4", "8", "stud"}; "8FT" → "8"; plurals folded."""
    out = set()
    for w in re.findall(r"[a-z0-9/]+", str(text or "").lower()):
        w = _UNIT.sub(r"\1", w)
        if re.fullmatch(r"\d+(x\d+)+", w):  # dimensions: 2x4x8
            parts = w.split("x")
            out.update(parts)
            out.add("x".join(parts[:2]))
            continue
        w = w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
        if w and w not in _STOP:
            out.add(w)
    return out


def _same(a: str, b: str) -> bool:
    """Pure logic. Two words are the same item word: equal, or one is the
    other's store abbreviation (same first letter, its letters in order:
    "plywd" ~ "plywood", "scrw" ~ "screw")."""
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if len(short) < 3 or short[0] != long_[0] or short.isdigit() or long_.isdigit():
        return False
    it = iter(long_)
    return all(ch in it for ch in short)


def similarity(recipe_name: str, receipt_line: str) -> float:
    """Pure logic. How much of a recipe material's name the receipt line
    has, 0 to 1 (a receipt line says more than the recipe does)."""
    ta, tb = _tokens(recipe_name), _tokens(receipt_line)
    if not ta or not tb:
        return 0.0
    found = [t for t in ta if any(_same(t, u) for u in tb)]
    if not any(not t.isdigit() for t in found):  # numbers alone ("2", "4") never match
        return 0.0
    return round(len(found) / len(ta), 3)


def match(names: list[str], items: list[dict]) -> dict:
    """Pure logic. Each name (a recipe material) to its best receipt line,
    each line used once, best pairs first. Returns {"pairs": {name index:
    item index}, "unused": [item indexes]}."""
    scored = sorted(((similarity(n, it.get("description", "")), i, j)
                     for i, n in enumerate(names) for j, it in enumerate(items)), reverse=True)
    pairs: dict[int, int] = {}
    used: set[int] = set()
    for score, i, j in scored:
        if score < MIN_SCORE:
            break
        if i in pairs or j in used:
            continue
        pairs[i], _ = j, used.add(j)
    return {"pairs": pairs, "unused": [j for j in range(len(items)) if j not in used]}


def prefill(recipe, items: list[dict]) -> dict:
    """Bought It's values from a receipt: q_<line> and c_<line> for each
    recipe material the receipt has, plus what matched and what didn't."""
    lines = recipe.lines
    found = match([l.name for l in lines], items)
    values, matched = {}, []
    for i, j in found["pairs"].items():
        it = items[j]
        qty = float(it.get("quantity") or 0) or 1.0
        values[f"q_{i}"] = qty
        values[f"c_{i}"] = round(float(it.get("amount") or 0), 2)
        matched.append({"material": lines[i].name, "receipt": it.get("description", ""), "quantity": qty,
                        "paid": values[f"c_{i}"]})
    return {"values": values, "matched": matched,
            "unmatched": [items[j].get("description", "") for j in found["unused"]]}


def receipts(context, limit: int = 15) -> list[dict]:
    """Recent receipts with their lines: filed ones (Budget expenses that
    kept their items). Newest first."""
    from core.region import money

    budget = getattr(context, "budget", None)
    if budget is None:
        return []
    out = []
    for e in sorted((e for e in budget.all_expenses() if getattr(e, "items", None)), key=lambda e: e.date or "", reverse=True)[:limit]:
        out.append({"id": f"expense:{e.entry_id}", "name": f"{e.payee or e.description or 'Receipt'} · {e.date} · {money(e.amount)}",
                    "items": list(e.items)})
    return out


def find(context, receipt_id: str) -> Optional[dict]:
    return next((r for r in receipts(context, limit=200) if r["id"] == receipt_id), None)
