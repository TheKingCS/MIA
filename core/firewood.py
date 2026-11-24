"""
core.firewood
===============

Firewood for the winter (Jarvis brainstorm, round 4: homestead). "Do I have enough firewood?" says the cords in his
inventory against what a winter takes him: his own figure (`prepared.firewood_cords`, set by voice with
set_preparedness), never a guess; without it, the usual range said as only that and his number asked for.

How: `cords_on_hand(items)` (pure) reads inventory records named as firewood or wood with a cord measure: "cords"
(full cords, 128 cubic feet), "face cord" or "rick" (about a third of a cord, the common 16-inch pieces); a record
whose amount it can't read is named, never guessed. `say(context)` compares and says what's short.
"""

from __future__ import annotations

import re
from typing import Optional

FACE_CORD = 1 / 3  # a face cord (rick) of 16-inch pieces is about a third of a full cord
_WOOD = re.compile(r"\b(?:fire ?wood|split wood|wood ?pile|cord ?wood|seasoned wood)\b", re.I)
_FACE = re.compile(r"\b(?:face cords?|ricks?)\b", re.I)
_CORD = re.compile(r"\bcords?\b", re.I)
_NUMBER = re.compile(r"(\d+(?:\.\d+)?)\s*(?=(?:face )?cords?\b|ricks?\b)", re.I)


def cords_on_hand(items: list) -> tuple[float, list]:
    """Pure logic. (full cords of firewood in his records, the firewood records whose amount couldn't be read). A
    record counts its quantity in its measure ("Firewood (cords)" x 3 is 3 cords, "Face cord oak" x 3 is 1); a number
    in the name stands when there's no quantity ("Firewood 2 cords")."""
    total, unread = 0.0, []
    for item in items:
        name = str(getattr(item, "name", "") or "")
        if not _WOOD.search(name) and not (_CORD.search(name) or _FACE.search(name)):
            continue
        if not (_CORD.search(name) or _FACE.search(name) or _CORD.search(str(getattr(item, "unit", "") or ""))):
            unread.append(name)
            continue
        try:
            qty = float(getattr(item, "quantity", 0) or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            found = _NUMBER.search(name)
            qty = float(found.group(1)) if found else 0.0
        if qty <= 0:
            continue
        total += qty * (FACE_CORD if _FACE.search(name) else 1.0)
    return round(total, 2), unread


def _setting(context, key: str) -> Optional[float]:
    """His number setting, or None."""
    try:
        from core import person_settings

        value = person_settings.get(context, key, None)
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError, AttributeError):
        return None


def say(context) -> str:
    """For "do I have enough firewood?": cords on hand against his winter's figure, what's short; without his figure,
    the usual range said as only that and his number asked for."""
    inventory = getattr(context, "inventory", None)
    have, unread = cords_on_hand(inventory.all_items() if inventory is not None else [])
    need = _setting(context, "prepared.firewood_cords")
    parts = [f"Firewood: about {have:g} cord{'s' if have != 1 else ''} in your inventory." if have else
             "Firewood: none in your inventory with a cord measure (log it like \"firewood, cords\", 3)."]
    if need:
        if have >= need:
            parts.append(f"That covers your {need:g} cords a winter.")
        else:
            parts.append(f"You burn about {need:g} cords a winter, so you're {round(need - have, 2):g} short.")
    else:
        parts.append("How many cords does a winter take you? A wood stove as the main heat often burns 3 to 6, a "
                     "few as backup heat; tell me yours (\"I burn 4 cords a winter\") and I'll keep count.")
    if unread:
        parts.append("I couldn't read how much is in " + ", ".join(unread[:3]) + " (give it in cords or face cords).")
    return " ".join(parts)
