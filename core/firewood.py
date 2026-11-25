"""
core.firewood
===============

Firewood for the winter (Jarvis brainstorm, round 4: homestead). "Do I have enough firewood?" says the cords in his
inventory against what a winter takes him: his own figure (`prepared.firewood_cords`, set by voice with
set_preparedness), never a guess; without it, the usual range said as only that and his number asked for.

How: `cords_on_hand(items)` (pure) reads inventory records named as firewood (or a kind of wood with a cord measure;
never bungee or extension cords), in "cords" (full cords, 128 cubic feet) or "face cords"/"ricks" (the piece length
over 48 inches of a cord: a third for 16-inch pieces), with fractions and words ("1 1/2 cords", "half cord"); a record
whose amount it can't read is named, never guessed. `say(context)` compares and says what's short.
"I burn about 4 cords a winter" is kept in code (`reply`, from core/quick_commands.py).
"""

from __future__ import annotations

import re
from typing import Optional

FACE_CORD = 1 / 3  # a face cord (rick) of 16-inch pieces is about a third of a full cord (4 x 8 ft x the length)
# Only wood: "bungee cords", "an extension cord" and "a cord of rope" are never firewood
_WOOD = re.compile(r"\b(?:fire ?wood|split wood|wood ?pile|cord ?wood|seasoned wood)\b", re.I)
# A kind of wood counts only with a cord measure ("oak, 2 cords"): never "an oak dining table" or "a log splitter"
_KIND = re.compile(r"\b(?:hardwood|softwood|logs|oak|maple|hickory|ash|birch|cherry|locust|pine)\b", re.I)
_FACE = re.compile(r"\b(?:face cords?|ricks?)\b", re.I)
_CORD = re.compile(r"\b(?:bush )?cords?\b", re.I)
_LENGTH = re.compile(r"(\d{1,2})\s*(?:\"|in\b|inch(?:es)?)", re.I)
# An amount of cords said in the name: "2 cords", "1.5 cords", ".5 cord", "1/2 cord", "1 1/2 cords", "half cord",
# "a cord and a half"
_AMOUNT = re.compile(r"(?:(\d+)\s+)?(\d+)/(\d+)\s*(?=(?:face |bush )?cords?\b|ricks?\b)"
                     r"|(\d*\.\d+|\d+)\s*(?=(?:face |bush )?cords?\b|ricks?\b)", re.I)
_WORD_AMOUNTS = (("a cord and a half", 1.5), ("cord and a half", 1.5), ("one and a half", 1.5), ("half a cord", 0.5),
                 ("half cord", 0.5), ("quarter cord", 0.25))


def _amount(name: str) -> Optional[float]:
    """Pure logic. The cords (or face cords) said in a record's name, or None when it says no amount."""
    low = name.lower()
    for words, value in _WORD_AMOUNTS:
        if words in low:
            return value
    m = _AMOUNT.search(low)
    if not m:
        return None
    if m.group(3):
        return float(m.group(1) or 0) + float(m.group(2)) / float(m.group(3))
    return float(m.group(4))


def _face_share(name: str) -> float:
    """Pure logic. What one face cord is of a full cord: its piece length over 48 inches, 16 inches unless said."""
    length = _LENGTH.search(name)
    inches = int(length.group(1)) if length else 16
    return inches / 48 if 6 <= inches <= 48 else FACE_CORD


def cords_on_hand(items: list) -> tuple[float, list]:
    """Pure logic. (full cords of firewood in his records, the firewood records whose amount couldn't be read). Only
    records named as firewood count, or a kind of wood with a cord measure ("oak, 2 cords"). The amount is the one in
    the name ("Firewood 1 1/2 cords", "half cord") times how many when the quantity is above one; with none in the
    name, a record named in cords ("Firewood (cords)") counts its quantity. A face cord is its piece length over 48
    inches of a full cord (16 inches, a third, unless said). A record that says no amount, one with an amount in its
    name but a count of 0, or "cord wood" by the piece, is named, never guessed."""
    total, unread = 0.0, []
    for item in items:
        name = str(getattr(item, "name", "") or "")
        face = bool(_FACE.search(name))
        if not (_WOOD.search(name) or (_KIND.search(name) and (face or _CORD.search(name)))):
            continue
        if not face and not _CORD.search(name):
            unread.append(name)  # firewood with no cord measure
            continue
        try:
            qty = float(getattr(item, "quantity", 0) or 0)
        except (TypeError, ValueError):
            qty = 0.0
        said = _amount(name)
        if said is not None and qty > 0:
            cords = said * (qty if qty > 1 else 1)
        elif said is None and qty > 0 and not re.search(r"\bcord ?wood\b", name, re.I):
            cords = qty
        else:
            unread.append(name)
            continue
        total += cords * (_face_share(name) if face else 1.0)
    return round(total, 2), unread


def _setting(context, key: str) -> Optional[float]:
    """His number setting, or None."""
    try:
        from core import person_settings

        value = person_settings.get(context, key, None)
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError, AttributeError):
        return None


_BURN = re.compile(r"^\s*(?:i|we)\s+(?:usually\s+|probably\s+)?(?:burn|go through|use)\s+(?:about\s+|around\s+|"
                   r"roughly\s+)?(\d+(?:\.\d+)?)\s+(face\s+)?cords?\b", re.I)


def reply(context, text: str) -> Optional[str]:
    """"I burn about 4 cords a winter" kept, in code (core/quick_commands.py): the model only echoed it (live check
    through the whole turn, 2026-11-24). Then the firewood check against it. None for other words."""
    found = _BURN.search(text or "")
    if not found or "winter" not in (text or "").lower() and "year" not in (text or "").lower():
        return None
    from core.assistant_today_actions import _action_set_preparedness

    cords = float(found.group(1)) * (1 / 3 if found.group(2) else 1)  # a face cord is about a third of a cord
    kept = _action_set_preparedness(context, {"firewood_cords": round(cords, 2)})
    return kept + " " + say(context)


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
